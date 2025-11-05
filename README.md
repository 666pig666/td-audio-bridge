# TouchDesigner Audio Analysis Bridge

A comprehensive Python module for TouchDesigner that replicates Web Audio API patterns for audio analysis, transient detection, MIDI routing, and OSC export.

## Overview

This project provides a complete audio-reactive framework for TouchDesigner, enabling sophisticated audio analysis and routing to external applications. It bridges the gap between TouchDesigner's CHOP-based audio system and familiar web audio paradigms.

### Key Features

- 🎵 **Web Audio API Compatible**: FFT analysis matching `AnalyserNode` behavior
- 📊 **Multi-Band Analysis**: 8, 16, and 32-band frequency analysis
- 🥁 **Transient Detection**: Kick, snare, hi-hat detection with multiple algorithms
- 🎹 **MIDI Integration**: CC mapping and Note On/Off with configurable routing
- 🌐 **OSC/UDP Export**: Send analysis data to external applications
- ⚡ **Real-Time Performance**: Optimized for 60fps+ operation
- 🎨 **Modular Design**: Use components independently or together

## Installation

1. Clone or download this repository into your TouchDesigner project directory
2. Import Python modules into your project:

```python
# In TouchDesigner, add the scripts folder to your Python path
import sys
sys.path.append('/path/to/td-audio-bridge/scripts')

from scripts.audio_analyzer import AudioAnalyzer
from scripts.transient_detector import TransientDetector
from scripts.midi_router import MIDIRouter
from scripts.osc_exporter import OSCExporter
```

## Quick Start

### Basic Audio Analysis

```python
from scripts.audio_analyzer import AudioAnalyzer

# Initialize analyzer
analyzer = AudioAnalyzer(fft_size=2048, smoothing_time_constant=0.8)

# In your frame callback
def onFrameStart(frame):
    # Get audio spectrum CHOP
    audio_spectrum = op('audiospectrumchop')

    # Analyze
    result = analyzer.analyze_chop(audio_spectrum)

    # Access data
    print(f"RMS: {result['rms']}")
    print(f"Peak: {result['peak']}")
    print(f"8 Bands: {result['bands']['8_band']}")
```

### Kick Detection

```python
from scripts.transient_detector import TransientDetector

detector = TransientDetector(threshold=0.3, sensitivity=0.5)

def on_kick(strength, detection_type):
    print(f"KICK! Strength: {strength}")
    op('visualizer').par.Trigger.pulse()

detector.add_callback(on_kick)

# In frame callback
result = detector.detect_kick(band_data)
```

### MIDI Control

```python
from scripts.midi_router import MIDIRouter, MIDIPresets

router = MIDIRouter()
MIDIPresets.create_band_mapping(router, num_bands=8, start_cc=20)

# Map audio data to MIDI
messages = router.map_multiple({
    'band_0': bass_level,
    'band_1': mid_level
})

# Send MIDI
for msg in messages:
    op('midiout1').sendCC(msg['channel'], msg['cc_number'], msg['value'])
```

## Web Audio API ↔ TouchDesigner Equivalents

### Frequency Analysis

| Web Audio API | TouchDesigner | Notes |
|---------------|---------------|-------|
| `AnalyserNode` | `AudioAnalyzer` class | Main analysis interface |
| `fftSize` | `fft_size` parameter | Power of 2, typically 2048 |
| `smoothingTimeConstant` | `smoothing_time_constant` | 0-1 range, controls averaging |
| `frequencyBinCount` | `frequency_bin_count` | fftSize / 2 |
| `getByteFrequencyData()` | `analyze_chop()` | Returns frequency magnitudes |
| `getByteTimeDomainData()` | `time_domain_data` | Waveform data |

### Audio Context

| Web Audio API | TouchDesigner | Notes |
|---------------|---------------|-------|
| `AudioContext` | Audio Device In CHOP | System audio input |
| `createAnalyser()` | `AudioAnalyzer()` | Create analyzer instance |
| `createBiquadFilter()` | Filter CHOP | Frequency filtering |
| `createGain()` | Math CHOP (multiply) | Gain control |
| `sampleRate` | Audio Device sample rate | Typically 44100 or 48000 Hz |

### Code Comparison

#### Web Audio API
```javascript
// Web Audio API
const audioContext = new AudioContext();
const analyser = audioContext.createAnalyser();
analyser.fftSize = 2048;
analyser.smoothingTimeConstant = 0.8;

const dataArray = new Uint8Array(analyser.frequencyBinCount);

function analyze() {
  analyser.getByteFrequencyData(dataArray);

  // Get average for frequency range
  let sum = 0;
  for (let i = 0; i < dataArray.length; i++) {
    sum += dataArray[i];
  }
  let average = sum / dataArray.length;
}
```

#### TouchDesigner + This Module
```python
# TouchDesigner
from scripts.audio_analyzer import AudioAnalyzer

analyzer = AudioAnalyzer(fft_size=2048, smoothing_time_constant=0.8)

def analyze():
    audio_spectrum = op('audiospectrumchop')
    result = analyzer.analyze_chop(audio_spectrum)

    # Get average
    frequency_data = result['frequency_data']
    average = sum(frequency_data) / len(frequency_data)
```

## Module Documentation

### AudioAnalyzer

Main audio analysis class that replicates Web Audio API `AnalyserNode`.

#### Constructor
```python
AudioAnalyzer(fft_size=2048, smoothing_time_constant=0.8)
```

#### Methods
- `analyze_chop(chop_reference)` - Analyze audio from CHOP
- `get_frequency_range(min_freq, max_freq)` - Get magnitude for frequency range
- `get_history_average(frames=30)` - Get average RMS over time
- `set_attack_release(attack_ms, release_ms)` - Configure envelope follower
- `reset()` - Reset all analysis data

#### Returns
```python
{
    'frequency_data': [float],  # Raw frequency magnitudes
    'rms': float,               # Root mean square level
    'peak': float,              # Peak level
    'envelope': float,          # Envelope follower
    'bands': {
        '8_band': [float],      # 8 frequency bands
        '16_band': [float],     # 16 frequency bands
        '32_band': [float]      # 32 frequency bands
    }
}
```

### TransientDetector

Detects transients (kicks, snares, hits) in audio.

#### Constructor
```python
TransientDetector(threshold=0.3, sensitivity=0.5, min_interval_ms=100)
```

#### Methods
- `detect_energy_based(rms_level, peak_level)` - Simple energy detection
- `detect_spectral_flux(frequency_data)` - Spectral change detection
- `detect_kick(band_data)` - Specialized kick detection
- `detect_snare(band_data)` - Specialized snare detection
- `detect_hihat(band_data)` - Specialized hi-hat detection
- `add_callback(callback_func)` - Add detection callback

#### Callback Signature
```python
def on_transient(strength: float, detection_type: str):
    # strength: 0-1+ normalized detection strength
    # detection_type: 'kick', 'snare', 'hihat', etc.
    pass
```

### MIDIRouter

Maps audio data to MIDI CC and Note messages.

#### Constructor
```python
MIDIRouter()
```

#### Methods
- `add_mapping(name, cc_number, channel=1, ...)` - Add CC mapping
- `map_value(name, input_value)` - Map single value
- `map_multiple(mappings_dict)` - Map multiple values
- `enable_mapping(name)` / `disable_mapping(name)` - Toggle mappings

#### Presets
```python
from scripts.midi_router import MIDIPresets

# Create 8-band mapping (CC 20-27)
MIDIPresets.create_band_mapping(router, num_bands=8, start_cc=20)

# Create level mappings (RMS, Peak, Envelope)
MIDIPresets.create_level_mapping(router, channel=1)

# Create transient note mapping
MIDIPresets.create_transient_mapping(router, channel=1)
```

### OSCExporter

Export audio data over OSC/UDP.

#### Constructor
```python
OSCExporter(host='127.0.0.1', port=7000)
```

#### Methods
- `send_message(address, *values)` - Send OSC message
- `send_analysis_data(analysis_result)` - Send complete analysis
- `send_band_data(band_data, num_bands=8)` - Send frequency bands
- `send_transient(transient_type, strength)` - Send transient event
- `set_address_prefix(prefix)` - Set OSC address prefix

#### OSC Address Map
```
/audio/rms                    - RMS level
/audio/peak                   - Peak level
/audio/envelope               - Envelope follower
/audio/band/8/[0-7]          - 8-band spectrum
/audio/band/16/[0-15]        - 16-band spectrum
/audio/band/32/[0-31]        - 32-band spectrum
/audio/transient/kick        - Kick detection
/audio/transient/snare       - Snare detection
/audio/transient/hihat       - Hi-hat detection
```

## TouchDesigner Component Build Guides

Pre-built component templates are documented in the `toxes/` folder:

- **FrequencyBands.tox** - Multi-band frequency analyzer
- **TransientDetector.tox** - Real-time transient detection
- **MIDIMapper.tox** - Audio to MIDI routing

See individual build guides for CHOP network construction details.

## Examples

The `examples/` folder contains complete working examples:

### 1. Basic Setup (`basic_setup.py`)
- Simple audio analysis
- RMS/Peak tracking
- 8-band frequency analysis
- Basic kick detection

### 2. MIDI Control (`midi_control_example.py`)
- Complete MIDI CC mapping
- Drum machine note mapping
- Transient-to-MIDI-note conversion
- Hardware/software integration

### 3. OSC Export (`osc_export_example.py`)
- OSC message sending
- Multi-destination support
- Processing/Max/MSP receiver examples

### 4. Full Integration (`full_integration_example.py`)
- Combined analysis, MIDI, and OSC
- Callbacks and event handling
- Statistics logging
- Complete audio-reactive system

## Frequency Band Presets

### EQ Bands
```python
from scripts.audio_analyzer import FrequencyBandPresets

# Standard EQ bands
bands = FrequencyBandPresets.EQ_BANDS
# {'sub_bass': (20, 60), 'bass': (60, 250), ...}
```

### Musical Instrument Ranges
```python
# Get frequency range for kick drum
kick_range = FrequencyBandPresets.INSTRUMENT_RANGES['kick']  # (40, 100)
kick_energy = analyzer.get_frequency_range(kick_range[0], kick_range[1])
```

### Available Presets
- `EQ_BANDS` - Standard 7-band EQ
- `INSTRUMENT_RANGES` - Musical instrument frequency ranges
- `OCTAVE_BANDS` - ISO standard octave bands

## Performance Considerations

### Frame Rate
- Optimized for 60fps operation
- FFT size affects performance (2048 recommended)
- History buffers default to 60 frames (1 second)

### Smoothing
- Lower values (0.1-0.3): More responsive, more jitter
- Medium values (0.4-0.6): Balanced
- Higher values (0.7-0.9): Smoother, more latency

### Memory Usage
- Each `AudioAnalyzer` instance: ~50KB
- History buffers: ~10KB per analyzer
- MIDI router mappings: Minimal (~1KB per 100 mappings)

## Hardware Integration

### Supported MIDI Devices
- USB MIDI controllers
- MIDI interfaces
- DAW software (Ableton, FL Studio, etc.)
- Hardware synthesizers

### Supported OSC Applications
- Processing
- Max/MSP
- Pure Data
- Resolume Arena/Avenue
- VDMX
- MadMapper
- Any OSC-compatible software

## Troubleshooting

### No Audio Analysis
1. Verify Audio Device In CHOP is receiving audio
2. Check Audio Spectrum CHOP has resolution > 0
3. Ensure CHOP is cooking (green flag)

### MIDI Not Sending
1. Verify MIDI Out DAT is configured
2. Check MIDI device is connected
3. Test with MIDI monitor software

### OSC Not Receiving
1. Verify IP address and port
2. Check firewall settings
3. Test with OSC monitoring software (oscplot, OSCulator)

### Transients Not Detecting
1. Adjust threshold (lower = more sensitive)
2. Increase sensitivity parameter
3. Check min_interval_ms (may be too long)
4. Verify frequency bands have sufficient energy

## Advanced Usage

### Custom Detection Algorithms
```python
class CustomDetector(TransientDetector):
    def detect_custom(self, data):
        # Your custom algorithm
        pass
```

### Multi-Destination OSC
```python
from scripts.osc_exporter import MulticastExporter

multicast = MulticastExporter()
multicast.add_osc_destination('processing', '127.0.0.1', 8000)
multicast.add_osc_destination('resolume', '192.168.1.100', 7001)

multicast.send_to_all('analysis', analysis_result)
```

### MIDI Learn System
```python
# Implement MIDI learn for dynamic CC mapping
def midi_learn_mode(cc_number, audio_parameter):
    router.add_mapping(
        name=f'learned_{cc_number}',
        cc_number=cc_number,
        input_min=0.0,
        input_max=1.0
    )
```

## API Reference

Full API documentation is available in the source code docstrings. Use Python's `help()` function:

```python
from scripts import audio_analyzer
help(audio_analyzer.AudioAnalyzer)
```

## Contributing

This is an open-source project. Contributions are welcome!

### Areas for Contribution
- Additional transient detection algorithms
- More MIDI presets
- OSC bundle optimization
- Additional frequency band presets
- Example projects

## License

MIT License - See LICENSE file for details

## Credits

Developed for the TouchDesigner community. Based on Web Audio API specifications and common audio analysis patterns.

## Version History

- **v1.0.0** - Initial release
  - Audio analysis with Web Audio API compatibility
  - Transient detection (kick, snare, hi-hat)
  - MIDI CC and Note mapping
  - OSC/UDP export
  - Complete documentation and examples

## Support

For questions and support:
1. Check the examples in `/examples/`
2. Review the build guides in `/toxes/`
3. Open an issue on GitHub

---

**Made with ❤️ for the TouchDesigner community**
