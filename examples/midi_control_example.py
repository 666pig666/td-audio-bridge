"""
MIDI Control Example
Maps audio analysis to MIDI CC for external hardware/software control
"""

from scripts.audio_analyzer import AudioAnalyzer
from scripts.midi_router import MIDIRouter, MIDIPresets, DrumMachineMapper
from scripts.transient_detector import MultiTransientDetector

# Initialize components
analyzer = AudioAnalyzer(fft_size=2048, smoothing_time_constant=0.7)
midi_router = MIDIRouter()
drum_mapper = DrumMachineMapper(channel=10)
transient_detector = MultiTransientDetector()

# Setup MIDI mappings
print("Setting up MIDI mappings...")

# Map frequency bands to CC 20-27 (channel 1)
MIDIPresets.create_band_mapping(midi_router, num_bands=8, start_cc=20, channel=1)

# Map audio levels to standard CCs
MIDIPresets.create_level_mapping(midi_router, channel=1)

# Additional custom mappings
midi_router.add_mapping(
    name='bass_boost',
    cc_number=10,
    channel=1,
    min_value=0,
    max_value=127,
    input_min=0.0,
    input_max=1.0,
    smoothing=0.4
)

midi_router.add_mapping(
    name='treble_boost',
    cc_number=11,
    channel=1,
    min_value=0,
    max_value=127,
    input_min=0.0,
    input_max=1.0,
    smoothing=0.4
)


def process_audio_to_midi():
    """Main processing function."""

    # Get audio spectrum
    audio_spectrum = op('audiospectrumchop')
    if audio_spectrum is None:
        return

    # Analyze audio
    result = analyzer.analyze_chop(audio_spectrum)

    # Get data
    bands_8 = result['bands']['8_band']
    rms = result['rms']
    peak = result['peak']
    envelope = result['envelope']

    # === MIDI CC Mapping ===

    # Map frequency bands
    band_mappings = {f'band_{i}': bands_8[i] for i in range(8)}
    band_mappings['rms'] = rms
    band_mappings['peak'] = peak
    band_mappings['envelope'] = envelope

    # Calculate bass and treble
    bass = sum(bands_8[:2]) / 2  # Average of first 2 bands
    treble = sum(bands_8[-2:]) / 2  # Average of last 2 bands
    band_mappings['bass_boost'] = bass
    band_mappings['treble_boost'] = treble

    # Generate MIDI messages
    midi_messages = midi_router.map_multiple(band_mappings)

    # Send MIDI CC messages
    for msg in midi_messages:
        send_midi_cc(msg['cc_number'], msg['channel'], msg['value'])

    # === Transient Detection and MIDI Notes ===

    # Detect all transients
    transient_results = transient_detector.detect_all(bands_8)

    # Send MIDI notes for drum hits
    if transient_results['kick']['triggered']:
        strength = transient_results['kick']['strength']
        note_msg = drum_mapper.trigger_drum('kick', strength)
        if note_msg:
            send_midi_note(note_msg)

    if transient_results['snare']['triggered']:
        strength = transient_results['snare']['strength']
        note_msg = drum_mapper.trigger_drum('snare', strength)
        if note_msg:
            send_midi_note(note_msg)

    if transient_results['hihat']['triggered']:
        strength = transient_results['hihat']['strength']
        note_msg = drum_mapper.trigger_drum('hihat_closed', strength)
        if note_msg:
            send_midi_note(note_msg)


def send_midi_cc(cc_number, channel, value):
    """Send MIDI CC via TouchDesigner MIDI Out."""
    midi_out = op('midiout1')
    if midi_out:
        midi_out.sendCC(channel, cc_number, value)


def send_midi_note(note_msg):
    """Send MIDI Note On/Off."""
    midi_out = op('midiout1')
    if not midi_out:
        return

    if note_msg['type'] == 'note_on':
        midi_out.sendNoteOn(
            note_msg['channel'],
            note_msg['note'],
            note_msg['velocity']
        )

        # Schedule note off
        duration_frames = note_msg.get('duration_frames', 5)
        run(
            f"op('midiout1').sendNoteOff({note_msg['channel']}, {note_msg['note']}, 0)",
            delayFrames=duration_frames
        )


def list_midi_mappings():
    """Print all MIDI mappings."""
    print("\n=== MIDI CC Mappings ===")
    for name, config in midi_router.get_all_mappings().items():
        print(f"{name}: CC {config['cc_number']} on Channel {config['channel']}")

    print("\n=== MIDI Note Mappings ===")
    drums = drum_mapper.get_available_drums()
    print(f"Available drums: {', '.join(drums)}")


# Execute every frame
def onFrameStart(frame):
    """Frame callback."""
    process_audio_to_midi()


# Display configuration
list_midi_mappings()

print("\n=== MIDI Control Setup Complete ===")
print("Audio analysis data is now being sent as MIDI CC and Notes")
print("Configure your MIDI device to receive on channel 1 (CC) and 10 (drums)")
