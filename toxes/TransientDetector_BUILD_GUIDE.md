# TransientDetector.tox - Build Guide

## Overview
Real-time kick/snare/hi-hat detection using energy-based and spectral flux algorithms. Provides trigger events and callback support.

## CHOP Network Structure

### Inputs
- **audioin**: Audio input for analysis
- **bandsin**: Optional frequency band input (from FrequencyBands.tox)

### Core Components

#### 1. Energy Detection Path

**Audio Analysis CHOP**
- Input: audioin
- Function: RMS
- Purpose: Measure overall energy level

**Math CHOP (Threshold)**
- Input: Audio Analysis output
- Operation: Compare (Greater Than)
- Threshold: Custom parameter (default: 0.3)
- Output: Binary trigger (0 or 1)

**Logic CHOP (Debounce)**
- Input: Threshold output
- Operation: Timer Off Delay
- Delay: Minimum interval parameter (default: 100ms)
- Purpose: Prevent multiple triggers

#### 2. Spectral Flux Path

**Math CHOP (Diff)**
- Input: bandsin (frequency bands)
- Operation: Subtract
- Pre OP: 1 frame delay
- Purpose: Calculate change in spectrum

**Math CHOP (Positive Only)**
- Input: Diff output
- Operation: Max with 0
- Purpose: Keep only increases

**Math CHOP (Sum)**
- Input: Positive only output
- Operation: Sum all channels
- Output: Spectral flux value

**Math CHOP (Flux Threshold)**
- Input: Spectral flux
- Operation: Compare with adaptive threshold
- Output: Binary trigger

#### 3. Band-Specific Detectors

**Kick Detector (Bands 0-1)**
- Input: bandsin channels 0-1
- Math: Average
- Threshold: Custom (default: 0.3)
- Output: kick_trigger

**Snare Detector (Bands 2-4)**
- Input: bandsin channels 2-4
- Math: Average
- Threshold: Custom (default: 0.35)
- Output: snare_trigger

**Hi-Hat Detector (Bands 6-7)**
- Input: bandsin channels 6-7
- Math: Average
- Threshold: Custom (default: 0.25)
- Output: hihat_trigger

#### 4. Adaptive Threshold

**Trail CHOP**
- Input: Energy or flux value
- Length: 60 frames (1 second at 60fps)
- Purpose: Recent history

**Math CHOP (Average)**
- Input: Trail output
- Operation: Average
- Output: baseline_energy

**Math CHOP (Threshold Calculation)**
- Formula: `baseline_energy + (threshold * sensitivity)`
- Output: adaptive_threshold

### Python Extension

**transient_callbacks.py** (attach to Execute DAT)
```python
def onValueChange(channel, sampleIndex, val, prev):
    """Called when transient is detected."""

    detector = parent().par.Detector.eval()

    if channel.name == 'kick_trigger' and val > 0:
        # Fire kick callback
        strength = op('kick_energy')[0]
        parent.Transientdetector.OnKick(strength)

    elif channel.name == 'snare_trigger' and val > 0:
        # Fire snare callback
        strength = op('snare_energy')[0]
        parent.Transientdetector.OnSnare(strength)

    elif channel.name == 'hihat_trigger' and val > 0:
        # Fire hi-hat callback
        strength = op('hihat_energy')[0]
        parent.Transientdetector.OnHihat(strength)
```

### Custom Parameters

**Detection**
- **Algorithm**: Menu (Energy, Spectral Flux, Hybrid) - Detection method
- **Threshold**: Float (0-1) - Base detection threshold
- **Sensitivity**: Float (0-1) - Adaptive sensitivity
- **Min Interval**: Integer (ms) - Minimum time between triggers

**Kick Settings**
- **Kick Enable**: Toggle - Enable kick detection
- **Kick Threshold**: Float (0-1)
- **Kick Bands**: String - Band indices (e.g., "0 1")

**Snare Settings**
- **Snare Enable**: Toggle
- **Snare Threshold**: Float (0-1)
- **Snare Bands**: String - Band indices (e.g., "2 3 4")

**Hi-Hat Settings**
- **Hihat Enable**: Toggle
- **Hihat Threshold**: Float (0-1)
- **Hihat Bands**: String - Band indices (e.g., "6 7")

### Outputs (CHOPs)
- **kick_trigger**: Binary trigger for kick detection
- **snare_trigger**: Binary trigger for snare detection
- **hihat_trigger**: Binary trigger for hi-hat detection
- **general_trigger**: General transient trigger
- **kick_strength**: Normalized strength value
- **snare_strength**: Normalized strength value
- **hihat_strength**: Normalized strength value
- **adaptive_threshold**: Current adaptive threshold value

### Outputs (DAT)
- **trigger_log**: Recent trigger events with timestamps

## Usage with Python Module

```python
# Import the transient detector module
from scripts import transient_detector

# Create detector instance
detector = transient_detector.TransientDetector(
    threshold=0.3,
    sensitivity=0.5,
    min_interval_ms=100
)

# Add callback
def on_kick(strength, det_type):
    print(f"Kick detected! Strength: {strength}")
    # Trigger visual effect, etc.

detector.add_callback(on_kick)

# In frame update
def onFrameStart(frame):
    # Get frequency bands from FrequencyBands.tox
    bands_op = op('FrequencyBands/bands8')
    band_data = [bands_op[i] for i in range(8)]

    # Detect kick
    result = detector.detect_kick(band_data)

    if result['triggered']:
        print(f"Kick! Strength: {result['strength']}")
```

## CHOP Execute DAT Template

```python
def onValueChange(channel, sampleIndex, val, prev):
    """Execute on CHOP value change."""

    # Only trigger on rising edge
    if val > prev and val > 0.5:

        channel_name = channel.name
        strength = val

        # Route to appropriate handler
        if 'kick' in channel_name:
            op('audio_visualizer').par.Kicktrigger.pulse()

        elif 'snare' in channel_name:
            op('audio_visualizer').par.Snaretrigger.pulse()

        elif 'hihat' in channel_name:
            op('audio_visualizer').par.Hihattrigger.pulse()
```

## Tips
- **Kick**: Use lower threshold (0.25-0.35) and longer min interval (100-150ms)
- **Snare**: Use medium threshold (0.3-0.4) and medium interval (80-120ms)
- **Hi-Hat**: Use higher threshold (0.2-0.3) and short interval (40-60ms)
- **Adaptive mode**: Better for varying dynamics, but may miss quiet sections
- **Fixed mode**: More consistent, but may over-trigger in loud sections
- Test with different music styles and adjust accordingly

## Calibration Process
1. Play typical audio content
2. Monitor adaptive_threshold output
3. Adjust sensitivity so threshold sits just below average peaks
4. Test with quiet and loud sections
5. Fine-tune min_interval to prevent double triggers
