"""
TouchDesigner MIDI Router
Maps audio analysis data to MIDI CC messages for hardware control

Provides flexible routing from audio features (RMS, peaks, bands, transients)
to MIDI CC messages with scaling, smoothing, and range mapping.
"""

import collections


class MIDIRouter:
    """
    Routes audio analysis data to MIDI CC messages.
    Handles scaling, range mapping, and smoothing.
    """

    def __init__(self):
        """Initialize the MIDI router."""
        self.mappings = {}
        self.last_values = {}
        self.smoothing_buffers = {}

    def add_mapping(self, name, cc_number, channel=1, min_value=0, max_value=127,
                    input_min=0.0, input_max=1.0, smoothing=0.0, invert=False):
        """
        Add a mapping from audio data to MIDI CC.

        Args:
            name (str): Unique name for this mapping
            cc_number (int): MIDI CC number (0-127)
            channel (int): MIDI channel (1-16). Default: 1
            min_value (int): Minimum MIDI value (0-127). Default: 0
            max_value (int): Maximum MIDI value (0-127). Default: 127
            input_min (float): Minimum expected input value. Default: 0.0
            input_max (float): Maximum expected input value. Default: 1.0
            smoothing (float): Smoothing factor (0-1, 0=no smoothing). Default: 0.0
            invert (bool): Invert the mapping. Default: False
        """
        self.mappings[name] = {
            'cc_number': max(0, min(127, cc_number)),
            'channel': max(1, min(16, channel)),
            'min_value': max(0, min(127, min_value)),
            'max_value': max(0, min(127, max_value)),
            'input_min': input_min,
            'input_max': input_max,
            'smoothing': max(0.0, min(1.0, smoothing)),
            'invert': invert,
            'enabled': True
        }
        self.smoothing_buffers[name] = collections.deque(maxlen=10)
        self.last_values[name] = 0

    def remove_mapping(self, name):
        """Remove a mapping by name."""
        if name in self.mappings:
            del self.mappings[name]
            del self.last_values[name]
            del self.smoothing_buffers[name]

    def map_value(self, name, input_value):
        """
        Map an input value to MIDI CC based on the named mapping.

        Args:
            name (str): Name of the mapping to use
            input_value (float): Input value to map

        Returns:
            dict: MIDI message with cc_number, channel, value
        """
        if name not in self.mappings:
            return None

        mapping = self.mappings[name]

        if not mapping['enabled']:
            return None

        # Normalize input to 0-1 range
        normalized = (input_value - mapping['input_min']) / (mapping['input_max'] - mapping['input_min'])
        normalized = max(0.0, min(1.0, normalized))

        # Invert if needed
        if mapping['invert']:
            normalized = 1.0 - normalized

        # Apply smoothing
        if mapping['smoothing'] > 0:
            self.smoothing_buffers[name].append(normalized)
            if len(self.smoothing_buffers[name]) > 0:
                smoothed = sum(self.smoothing_buffers[name]) / len(self.smoothing_buffers[name])
                normalized = (mapping['smoothing'] * self.last_values[name] +
                              (1 - mapping['smoothing']) * smoothed)

        # Scale to MIDI range
        midi_range = mapping['max_value'] - mapping['min_value']
        midi_value = int(mapping['min_value'] + (normalized * midi_range))
        midi_value = max(mapping['min_value'], min(mapping['max_value'], midi_value))

        self.last_values[name] = normalized

        return {
            'cc_number': mapping['cc_number'],
            'channel': mapping['channel'],
            'value': midi_value,
            'normalized': normalized
        }

    def map_multiple(self, mappings_dict):
        """
        Map multiple values at once.

        Args:
            mappings_dict (dict): Dictionary of {mapping_name: input_value}

        Returns:
            list: List of MIDI messages
        """
        messages = []
        for name, value in mappings_dict.items():
            msg = self.map_value(name, value)
            if msg is not None:
                messages.append(msg)
        return messages

    def enable_mapping(self, name):
        """Enable a mapping."""
        if name in self.mappings:
            self.mappings[name]['enabled'] = True

    def disable_mapping(self, name):
        """Disable a mapping."""
        if name in self.mappings:
            self.mappings[name]['enabled'] = False

    def get_mapping(self, name):
        """Get mapping configuration."""
        return self.mappings.get(name)

    def get_all_mappings(self):
        """Get all mapping configurations."""
        return self.mappings.copy()

    def clear_all(self):
        """Clear all mappings."""
        self.mappings.clear()
        self.last_values.clear()
        self.smoothing_buffers.clear()


class MIDIPresets:
    """
    Common MIDI CC mapping presets for audio-reactive applications.
    """

    @staticmethod
    def create_band_mapping(router, num_bands=8, start_cc=20, channel=1):
        """
        Create mappings for frequency bands to sequential MIDI CCs.

        Args:
            router (MIDIRouter): MIDIRouter instance
            num_bands (int): Number of bands (8, 16, or 32). Default: 8
            start_cc (int): Starting CC number. Default: 20
            channel (int): MIDI channel. Default: 1
        """
        for i in range(num_bands):
            router.add_mapping(
                name=f'band_{i}',
                cc_number=start_cc + i,
                channel=channel,
                min_value=0,
                max_value=127,
                input_min=0.0,
                input_max=1.0,
                smoothing=0.3
            )

    @staticmethod
    def create_level_mapping(router, channel=1):
        """
        Create standard level mappings (RMS, Peak, Envelope).

        Args:
            router (MIDIRouter): MIDIRouter instance
            channel (int): MIDI channel. Default: 1
        """
        router.add_mapping('rms', cc_number=1, channel=channel, smoothing=0.5)
        router.add_mapping('peak', cc_number=2, channel=channel, smoothing=0.3)
        router.add_mapping('envelope', cc_number=3, channel=channel, smoothing=0.2)

    @staticmethod
    def create_transient_mapping(router, channel=1):
        """
        Create mappings for transient detections.

        Args:
            router (MIDIRouter): MIDIRouter instance
            channel (int): MIDI channel. Default: 1
        """
        router.add_mapping('kick', cc_number=10, channel=channel, smoothing=0.1)
        router.add_mapping('snare', cc_number=11, channel=channel, smoothing=0.1)
        router.add_mapping('hihat', cc_number=12, channel=channel, smoothing=0.1)

    @staticmethod
    def create_full_preset(router, channel=1):
        """
        Create a complete preset with bands, levels, and transients.

        Args:
            router (MIDIRouter): MIDIRouter instance
            channel (int): MIDI channel. Default: 1
        """
        MIDIPresets.create_level_mapping(router, channel)
        MIDIPresets.create_band_mapping(router, num_bands=8, start_cc=20, channel=channel)
        MIDIPresets.create_transient_mapping(router, channel)


class MIDINoteMapper:
    """
    Maps transient detections to MIDI note on/off messages.
    Useful for triggering drum samples or instruments.
    """

    def __init__(self):
        """Initialize the note mapper."""
        self.note_mappings = {}
        self.active_notes = set()

    def add_note_mapping(self, name, note_number, channel=1, velocity_min=64, velocity_max=127):
        """
        Add a mapping from transient to MIDI note.

        Args:
            name (str): Unique name for this mapping (e.g., 'kick', 'snare')
            note_number (int): MIDI note number (0-127)
            channel (int): MIDI channel (1-16). Default: 1
            velocity_min (int): Minimum velocity (0-127). Default: 64
            velocity_max (int): Maximum velocity (0-127). Default: 127
        """
        self.note_mappings[name] = {
            'note': max(0, min(127, note_number)),
            'channel': max(1, min(16, channel)),
            'velocity_min': max(0, min(127, velocity_min)),
            'velocity_max': max(0, min(127, velocity_max)),
            'enabled': True
        }

    def trigger_note(self, name, strength=1.0, duration_frames=10):
        """
        Trigger a MIDI note based on transient detection.

        Args:
            name (str): Name of the note mapping
            strength (float): Transient strength (0-1) affects velocity
            duration_frames (int): How long to hold the note. Default: 10

        Returns:
            dict: MIDI note on message, or None if mapping doesn't exist
        """
        if name not in self.note_mappings:
            return None

        mapping = self.note_mappings[name]

        if not mapping['enabled']:
            return None

        # Calculate velocity based on strength
        velocity_range = mapping['velocity_max'] - mapping['velocity_min']
        velocity = int(mapping['velocity_min'] + (strength * velocity_range))
        velocity = max(mapping['velocity_min'], min(mapping['velocity_max'], velocity))

        note_key = (mapping['note'], mapping['channel'])
        self.active_notes.add(note_key)

        return {
            'type': 'note_on',
            'note': mapping['note'],
            'channel': mapping['channel'],
            'velocity': velocity,
            'duration_frames': duration_frames
        }

    def release_note(self, name):
        """
        Release a MIDI note.

        Args:
            name (str): Name of the note mapping

        Returns:
            dict: MIDI note off message
        """
        if name not in self.note_mappings:
            return None

        mapping = self.note_mappings[name]
        note_key = (mapping['note'], mapping['channel'])

        if note_key in self.active_notes:
            self.active_notes.remove(note_key)

        return {
            'type': 'note_off',
            'note': mapping['note'],
            'channel': mapping['channel'],
            'velocity': 0
        }

    def release_all_notes(self):
        """Release all active notes."""
        messages = []
        for note, channel in list(self.active_notes):
            messages.append({
                'type': 'note_off',
                'note': note,
                'channel': channel,
                'velocity': 0
            })
        self.active_notes.clear()
        return messages

    def get_active_notes(self):
        """Get list of currently active notes."""
        return list(self.active_notes)


class DrumMachineMapper:
    """
    Specialized mapper for drum machine style MIDI note mapping.
    Uses General MIDI drum note assignments.
    """

    # General MIDI Drum Map
    GM_DRUM_MAP = {
        'kick': 36,          # Bass Drum 1
        'kick_2': 35,        # Bass Drum 2
        'snare': 38,         # Acoustic Snare
        'snare_2': 40,       # Electric Snare
        'clap': 39,          # Hand Clap
        'hihat_closed': 42,  # Closed Hi-Hat
        'hihat_open': 46,    # Open Hi-Hat
        'hihat_pedal': 44,   # Pedal Hi-Hat
        'tom_low': 45,       # Low Tom
        'tom_mid': 47,       # Mid Tom
        'tom_high': 50,      # High Tom
        'crash': 49,         # Crash Cymbal
        'ride': 51,          # Ride Cymbal
        'rim': 37,           # Side Stick
        'cowbell': 56        # Cowbell
    }

    def __init__(self, channel=10):  # Channel 10 is standard for drums
        """
        Initialize drum machine mapper.

        Args:
            channel (int): MIDI channel (typically 10 for drums). Default: 10
        """
        self.note_mapper = MIDINoteMapper()
        self.channel = channel
        self._setup_drum_mappings()

    def _setup_drum_mappings(self):
        """Set up all drum note mappings."""
        for drum_name, note_number in self.GM_DRUM_MAP.items():
            self.note_mapper.add_note_mapping(
                name=drum_name,
                note_number=note_number,
                channel=self.channel,
                velocity_min=80,
                velocity_max=127
            )

    def trigger_drum(self, drum_name, strength=1.0):
        """
        Trigger a drum sound.

        Args:
            drum_name (str): Name from GM_DRUM_MAP
            strength (float): Hit strength (0-1)

        Returns:
            dict: MIDI note message
        """
        return self.note_mapper.trigger_note(drum_name, strength, duration_frames=5)

    def get_available_drums(self):
        """Get list of available drum names."""
        return list(self.GM_DRUM_MAP.keys())
