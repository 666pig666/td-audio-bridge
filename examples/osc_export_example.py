"""
OSC Export Example
Sends audio analysis data over OSC/UDP to external applications
Compatible with Processing, Max/MSP, Pure Data, Resolume, etc.
"""

from scripts.audio_analyzer import AudioAnalyzer
from scripts.osc_exporter import OSCExporter, MulticastExporter
from scripts.transient_detector import MultiTransientDetector

# Initialize components
analyzer = AudioAnalyzer(fft_size=2048, smoothing_time_constant=0.8)
transient_detector = MultiTransientDetector()

# Single destination setup
osc_exporter = OSCExporter(host='127.0.0.1', port=7000)
osc_exporter.set_address_prefix('/touchdesigner/audio')

# OR use multicast for multiple destinations
multicast = MulticastExporter()
multicast.add_osc_destination('local', '127.0.0.1', 7000)
multicast.add_osc_destination('processing', '127.0.0.1', 8000)
multicast.add_osc_destination('resolume', '127.0.0.1', 7001)

# Choose which to use
USE_MULTICAST = False


def export_audio_over_osc():
    """Main OSC export function."""

    # Get audio spectrum
    audio_spectrum = op('audiospectrumchop')
    if audio_spectrum is None:
        return

    # Analyze audio
    result = analyzer.analyze_chop(audio_spectrum)

    if USE_MULTICAST:
        # Send to multiple destinations
        multicast.send_to_all('analysis', result)
    else:
        # Send to single destination
        send_analysis_data(result)

    # Detect and send transients
    bands_8 = result['bands']['8_band']
    transient_results = transient_detector.detect_all(bands_8)

    for transient_type, detection in transient_results.items():
        if detection['triggered']:
            if USE_MULTICAST:
                multicast.send_to_all('transient', {
                    'type': transient_type,
                    'strength': detection['strength']
                })
            else:
                osc_exporter.send_transient(transient_type, detection['strength'])


def send_analysis_data(result):
    """Send detailed analysis data via OSC."""

    # Send level data
    osc_exporter.send_message('/rms', result['rms'])
    osc_exporter.send_message('/peak', result['peak'])
    osc_exporter.send_message('/envelope', result['envelope'])

    # Send frequency bands (all three resolutions)
    bands_8 = result['bands']['8_band']
    bands_16 = result['bands']['16_band']
    bands_32 = result['bands']['32_band']

    # Send as individual messages
    for i, value in enumerate(bands_8):
        osc_exporter.send_message(f'/bands/8/{i}', value)

    # OR send as bundle (all at once)
    # band_bundle = [(f'/bands/8/{i}', value) for i, value in enumerate(bands_8)]
    # osc_exporter.send_bundle(band_bundle)

    # Send specific frequency ranges
    bass_energy = analyzer.get_frequency_range(20, 250)  # Bass
    mid_energy = analyzer.get_frequency_range(250, 4000)  # Mids
    high_energy = analyzer.get_frequency_range(4000, 20000)  # Highs

    osc_exporter.send_message('/freq/bass', bass_energy)
    osc_exporter.send_message('/freq/mid', mid_energy)
    osc_exporter.send_message('/freq/high', high_energy)

    # Send statistics
    avg_rms = analyzer.get_history_average(frames=30)
    max_peak = analyzer.get_peak_history_max(frames=30)

    osc_exporter.send_message('/stats/avg_rms', avg_rms)
    osc_exporter.send_message('/stats/max_peak', max_peak)


def print_osc_addresses():
    """Print all OSC addresses being sent."""
    print("\n=== OSC Address Map ===")
    print("Levels:")
    print("  /touchdesigner/audio/rms - RMS level (0-1)")
    print("  /touchdesigner/audio/peak - Peak level (0-1)")
    print("  /touchdesigner/audio/envelope - Envelope follower (0-1)")
    print("\nFrequency Bands:")
    print("  /touchdesigner/audio/bands/8/[0-7] - 8-band spectrum")
    print("  /touchdesigner/audio/bands/16/[0-15] - 16-band spectrum")
    print("  /touchdesigner/audio/bands/32/[0-31] - 32-band spectrum")
    print("\nFrequency Ranges:")
    print("  /touchdesigner/audio/freq/bass - Bass (20-250 Hz)")
    print("  /touchdesigner/audio/freq/mid - Mids (250-4000 Hz)")
    print("  /touchdesigner/audio/freq/high - Highs (4000-20000 Hz)")
    print("\nTransients:")
    print("  /touchdesigner/audio/transient/kick - Kick detection")
    print("  /touchdesigner/audio/transient/snare - Snare detection")
    print("  /touchdesigner/audio/transient/hihat - Hi-hat detection")
    print("\nStatistics:")
    print("  /touchdesigner/audio/stats/avg_rms - Average RMS (30 frames)")
    print("  /touchdesigner/audio/stats/max_peak - Max peak (30 frames)")


# Example: Processing receiver code
def print_processing_example():
    """Print example Processing code to receive OSC."""
    print("\n=== Processing Receiver Example ===")
    print("""
import oscP5.*;

OscP5 oscP5;

void setup() {
  size(800, 600);
  oscP5 = new OscP5(this, 7000);
}

void oscEvent(OscMessage msg) {
  // Receive RMS level
  if (msg.checkAddrPattern("/touchdesigner/audio/rms")) {
    float rms = msg.get(0).floatValue();
    println("RMS: " + rms);
  }

  // Receive frequency band
  if (msg.checkAddrPattern("/touchdesigner/audio/bands/8/0")) {
    float bassLevel = msg.get(0).floatValue();
    println("Bass: " + bassLevel);
  }

  // Receive kick transient
  if (msg.checkAddrPattern("/touchdesigner/audio/transient/kick")) {
    float strength = msg.get(0).floatValue();
    println("KICK! Strength: " + strength);
    // Trigger visual effect
  }
}
    """)


# Example: Max/MSP receiver setup
def print_maxmsp_example():
    """Print example Max/MSP setup."""
    print("\n=== Max/MSP Receiver Example ===")
    print("""
1. Create [udpreceive 7000] object
2. Connect to [oscparse] object
3. Route messages:
   [route /touchdesigner/audio/rms]
   [route /touchdesigner/audio/peak]
   [route /touchdesigner/audio/bands/8/0]
   [route /touchdesigner/audio/transient/kick]

4. Use received values to control parameters
    """)


# Frame callback
def onFrameStart(frame):
    """Execute every frame."""
    export_audio_over_osc()


# Setup complete
print("=== OSC Export Setup Complete ===")
print(f"Sending OSC to: {osc_exporter.host}:{osc_exporter.port}")
print_osc_addresses()

# Uncomment to see receiver examples
# print_processing_example()
# print_maxmsp_example()

print("\nOSC exporter is now running!")
print("Use OSC monitoring software to verify messages are being sent")
