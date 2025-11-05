"""
TouchDesigner Transient Detector
Real-time kick/hit detection for audio-reactive applications

Implements multiple detection algorithms:
- Energy-based detection (simple threshold)
- Spectral flux detection (frequency domain)
- Adaptive threshold detection (learns from audio)
"""

import collections
import time


class TransientDetector:
    """
    Detects transients (kicks, snares, hits) in audio signals.
    Provides multiple detection algorithms and callback support.
    """

    def __init__(self, threshold=0.3, sensitivity=0.5, min_interval_ms=100):
        """
        Initialize the transient detector.

        Args:
            threshold (float): Base detection threshold (0-1). Default: 0.3
            sensitivity (float): Detection sensitivity (0-1). Higher = more sensitive. Default: 0.5
            min_interval_ms (int): Minimum time between detections in milliseconds. Default: 100
        """
        self.threshold = threshold
        self.sensitivity = sensitivity
        self.min_interval_ms = min_interval_ms

        # State tracking
        self.last_trigger_time = 0
        self.is_triggered = False

        # Energy tracking
        self.current_energy = 0.0
        self.energy_history = collections.deque(maxlen=60)
        self.adaptive_threshold = threshold

        # Spectral flux tracking
        self.previous_spectrum = []
        self.spectral_flux = 0.0
        self.flux_history = collections.deque(maxlen=60)

        # Callbacks
        self.on_transient_callbacks = []

        # Statistics
        self.total_triggers = 0
        self.last_trigger_strength = 0.0

    def detect_energy_based(self, rms_level, peak_level):
        """
        Simple energy-based transient detection.
        Triggers when peak exceeds threshold.

        Args:
            rms_level (float): Current RMS level
            peak_level (float): Current peak level

        Returns:
            dict: Detection result with trigger status and strength
        """
        current_time = time.time() * 1000  # Convert to milliseconds

        # Check minimum interval
        time_since_last = current_time - self.last_trigger_time
        if time_since_last < self.min_interval_ms:
            return self._get_detection_result(False, 0.0)

        # Energy calculation
        self.current_energy = peak_level
        self.energy_history.append(self.current_energy)

        # Adaptive threshold
        if len(self.energy_history) > 10:
            avg_energy = sum(self.energy_history) / len(self.energy_history)
            self.adaptive_threshold = avg_energy + (self.threshold * self.sensitivity)

        # Detect transient
        triggered = peak_level > self.adaptive_threshold
        strength = peak_level / max(0.01, self.adaptive_threshold) if triggered else 0.0

        if triggered:
            self.last_trigger_time = current_time
            self.total_triggers += 1
            self.last_trigger_strength = strength
            self._fire_callbacks(strength, 'energy')

        return self._get_detection_result(triggered, strength)

    def detect_spectral_flux(self, frequency_data):
        """
        Spectral flux-based detection.
        Detects sudden changes in frequency spectrum (more accurate for complex audio).

        Args:
            frequency_data (list): Array of frequency magnitudes

        Returns:
            dict: Detection result with trigger status and strength
        """
        current_time = time.time() * 1000

        # Check minimum interval
        time_since_last = current_time - self.last_trigger_time
        if time_since_last < self.min_interval_ms:
            return self._get_detection_result(False, 0.0)

        # Initialize previous spectrum
        if not self.previous_spectrum:
            self.previous_spectrum = frequency_data.copy()
            return self._get_detection_result(False, 0.0)

        # Calculate spectral flux (sum of positive differences)
        flux = 0.0
        for i in range(min(len(frequency_data), len(self.previous_spectrum))):
            diff = frequency_data[i] - self.previous_spectrum[i]
            if diff > 0:
                flux += diff

        self.spectral_flux = flux
        self.flux_history.append(flux)

        # Adaptive threshold for flux
        if len(self.flux_history) > 10:
            avg_flux = sum(self.flux_history) / len(self.flux_history)
            flux_threshold = avg_flux * (1.0 + self.sensitivity)
        else:
            flux_threshold = self.threshold

        # Detect transient
        triggered = flux > flux_threshold
        strength = flux / max(0.01, flux_threshold) if triggered else 0.0

        if triggered:
            self.last_trigger_time = current_time
            self.total_triggers += 1
            self.last_trigger_strength = strength
            self._fire_callbacks(strength, 'spectral_flux')

        # Update previous spectrum
        self.previous_spectrum = frequency_data.copy()

        return self._get_detection_result(triggered, strength)

    def detect_band_transient(self, band_data, band_index=0):
        """
        Detect transient in a specific frequency band.
        Useful for kick (low), snare (mid), hi-hat (high) detection.

        Args:
            band_data (list): Array of frequency band magnitudes
            band_index (int): Index of band to monitor. Default: 0 (bass/kick)

        Returns:
            dict: Detection result with trigger status and strength
        """
        current_time = time.time() * 1000

        # Check minimum interval
        time_since_last = current_time - self.last_trigger_time
        if time_since_last < self.min_interval_ms:
            return self._get_detection_result(False, 0.0)

        if band_index >= len(band_data):
            return self._get_detection_result(False, 0.0)

        # Get band energy
        band_energy = band_data[band_index]
        self.energy_history.append(band_energy)

        # Adaptive threshold
        if len(self.energy_history) > 10:
            avg_energy = sum(self.energy_history) / len(self.energy_history)
            band_threshold = avg_energy + (self.threshold * self.sensitivity)
        else:
            band_threshold = self.threshold

        # Detect transient
        triggered = band_energy > band_threshold
        strength = band_energy / max(0.01, band_threshold) if triggered else 0.0

        if triggered:
            self.last_trigger_time = current_time
            self.total_triggers += 1
            self.last_trigger_strength = strength
            self._fire_callbacks(strength, f'band_{band_index}')

        return self._get_detection_result(triggered, strength)

    def detect_kick(self, band_data):
        """
        Specialized kick drum detection (monitors bass frequencies).

        Args:
            band_data (list): Array of frequency band magnitudes (8+ bands)

        Returns:
            dict: Detection result specific to kick drum
        """
        # Kick is typically in the first 2 bands (20-250 Hz)
        if len(band_data) < 2:
            return self._get_detection_result(False, 0.0)

        # Average the low bands
        kick_energy = (band_data[0] + band_data[1]) / 2.0

        # Use energy-based detection with kick energy
        current_time = time.time() * 1000
        time_since_last = current_time - self.last_trigger_time

        if time_since_last < self.min_interval_ms:
            return self._get_detection_result(False, 0.0)

        self.energy_history.append(kick_energy)

        if len(self.energy_history) > 10:
            avg_energy = sum(self.energy_history) / len(self.energy_history)
            kick_threshold = avg_energy + (self.threshold * self.sensitivity)
        else:
            kick_threshold = self.threshold

        triggered = kick_energy > kick_threshold
        strength = kick_energy / max(0.01, kick_threshold) if triggered else 0.0

        if triggered:
            self.last_trigger_time = current_time
            self.total_triggers += 1
            self.last_trigger_strength = strength
            self._fire_callbacks(strength, 'kick')

        return self._get_detection_result(triggered, strength)

    def detect_snare(self, band_data):
        """
        Specialized snare detection (monitors mid frequencies).

        Args:
            band_data (list): Array of frequency band magnitudes (8+ bands)

        Returns:
            dict: Detection result specific to snare
        """
        # Snare is typically in bands 2-4 (150-500 Hz) for 8-band
        if len(band_data) < 4:
            return self._get_detection_result(False, 0.0)

        snare_energy = (band_data[2] + band_data[3]) / 2.0

        current_time = time.time() * 1000
        time_since_last = current_time - self.last_trigger_time

        if time_since_last < self.min_interval_ms:
            return self._get_detection_result(False, 0.0)

        self.energy_history.append(snare_energy)

        if len(self.energy_history) > 10:
            avg_energy = sum(self.energy_history) / len(self.energy_history)
            snare_threshold = avg_energy + (self.threshold * self.sensitivity)
        else:
            snare_threshold = self.threshold

        triggered = snare_energy > snare_threshold
        strength = snare_energy / max(0.01, snare_threshold) if triggered else 0.0

        if triggered:
            self.last_trigger_time = current_time
            self.total_triggers += 1
            self.last_trigger_strength = strength
            self._fire_callbacks(strength, 'snare')

        return self._get_detection_result(triggered, strength)

    def detect_hihat(self, band_data):
        """
        Specialized hi-hat detection (monitors high frequencies).

        Args:
            band_data (list): Array of frequency band magnitudes (8+ bands)

        Returns:
            dict: Detection result specific to hi-hat
        """
        # Hi-hat is typically in the highest bands (5000+ Hz)
        if len(band_data) < 6:
            return self._get_detection_result(False, 0.0)

        hihat_energy = sum(band_data[-2:]) / 2.0  # Last 2 bands

        current_time = time.time() * 1000
        time_since_last = current_time - self.last_trigger_time

        if time_since_last < self.min_interval_ms:
            return self._get_detection_result(False, 0.0)

        self.energy_history.append(hihat_energy)

        if len(self.energy_history) > 10:
            avg_energy = sum(self.energy_history) / len(self.energy_history)
            hihat_threshold = avg_energy + (self.threshold * self.sensitivity)
        else:
            hihat_threshold = self.threshold

        triggered = hihat_energy > hihat_threshold
        strength = hihat_energy / max(0.01, hihat_threshold) if triggered else 0.0

        if triggered:
            self.last_trigger_time = current_time
            self.total_triggers += 1
            self.last_trigger_strength = strength
            self._fire_callbacks(strength, 'hihat')

        return self._get_detection_result(triggered, strength)

    def add_callback(self, callback_func):
        """
        Add a callback function to be called when transient is detected.

        Args:
            callback_func: Function with signature: callback(strength, detection_type)
        """
        if callback_func not in self.on_transient_callbacks:
            self.on_transient_callbacks.append(callback_func)

    def remove_callback(self, callback_func):
        """Remove a previously added callback function."""
        if callback_func in self.on_transient_callbacks:
            self.on_transient_callbacks.remove(callback_func)

    def _fire_callbacks(self, strength, detection_type):
        """Fire all registered callbacks."""
        for callback in self.on_transient_callbacks:
            try:
                callback(strength, detection_type)
            except Exception as e:
                print(f"Error in transient callback: {e}")

    def set_threshold(self, threshold):
        """Set the detection threshold (0-1)."""
        self.threshold = max(0.0, min(1.0, threshold))

    def set_sensitivity(self, sensitivity):
        """Set the detection sensitivity (0-1)."""
        self.sensitivity = max(0.0, min(1.0, sensitivity))

    def set_min_interval(self, interval_ms):
        """Set minimum interval between detections in milliseconds."""
        self.min_interval_ms = max(0, interval_ms)

    def reset(self):
        """Reset detector state and history."""
        self.last_trigger_time = 0
        self.is_triggered = False
        self.current_energy = 0.0
        self.energy_history.clear()
        self.flux_history.clear()
        self.previous_spectrum = []
        self.total_triggers = 0
        self.last_trigger_strength = 0.0

    def get_statistics(self):
        """Get detection statistics."""
        return {
            'total_triggers': self.total_triggers,
            'last_trigger_strength': self.last_trigger_strength,
            'current_threshold': self.adaptive_threshold,
            'avg_energy': sum(self.energy_history) / len(self.energy_history) if self.energy_history else 0.0
        }

    def _get_detection_result(self, triggered, strength):
        """Format detection result."""
        return {
            'triggered': triggered,
            'strength': strength,
            'time': time.time(),
            'threshold': self.adaptive_threshold
        }


class MultiTransientDetector:
    """
    Manages multiple transient detectors for different frequency bands.
    Allows simultaneous detection of kick, snare, hi-hat, etc.
    """

    def __init__(self):
        """Initialize multi-detector with presets for common instruments."""
        self.detectors = {
            'kick': TransientDetector(threshold=0.3, sensitivity=0.5, min_interval_ms=100),
            'snare': TransientDetector(threshold=0.35, sensitivity=0.6, min_interval_ms=80),
            'hihat': TransientDetector(threshold=0.25, sensitivity=0.7, min_interval_ms=50),
            'general': TransientDetector(threshold=0.3, sensitivity=0.5, min_interval_ms=100)
        }

    def detect_all(self, band_data):
        """
        Run all detectors and return results.

        Args:
            band_data (list): Array of frequency band magnitudes

        Returns:
            dict: Results from all detectors
        """
        return {
            'kick': self.detectors['kick'].detect_kick(band_data),
            'snare': self.detectors['snare'].detect_snare(band_data),
            'hihat': self.detectors['hihat'].detect_hihat(band_data),
            'general': self.detectors['general'].detect_band_transient(band_data, 0)
        }

    def get_detector(self, name):
        """Get a specific detector by name."""
        return self.detectors.get(name)

    def add_detector(self, name, detector):
        """Add a custom detector."""
        self.detectors[name] = detector

    def reset_all(self):
        """Reset all detectors."""
        for detector in self.detectors.values():
            detector.reset()
