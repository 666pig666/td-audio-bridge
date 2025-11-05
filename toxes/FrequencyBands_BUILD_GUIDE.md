# FrequencyBands.tox - Build Guide

## Overview
This component provides multi-band frequency analysis with 8, 16, or 32 band configurations matching Web Audio API patterns.

## CHOP Network Structure

### Input
- **audioin**: Audio Signature CHOP input

### Core Components

1. **Audio Spectrum CHOP**
   - Input: audioin
   - Resolution: 2048
   - FFT Overlap: 75%
   - Output: Frequency spectrum (0-22050 Hz)

2. **Resample CHOP (for 8-band)**
   - Input: Audio Spectrum output
   - Method: Average
   - Samples: 8
   - Output: 8 frequency bands (logarithmic)

3. **Resample CHOP (for 16-band)**
   - Input: Audio Spectrum output
   - Method: Average
   - Samples: 16
   - Output: 16 frequency bands

4. **Resample CHOP (for 32-band)**
   - Input: Audio Spectrum output
   - Method: Average
   - Samples: 32
   - Output: 32 frequency bands

5. **Math CHOP (Smoothing)**
   - Input: Each band output
   - Operation: Lag
   - Lag: 0.3 (adjustable)
   - Purpose: Smooth out rapid fluctuations

6. **Math CHOP (Gain)**
   - Input: Smoothed bands
   - Operation: Multiply
   - Value: Custom parameter (default 2.0)
   - Purpose: Adjust overall sensitivity

### Parameters (Custom)
- **Bands**: Integer (8, 16, or 32) - Select number of bands
- **Smoothing**: Float (0-1) - Lag amount
- **Gain**: Float (0-10) - Output gain multiplier
- **Min Freq**: Float - Minimum frequency to analyze (default: 20 Hz)
- **Max Freq**: Float - Maximum frequency to analyze (default: 20000 Hz)

### Outputs
- **bands8**: 8-band output
- **bands16**: 16-band output
- **bands32**: 32-band output
- **selected**: Currently selected band configuration

## Web Audio API Equivalence

```javascript
// Web Audio API
const analyser = audioContext.createAnalyser();
analyser.fftSize = 2048;
analyser.smoothingTimeConstant = 0.3;

const dataArray = new Uint8Array(analyser.frequencyBinCount);
analyser.getByteFrequencyData(dataArray);
```

**TouchDesigner Equivalent:**
- `fftSize = 2048` → Audio Spectrum Resolution: 2048
- `smoothingTimeConstant = 0.3` → Math CHOP Lag: 0.3
- `getByteFrequencyData()` → bands8/16/32 output CHOPs

## Usage Example

```python
# In a TouchDesigner script
freq_bands = op('FrequencyBands')
bands = freq_bands.cook()

# Get 8-band data
for i in range(8):
    band_value = freq_bands['bands8'][i]
    print(f"Band {i}: {band_value}")
```

## Tips
- Use lower band counts (8) for rhythm analysis
- Use higher band counts (32) for detailed spectral analysis
- Adjust smoothing based on tempo (higher for slower, lower for faster)
- Connect to Null CHOP for cooking control
