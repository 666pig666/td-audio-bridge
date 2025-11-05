"""
Full Integration Example
Combines all modules: Audio Analysis, Transient Detection, MIDI, and OSC
Demonstrates a complete audio-reactive system
"""

from scripts.audio_analyzer import AudioAnalyzer, FrequencyBandPresets
from scripts.transient_detector import MultiTransientDetector
from scripts.midi_router import MIDIRouter, MIDIPresets, DrumMachineMapper
from scripts.osc_exporter import OSCExporter

# ============================================================================
# INITIALIZATION
# ============================================================================

print("Initializing TouchDesigner Audio Analysis Bridge...")

# Audio analyzer
analyzer = AudioAnalyzer(fft_size=2048, smoothing_time_constant=0.75)
analyzer.set_attack_release(attack_ms=5, release_ms=150, fps=60)

# Transient detection
transient_detector = MultiTransientDetector()

# Configure individual detectors
transient_detector.get_detector('kick').set_threshold(0.3)
transient_detector.get_detector('kick').set_sensitivity(0.5)
transient_detector.get_detector('kick').set_min_interval(120)

transient_detector.get_detector('snare').set_threshold(0.35)
transient_detector.get_detector('snare').set_sensitivity(0.6)
transient_detector.get_detector('snare').set_min_interval(100)

transient_detector.get_detector('hihat').set_threshold(0.25)
transient_detector.get_detector('hihat').set_sensitivity(0.7)
transient_detector.get_detector('hihat').set_min_interval(60)

# MIDI routing
midi_router = MIDIRouter()
drum_mapper = DrumMachineMapper(channel=10)

# Setup MIDI presets
MIDIPresets.create_full_preset(midi_router, channel=1)

# OSC export
osc_exporter = OSCExporter(host='127.0.0.1', port=7000)
osc_exporter.set_address_prefix('/audio')

# ============================================================================
# CALLBACKS
# ============================================================================

def on_kick(strength, detection_type):
    """Callback for kick detection."""
    print(f"🥁 Kick: {strength:.2f}")

    # Trigger visual effect
    op('kick_visualizer').par.Trigger.pulse()

    # Send MIDI note
    note_msg = drum_mapper.trigger_drum('kick', strength)
    if note_msg:
        op('midiout1').sendNoteOn(
            note_msg['channel'],
            note_msg['note'],
            note_msg['velocity']
        )

    # Send OSC
    osc_exporter.send_transient('kick', strength)


def on_snare(strength, detection_type):
    """Callback for snare detection."""
    print(f"🥁 Snare: {strength:.2f}")
    op('snare_visualizer').par.Trigger.pulse()

    note_msg = drum_mapper.trigger_drum('snare', strength)
    if note_msg:
        op('midiout1').sendNoteOn(
            note_msg['channel'],
            note_msg['note'],
            note_msg['velocity']
        )

    osc_exporter.send_transient('snare', strength)


def on_hihat(strength, detection_type):
    """Callback for hi-hat detection."""
    print(f"🥁 Hi-Hat: {strength:.2f}")
    op('hihat_visualizer').par.Trigger.pulse()

    note_msg = drum_mapper.trigger_drum('hihat_closed', strength)
    if note_msg:
        op('midiout1').sendNoteOn(
            note_msg['channel'],
            note_msg['note'],
            note_msg['velocity']
        )

    osc_exporter.send_transient('hihat', strength)


# Register callbacks
transient_detector.get_detector('kick').add_callback(on_kick)
transient_detector.get_detector('snare').add_callback(on_snare)
transient_detector.get_detector('hihat').add_callback(on_hihat)

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_audio():
    """Main audio processing pipeline."""

    # Get audio input
    audio_spectrum = op('audiospectrumchop')
    if audio_spectrum is None:
        return

    # === 1. ANALYZE AUDIO ===
    result = analyzer.analyze_chop(audio_spectrum)

    rms = result['rms']
    peak = result['peak']
    envelope = result['envelope']
    bands_8 = result['bands']['8_band']
    bands_16 = result['bands']['16_band']

    # === 2. UPDATE TOUCHDESIGNER PARAMETERS ===
    # Update level meters
    if op('audio_levels'):
        op('audio_levels').par.Rms = rms
        op('audio_levels').par.Peak = peak
        op('audio_levels').par.Envelope = envelope

    # Update visualizers
    if op('level_visualizer'):
        op('level_visualizer').par.Value0 = rms
        op('level_visualizer').par.Value1 = peak
        op('level_visualizer').par.Value2 = envelope

    # === 3. TRANSIENT DETECTION ===
    transient_results = transient_detector.detect_all(bands_8)

    # Update trigger indicators (no callback needed, just visual feedback)
    if op('trigger_indicators'):
        op('trigger_indicators').par.Kick = 1 if transient_results['kick']['triggered'] else 0
        op('trigger_indicators').par.Snare = 1 if transient_results['snare']['triggered'] else 0
        op('trigger_indicators').par.Hihat = 1 if transient_results['hihat']['triggered'] else 0

    # === 4. MIDI OUTPUT ===
    # Map frequency bands to MIDI CC
    band_mappings = {
        'rms': rms,
        'peak': peak,
        'envelope': envelope
    }

    for i in range(8):
        band_mappings[f'band_{i}'] = bands_8[i]

    # Generate and send MIDI messages
    midi_messages = midi_router.map_multiple(band_mappings)
    for msg in midi_messages:
        if op('midiout1'):
            op('midiout1').sendCC(
                msg['channel'],
                msg['cc_number'],
                msg['value']
            )

    # === 5. OSC EXPORT ===
    # Send complete analysis over OSC
    osc_exporter.send_analysis_data(result)

    # Send additional frequency range data
    bass = analyzer.get_frequency_range(20, 250)
    mid = analyzer.get_frequency_range(250, 4000)
    high = analyzer.get_frequency_range(4000, 20000)

    osc_exporter.send_message('/freq/bass', bass)
    osc_exporter.send_message('/freq/mid', mid)
    osc_exporter.send_message('/freq/high', high)

    # === 6. OUTPUT TO CHOPS (for further processing in TD) ===
    # Create CHOP outputs
    if op('analysis_output'):
        output_chop = op('analysis_output')
        output_chop['rms'][0] = rms
        output_chop['peak'][0] = peak
        output_chop['envelope'][0] = envelope

        for i in range(8):
            output_chop[f'band_{i}'][0] = bands_8[i]

    # === 7. STATISTICS AND LOGGING ===
    # Log every 60 frames (once per second at 60fps)
    if me.time.frame % 60 == 0:
        log_statistics()


def log_statistics():
    """Log analysis statistics."""
    stats = {
        'analyzer': {
            'avg_rms': analyzer.get_history_average(30),
            'max_peak': analyzer.get_peak_history_max(30)
        },
        'transients': {
            'kick': transient_detector.get_detector('kick').get_statistics(),
            'snare': transient_detector.get_detector('snare').get_statistics(),
            'hihat': transient_detector.get_detector('hihat').get_statistics()
        },
        'midi': {
            'total_mappings': len(midi_router.get_all_mappings())
        },
        'osc': osc_exporter.get_statistics()
    }

    # Write to DAT for monitoring
    if op('statistics_log'):
        log_dat = op('statistics_log')
        log_dat.clear()
        log_dat.appendRow(['Statistic', 'Value'])
        log_dat.appendRow(['Avg RMS', f"{stats['analyzer']['avg_rms']:.3f}"])
        log_dat.appendRow(['Max Peak', f"{stats['analyzer']['max_peak']:.3f}"])
        log_dat.appendRow(['Kick Triggers', stats['transients']['kick']['total_triggers']])
        log_dat.appendRow(['Snare Triggers', stats['transients']['snare']['total_triggers']])
        log_dat.appendRow(['Hi-Hat Triggers', stats['transients']['hihat']['total_triggers']])
        log_dat.appendRow(['OSC Messages', stats['osc']['messages_sent']])


# ============================================================================
# CONTROL FUNCTIONS
# ============================================================================

def reset_all():
    """Reset all analyzers and detectors."""
    analyzer.reset()
    transient_detector.reset_all()
    print("All analyzers reset!")


def enable_midi(enable=True):
    """Enable or disable MIDI output."""
    for name in midi_router.get_all_mappings().keys():
        if enable:
            midi_router.enable_mapping(name)
        else:
            midi_router.disable_mapping(name)
    print(f"MIDI output {'enabled' if enable else 'disabled'}")


def enable_osc(enable=True):
    """Enable or disable OSC output."""
    if enable:
        osc_exporter.enable()
    else:
        osc_exporter.disable()
    print(f"OSC output {'enabled' if enable else 'disabled'}")


def set_sensitivity(sensitivity):
    """Set global transient detection sensitivity (0-1)."""
    for name in ['kick', 'snare', 'hihat']:
        detector = transient_detector.get_detector(name)
        if detector:
            detector.set_sensitivity(sensitivity)
    print(f"Sensitivity set to: {sensitivity}")


# ============================================================================
# TOUCHDESIGNER CALLBACKS
# ============================================================================

def onFrameStart(frame):
    """Execute every frame."""
    process_audio()


def onStart():
    """Execute when project starts."""
    print("\n" + "="*60)
    print("TouchDesigner Audio Analysis Bridge - ACTIVE")
    print("="*60)
    print(f"FFT Size: {analyzer.fft_size}")
    print(f"Smoothing: {analyzer.smoothing_time_constant}")
    print(f"MIDI Mappings: {len(midi_router.get_all_mappings())}")
    print(f"OSC Destination: {osc_exporter.host}:{osc_exporter.port}")
    print("="*60 + "\n")


def onExit():
    """Cleanup when project closes."""
    print("Closing OSC connection...")
    osc_exporter.close()
    print("Audio Analysis Bridge shutdown complete.")


# ============================================================================
# INITIALIZATION COMPLETE
# ============================================================================

print("\n✅ Full Integration Setup Complete!")
print("Audio analysis with MIDI and OSC output is now running.")
print("\nAvailable functions:")
print("  - reset_all(): Reset all analyzers")
print("  - enable_midi(True/False): Toggle MIDI output")
print("  - enable_osc(True/False): Toggle OSC output")
print("  - set_sensitivity(0-1): Adjust transient detection sensitivity")
