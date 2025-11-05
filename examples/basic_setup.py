"""
Basic Setup Example
Demonstrates simple audio analysis with visualization
"""

from scripts.audio_analyzer import AudioAnalyzer
from scripts.transient_detector import TransientDetector

# Create analyzer instance
analyzer = AudioAnalyzer(fft_size=2048, smoothing_time_constant=0.8)

# Set attack/release for envelope follower
analyzer.set_attack_release(attack_ms=5, release_ms=100, fps=60)

# Create transient detector for kick detection
kick_detector = TransientDetector(threshold=0.3, sensitivity=0.5, min_interval_ms=100)


def on_kick_detected(strength, detection_type):
    """Callback when kick is detected."""
    print(f"KICK! Strength: {strength:.2f}")
    # Trigger visual effect
    op('visualizer').par.Trigger.pulse()


# Add callback
kick_detector.add_callback(on_kick_detected)


# Main analysis function (call every frame)
def analyze_audio():
    """Run audio analysis."""

    # Get audio spectrum CHOP
    audio_spectrum = op('audiospectrumchop')

    if audio_spectrum is None:
        return

    # Analyze audio
    result = analyzer.analyze_chop(audio_spectrum)

    # Get analysis data
    rms = result['rms']
    peak = result['peak']
    envelope = result['envelope']
    bands_8 = result['bands']['8_band']

    # Update TouchDesigner parameters
    op('audio_levels').par.Rms = rms
    op('audio_levels').par.Peak = peak
    op('audio_levels').par.Envelope = envelope

    # Detect kick drum
    kick_result = kick_detector.detect_kick(bands_8)

    if kick_result['triggered']:
        print(f"Kick detected at strength: {kick_result['strength']:.2f}")

    # Output band data to CHOP
    for i, band_value in enumerate(bands_8):
        op('band_output')[i] = band_value


# Usage in TouchDesigner:
# 1. Create Execute DAT
# 2. Set to run on frameStart
# 3. Call this function

def onFrameStart(frame):
    """Execute every frame."""
    analyze_audio()


print("Basic audio analysis setup complete!")
print("Connect audio to 'audiospectrumchop' operator")
print("Visual feedback will appear on 'visualizer' operator")
