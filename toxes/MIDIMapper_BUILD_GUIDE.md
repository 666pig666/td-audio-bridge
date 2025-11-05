# MIDIMapper.tox - Build Guide

## Overview
Maps audio analysis data to MIDI CC messages and Note On/Off events. Includes range scaling, smoothing, and preset configurations.

## CHOP Network Structure

### Inputs
- **datain**: Multi-channel CHOP with audio analysis data
- **triggersin**: Binary triggers for note events

### Core Components

#### 1. MIDI CC Mapping Path

**Select CHOP (Channel Selector)**
- Input: datain
- Channels: User-defined selection
- Purpose: Select which channels to map

**Math CHOP (Range Remap)**
- Input: Selected channels
- From Range: 0 to 1 (normalized input)
- To Range: 0 to 127 (MIDI range)
- Operation: Clamp

**Math CHOP (Smoothing)**
- Input: Remapped values
- Operation: Lag
- Lag: Custom parameter (0-1)
- Purpose: Smooth rapid changes

**CHOP Execute DAT (MIDI Send)**
- Monitors smoothed output
- Sends MIDI CC on value change
- Uses TouchDesigner MIDI Out DAT

#### 2. MIDI Note Mapping Path

**CHOP Execute DAT (Note Trigger)**
- Input: triggersin
- Monitors: Rising edge (0 → 1)
- Action: Send MIDI Note On
- Auto Note Off: After duration

**Timer CHOP (Note Duration)**
- Trigger: Note On event
- Length: Custom parameter (default: 100ms)
- Output: Triggers Note Off

### MIDI Out DAT

**Configuration:**
```
MIDI Device: [Select from menu]
Channel: 1-16
Send Real-time: On
```

**CC Message Format:**
```
Type: Control Change
Number: [Parameter-defined CC number]
Value: [0-127 from CHOP]
Channel: [Parameter-defined channel]
```

**Note Message Format:**
```
Type: Note On/Off
Note: [Parameter-defined note number]
Velocity: [0-127 from strength]
Channel: [Parameter-defined channel]
```

### Custom Parameters

#### CC Mapping Parameters (per channel)
- **CC Number**: Integer (0-127) - MIDI CC number
- **MIDI Channel**: Integer (1-16) - MIDI channel
- **Input Min**: Float - Minimum expected input
- **Input Max**: Float - Maximum expected input
- **Output Min**: Integer (0-127) - Minimum MIDI value
- **Output Max**: Integer (0-127) - Maximum MIDI value
- **Smoothing**: Float (0-1) - Lag amount
- **Invert**: Toggle - Invert the mapping
- **Enabled**: Toggle - Enable/disable this mapping

#### Note Mapping Parameters (per trigger)
- **Note Number**: Integer (0-127) - MIDI note
- **MIDI Channel**: Integer (1-16)
- **Velocity Min**: Integer (0-127)
- **Velocity Max**: Integer (0-127)
- **Note Duration**: Integer (ms)
- **Enabled**: Toggle

#### Preset Configurations
- **Load Preset**: Menu (8-Band, 16-Band, Drum Machine, Custom)
- **Save Preset**: Button - Save current config
- **Reset All**: Button - Clear all mappings

### Python Extension (midi_handler.py)

```python
from scripts import midi_router

class MIDIHandler:
    def __init__(self, ownerComp):
        self.ownerComp = ownerComp
        self.router = midi_router.MIDIRouter()
        self._setup_mappings()

    def _setup_mappings(self):
        """Initialize MIDI mappings from parameters."""
        # Add CC mappings
        for i in range(8):
            cc_num = self.ownerComp.par[f'Ccnumber{i}'].eval()
            channel = self.ownerComp.par[f'Channel{i}'].eval()
            smoothing = self.ownerComp.par[f'Smoothing{i}'].eval()

            self.router.add_mapping(
                name=f'band_{i}',
                cc_number=cc_num,
                channel=channel,
                smoothing=smoothing
            )

    def process_frame(self, chop_data):
        """Process CHOP data and generate MIDI messages."""
        messages = []

        for i, channel in enumerate(chop_data.chans()):
            value = channel.vals[0]
            msg = self.router.map_value(f'band_{i}', value)
            if msg:
                messages.append(msg)

        return messages

    def send_midi_cc(self, cc_number, channel, value):
        """Send MIDI CC message via TouchDesigner."""
        midi_out = op('midiout1')
        midi_out.sendCC(channel, cc_number, value)

    def send_midi_note(self, note, channel, velocity):
        """Send MIDI Note On message."""
        midi_out = op('midiout1')
        midi_out.sendNoteOn(channel, note, velocity)

    def send_note_off(self, note, channel):
        """Send MIDI Note Off message."""
        midi_out = op('midiout1')
        midi_out.sendNoteOff(channel, note, 0)
```

### CHOP Execute DAT (CC Sender)

```python
def onValueChange(channel, sampleIndex, val, prev):
    """Send MIDI CC when value changes."""

    # Get mapping configuration
    mapper = parent().par.Midihandler.eval()

    if mapper is None:
        return

    # Get channel index
    chan_index = int(channel.name.replace('band_', ''))

    # Get CC number and MIDI channel from parameters
    cc_num = parent().par[f'Ccnumber{chan_index}'].eval()
    midi_chan = parent().par[f'Channel{chan_index}'].eval()

    # Convert to MIDI range (0-127)
    midi_val = int(val * 127)
    midi_val = max(0, min(127, midi_val))

    # Send MIDI
    op('midiout1').sendCC(midi_chan, cc_num, midi_val)
```

### CHOP Execute DAT (Note Trigger)

```python
def onValueChange(channel, sampleIndex, val, prev):
    """Trigger MIDI notes on transient detection."""

    # Detect rising edge
    if val > prev and val > 0.5:

        trigger_name = channel.name

        # Map trigger to note
        note_map = {
            'kick_trigger': 36,   # GM Kick
            'snare_trigger': 38,  # GM Snare
            'hihat_trigger': 42   # GM Hi-Hat
        }

        if trigger_name in note_map:
            note = note_map[trigger_name]
            velocity = int(val * 127)
            channel = 10  # Drum channel

            # Send Note On
            op('midiout1').sendNoteOn(channel, note, velocity)

            # Schedule Note Off
            run("op('midiout1').sendNoteOff(10, {}, 0)".format(note),
                delayFrames=10)
```

## Preset Configurations

### 8-Band Preset
Maps 8 frequency bands to CC 20-27:
- CC 20: Band 0 (Sub Bass)
- CC 21: Band 1 (Bass)
- CC 22: Band 2 (Low Mid)
- CC 23: Band 3 (Mid)
- CC 24: Band 4 (High Mid)
- CC 25: Band 5 (Presence)
- CC 26: Band 6 (Brilliance)
- CC 27: Band 7 (Air)

### Drum Machine Preset
Maps transients to GM Drum Notes on Channel 10:
- Note 36: Kick
- Note 38: Snare
- Note 42: Closed Hi-Hat
- Note 46: Open Hi-Hat

### Level Monitoring Preset
Maps audio levels to standard CCs:
- CC 1: RMS Level (Mod Wheel)
- CC 2: Peak Level
- CC 3: Envelope Follower
- CC 7: Master Volume (based on RMS)

## Table DAT Configuration

**mapping_config.txt** (DAT table):
```
name        cc_num  channel  in_min  in_max  out_min  out_max  smoothing  invert
band_0      20      1        0.0     1.0     0        127      0.3        0
band_1      21      1        0.0     1.0     0        127      0.3        0
band_2      22      1        0.0     1.0     0        127      0.3        0
rms         1       1        0.0     0.5     0        127      0.5        0
peak        2       1        0.0     1.0     0        127      0.2        0
```

Load configuration:
```python
def load_config():
    config_dat = op('mapping_config')
    mapper = parent.Midimapper.MIDIHandler

    for row in range(1, config_dat.numRows):
        name = config_dat[row, 'name'].val
        cc_num = int(config_dat[row, 'cc_num'].val)
        channel = int(config_dat[row, 'channel'].val)
        smoothing = float(config_dat[row, 'smoothing'].val)

        mapper.router.add_mapping(
            name=name,
            cc_number=cc_num,
            channel=channel,
            smoothing=smoothing
        )
```

## Usage Example

```python
# Setup
from scripts import midi_router

router = midi_router.MIDIRouter()

# Add frequency band mappings
midi_router.MIDIPresets.create_band_mapping(router, num_bands=8, start_cc=20)

# In frame update
def onFrameStart(frame):
    # Get band data
    bands_op = op('FrequencyBands/bands8')
    band_data = {f'band_{i}': bands_op[i] for i in range(8)}

    # Map to MIDI
    messages = router.map_multiple(band_data)

    # Send via MIDI Out
    for msg in messages:
        op('midiout1').sendCC(
            msg['channel'],
            msg['cc_number'],
            msg['value']
        )
```

## Hardware Integration

### Ableton Live
1. Enable MIDI Remote in Preferences
2. Map TouchDesigner as Control Surface
3. Use MIDI Learn to bind CCs to parameters

### VJ Software (Resolume, etc.)
1. Enable MIDI input
2. Map CCs to layer opacity, effects, etc.
3. Use transient notes to trigger clips

### Hardware Synthesizers
1. Connect via USB MIDI or MIDI interface
2. Configure synth to receive on specified channel
3. Map CCs to filter cutoff, resonance, etc.

## Tips
- Use smoothing (0.3-0.5) for CC values to prevent jitter
- Use less smoothing (0.1-0.2) for transient triggers
- Test MIDI output with MIDI Monitor software
- Save presets for different performance scenarios
- Use MIDI channel routing to control multiple devices
