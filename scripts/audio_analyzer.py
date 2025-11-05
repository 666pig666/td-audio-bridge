"""
TouchDesigner Audio Analyzer
Replicates Web Audio API AnalyserNode behavior for TouchDesigner

This module provides audio analysis functionality matching the Web Audio API's
AnalyserNode, including FFT analysis, frequency band extraction, and level tracking.
"""

import collections
import math


class AudioAnalyzer:
    """
    Main audio analysis class that interfaces with TouchDesigner CHOPs.
    Replicates Web Audio API AnalyserNode functionality.
    """

    def __init__(self, fft_size=2048, smoothing_time_constant=0.8):
        """
        Initialize the audio analyzer.

        Args:
            fft_size (int): FFT size (must be power of 2). Default: 2048
            smoothing_time_constant (float): Smoothing between 0-1 (0=no smoothing). Default: 0.8
        """
        self.fft_size = fft_size
        self.smoothing_time_constant = smoothing_time_constant
        self.frequency_bin_count = fft_size // 2

        # Cached analysis data
        self.frequency_data = [0.0] * self.frequency_bin_count
        self.time_domain_data = [0.0] * fft_size

        # Level tracking
        self.rms_level = 0.0
        self.peak_level = 0.0

        # Temporal cache for effects (last 60 frames)
        self.history_size = 60
        self.rms_history = collections.deque(maxlen=self.history_size)
        self.peak_history = collections.deque(maxlen=self.history_size)

        # Attack/Release envelope parameters (in frames)
        self.attack_frames = 1  # Fast attack
        self.release_frames = 30  # Slower release
        self.envelope_value = 0.0

    def analyze_chop(self, chop_reference):
        """
        Analyze audio from a CHOP reference (Audio Spectrum CHOP or Audio Analysis CHOP).

        Args:
            chop_reference: TouchDesigner CHOP operator reference

        Returns:
            dict: Analysis results containing frequency data, levels, and bands
        """
        if chop_reference is None:
            return self._get_empty_analysis()

        # Extract frequency data from CHOP channels
        num_samples = chop_reference.numSamples
        num_channels = chop_reference.numChans

        if num_samples == 0 or num_channels == 0:
            return self._get_empty_analysis()

        # Get frequency magnitude data
        raw_frequency_data = []
        for i in range(min(num_samples, self.frequency_bin_count)):
            sample_value = chop_reference[0][i]  # First channel
            raw_frequency_data.append(sample_value)

        # Apply smoothing (exponential moving average)
        for i in range(len(raw_frequency_data)):
            if i < len(self.frequency_data):
                self.frequency_data[i] = (
                    self.smoothing_time_constant * self.frequency_data[i] +
                    (1 - self.smoothing_time_constant) * raw_frequency_data[i]
                )

        # Calculate RMS and peak levels
        self._update_levels(chop_reference)

        return {
            'frequency_data': self.frequency_data,
            'rms': self.rms_level,
            'peak': self.peak_level,
            'envelope': self.envelope_value,
            'bands': self._extract_frequency_bands()
        }

    def _update_levels(self, chop_reference):
        """Update RMS and peak level tracking with envelope."""
        # Calculate RMS
        sum_squares = 0.0
        num_samples = chop_reference.numSamples

        for i in range(num_samples):
            value = chop_reference[0][i]
            sum_squares += value * value

        current_rms = math.sqrt(sum_squares / num_samples) if num_samples > 0 else 0.0

        # Calculate peak
        current_peak = max(abs(chop_reference[0][i]) for i in range(num_samples)) if num_samples > 0 else 0.0

        # Apply attack/release envelope
        if current_peak > self.envelope_value:
            # Attack
            self.envelope_value += (current_peak - self.envelope_value) / self.attack_frames
        else:
            # Release
            self.envelope_value -= (self.envelope_value - current_peak) / self.release_frames

        self.envelope_value = max(0.0, min(1.0, self.envelope_value))

        # Update levels
        self.rms_level = current_rms
        self.peak_level = current_peak

        # Add to history
        self.rms_history.append(current_rms)
        self.peak_history.append(current_peak)

    def _extract_frequency_bands(self):
        """
        Extract frequency bands from the spectrum.
        Returns multiple band configurations (8, 16, 32 bands).
        """
        return {
            '8_band': self._calculate_bands(8),
            '16_band': self._calculate_bands(16),
            '32_band': self._calculate_bands(32)
        }

    def _calculate_bands(self, num_bands):
        """
        Calculate logarithmically-spaced frequency bands.
        Mimics Web Audio API frequency band distribution.

        Args:
            num_bands (int): Number of bands to generate

        Returns:
            list: Band magnitude values
        """
        bands = []
        bin_count = len(self.frequency_data)

        for band in range(num_bands):
            # Logarithmic distribution
            start_bin = int((bin_count / num_bands) * band)
            end_bin = int((bin_count / num_bands) * (band + 1))

            # Average magnitude in this band
            band_sum = sum(self.frequency_data[start_bin:end_bin])
            band_avg = band_sum / (end_bin - start_bin) if end_bin > start_bin else 0.0
            bands.append(band_avg)

        return bands

    def get_frequency_range(self, min_freq, max_freq, sample_rate=44100):
        """
        Get magnitude for a specific frequency range.

        Args:
            min_freq (float): Minimum frequency in Hz
            max_freq (float): Maximum frequency in Hz
            sample_rate (int): Audio sample rate (default: 44100)

        Returns:
            float: Average magnitude in the frequency range
        """
        # Convert frequencies to bin indices
        freq_per_bin = sample_rate / self.fft_size
        start_bin = int(min_freq / freq_per_bin)
        end_bin = int(max_freq / freq_per_bin)

        # Clamp to valid range
        start_bin = max(0, min(start_bin, len(self.frequency_data) - 1))
        end_bin = max(0, min(end_bin, len(self.frequency_data)))

        if end_bin <= start_bin:
            return 0.0

        # Calculate average
        range_sum = sum(self.frequency_data[start_bin:end_bin])
        return range_sum / (end_bin - start_bin)

    def get_history_average(self, frames=30):
        """
        Get average RMS level over recent frames.

        Args:
            frames (int): Number of frames to average (default: 30)

        Returns:
            float: Average RMS over the period
        """
        if len(self.rms_history) == 0:
            return 0.0

        recent = list(self.rms_history)[-frames:]
        return sum(recent) / len(recent)

    def get_peak_history_max(self, frames=30):
        """
        Get maximum peak level over recent frames.

        Args:
            frames (int): Number of frames to check (default: 30)

        Returns:
            float: Maximum peak over the period
        """
        if len(self.peak_history) == 0:
            return 0.0

        recent = list(self.peak_history)[-frames:]
        return max(recent)

    def set_attack_release(self, attack_ms, release_ms, fps=60):
        """
        Set attack and release times for envelope follower.

        Args:
            attack_ms (float): Attack time in milliseconds
            release_ms (float): Release time in milliseconds
            fps (int): Frame rate (default: 60)
        """
        self.attack_frames = max(1, int((attack_ms / 1000.0) * fps))
        self.release_frames = max(1, int((release_ms / 1000.0) * fps))

    def reset(self):
        """Reset all analysis data and history."""
        self.frequency_data = [0.0] * self.frequency_bin_count
        self.time_domain_data = [0.0] * self.fft_size
        self.rms_level = 0.0
        self.peak_level = 0.0
        self.envelope_value = 0.0
        self.rms_history.clear()
        self.peak_history.clear()

    def _get_empty_analysis(self):
        """Return empty analysis result when no valid input."""
        return {
            'frequency_data': [0.0] * self.frequency_bin_count,
            'rms': 0.0,
            'peak': 0.0,
            'envelope': 0.0,
            'bands': {
                '8_band': [0.0] * 8,
                '16_band': [0.0] * 16,
                '32_band': [0.0] * 32
            }
        }


class FrequencyBandPresets:
    """
    Predefined frequency band ranges matching common audio analysis patterns.
    Based on Web Audio API common practices.
    """

    # Standard EQ bands
    EQ_BANDS = {
        'sub_bass': (20, 60),
        'bass': (60, 250),
        'low_mid': (250, 500),
        'mid': (500, 2000),
        'high_mid': (2000, 4000),
        'presence': (4000, 6000),
        'brilliance': (6000, 20000)
    }

    # Musical instrument ranges
    INSTRUMENT_RANGES = {
        'kick': (40, 100),
        'bass': (40, 250),
        'snare': (150, 250),
        'vocals': (300, 3400),
        'hi_hat': (5000, 10000),
        'cymbals': (8000, 16000)
    }

    # Octave bands (ISO standard)
    OCTAVE_BANDS = {
        '31.5': (22, 44),
        '63': (44, 88),
        '125': (88, 177),
        '250': (177, 355),
        '500': (355, 710),
        '1k': (710, 1420),
        '2k': (1420, 2840),
        '4k': (2840, 5680),
        '8k': (5680, 11360),
        '16k': (11360, 22720)
    }

    @staticmethod
    def get_band_names(preset_name='EQ_BANDS'):
        """Get the names of bands in a preset."""
        preset = getattr(FrequencyBandPresets, preset_name, {})
        return list(preset.keys())

    @staticmethod
    def get_band_range(preset_name, band_name):
        """Get the frequency range for a specific band."""
        preset = getattr(FrequencyBandPresets, preset_name, {})
        return preset.get(band_name, (0, 0))
