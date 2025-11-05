PROJECT: Python module for TouchDesigner that replicates web audio analysis patterns

REQUIREMENTS:
- CHOP-based audio analysis matching Web Audio API FFT behavior
- Frequency band extraction (8-band, 16-band, 32-band options)
- Transient/kick detection algorithm
- RMS and peak level tracking
- Python class structure for easy instantiation
- DAT-based parameter control
- Real-time visualization in TouchDesigner UI
- Export analysis data to OSC/UDP for external applications
- MIDI CC output for hardware control

TECHNICAL IMPLEMENTATION:
- Use Audio Analysis CHOP, Audio Spectrum CHOP
- Math CHOPs for band isolation and smoothing
- Python callbacks for event-driven transient detection
- Select CHOP for band routing
- Cache recent analysis for temporal effects
- Configurable attack/release envelopes

COMPONENTS TO BUILD:
1. AudioAnalyzer.py - Main analysis class
2. FrequencyBands.tox - Reusable CHOP network
3. TransientDetector.tox - Kick/hit detection
4. MIDIMapper.tox - Map analysis to MIDI CC
5. OSCExporter.tox - Send data over network
6. VisualizerHUD.tox - Debug/monitoring panel

DELIVERABLES:
- Complete .toe project file with examples
- Python modules in /project1/scripts/
- Reusable .tox components
- Parameter documentation
- Comparison chart: Web Audio API ↔ TouchDesigner equivalents

FILE STRUCTURE:
/td-audio-bridge/
  AudioAnalysisBridge.toe
  /scripts/
    audio_analyzer.py
    transient_detector.py
    midi_router.py
    osc_exporter.py
  /toxes/
    FrequencyBands.tox
    TransientDetector.tox
    MIDIMapper.tox
  /examples/
    basic_visualization.toe
    midi_control_demo.toe
  README.md