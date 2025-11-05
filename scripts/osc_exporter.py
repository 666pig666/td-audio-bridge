"""
TouchDesigner OSC Exporter
Export audio analysis data over OSC/UDP for external applications

Supports flexible OSC message routing and formatting.
Compatible with Processing, Max/MSP, Ableton Live, and other OSC-enabled software.
"""

import struct
import socket
import time


class OSCMessage:
    """
    Simple OSC message builder.
    Creates properly formatted OSC messages according to OSC 1.0 spec.
    """

    @staticmethod
    def encode_string(s):
        """Encode a string for OSC (null-terminated, 4-byte aligned)."""
        s = s.encode('utf-8') + b'\x00'
        padding = (4 - (len(s) % 4)) % 4
        return s + (b'\x00' * padding)

    @staticmethod
    def encode_int(i):
        """Encode an integer for OSC."""
        return struct.pack('>i', int(i))

    @staticmethod
    def encode_float(f):
        """Encode a float for OSC."""
        return struct.pack('>f', float(f))

    @staticmethod
    def build_message(address, *args):
        """
        Build an OSC message.

        Args:
            address (str): OSC address (e.g., '/audio/rms')
            *args: Values to send (int, float, or str)

        Returns:
            bytes: Formatted OSC message
        """
        # Encode address
        msg = OSCMessage.encode_string(address)

        # Build type tag string
        type_tags = ','
        arg_data = b''

        for arg in args:
            if isinstance(arg, int):
                type_tags += 'i'
                arg_data += OSCMessage.encode_int(arg)
            elif isinstance(arg, float):
                type_tags += 'f'
                arg_data += OSCMessage.encode_float(arg)
            elif isinstance(arg, str):
                type_tags += 's'
                arg_data += OSCMessage.encode_string(arg)
            else:
                # Default to float
                type_tags += 'f'
                arg_data += OSCMessage.encode_float(float(arg))

        # Encode type tags
        msg += OSCMessage.encode_string(type_tags)

        # Add argument data
        msg += arg_data

        return msg


class OSCExporter:
    """
    Export audio analysis data over OSC/UDP.
    """

    def __init__(self, host='127.0.0.1', port=7000):
        """
        Initialize OSC exporter.

        Args:
            host (str): Target IP address. Default: '127.0.0.1'
            port (int): Target UDP port. Default: 7000
        """
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.enabled = True
        self.address_prefix = '/audio'

        # Statistics
        self.messages_sent = 0
        self.last_send_time = 0

    def send_message(self, address, *values):
        """
        Send an OSC message.

        Args:
            address (str): OSC address (will be prefixed with address_prefix)
            *values: Values to send

        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            return False

        try:
            # Build full address
            full_address = f"{self.address_prefix}{address}"

            # Build and send message
            message = OSCMessage.build_message(full_address, *values)
            self.socket.sendto(message, (self.host, self.port))

            self.messages_sent += 1
            self.last_send_time = time.time()
            return True

        except Exception as e:
            print(f"OSC send error: {e}")
            return False

    def send_analysis_data(self, analysis_result):
        """
        Send complete audio analysis data.

        Args:
            analysis_result (dict): Result from AudioAnalyzer.analyze_chop()

        Returns:
            int: Number of messages sent
        """
        if not self.enabled or not analysis_result:
            return 0

        messages_sent = 0

        # Send level data
        if self.send_message('/rms', analysis_result.get('rms', 0.0)):
            messages_sent += 1

        if self.send_message('/peak', analysis_result.get('peak', 0.0)):
            messages_sent += 1

        if self.send_message('/envelope', analysis_result.get('envelope', 0.0)):
            messages_sent += 1

        # Send frequency bands
        bands = analysis_result.get('bands', {})

        if '8_band' in bands:
            for i, value in enumerate(bands['8_band']):
                if self.send_message(f'/band/8/{i}', value):
                    messages_sent += 1

        return messages_sent

    def send_band_data(self, band_data, num_bands=8):
        """
        Send frequency band data.

        Args:
            band_data (list): List of band magnitudes
            num_bands (int): Number of bands. Default: 8

        Returns:
            int: Number of messages sent
        """
        if not self.enabled:
            return 0

        messages_sent = 0

        for i, value in enumerate(band_data[:num_bands]):
            if self.send_message(f'/band/{i}', value):
                messages_sent += 1

        return messages_sent

    def send_transient(self, transient_type, strength):
        """
        Send transient detection event.

        Args:
            transient_type (str): Type of transient ('kick', 'snare', etc.)
            strength (float): Detection strength

        Returns:
            bool: True if sent successfully
        """
        return self.send_message(f'/transient/{transient_type}', strength)

    def send_bundle(self, messages):
        """
        Send multiple OSC messages as a bundle (all sent together).

        Args:
            messages (list): List of (address, values) tuples

        Returns:
            int: Number of messages sent
        """
        if not self.enabled:
            return 0

        count = 0
        for address, *values in messages:
            if self.send_message(address, *values):
                count += 1

        return count

    def set_destination(self, host, port):
        """
        Change OSC destination.

        Args:
            host (str): Target IP address
            port (int): Target UDP port
        """
        self.host = host
        self.port = port

    def set_address_prefix(self, prefix):
        """
        Set the address prefix for all messages.

        Args:
            prefix (str): Address prefix (e.g., '/myapp/audio')
        """
        self.address_prefix = prefix if prefix.startswith('/') else f'/{prefix}'

    def enable(self):
        """Enable OSC sending."""
        self.enabled = True

    def disable(self):
        """Disable OSC sending."""
        self.enabled = False

    def get_statistics(self):
        """Get sending statistics."""
        return {
            'messages_sent': self.messages_sent,
            'last_send_time': self.last_send_time,
            'enabled': self.enabled,
            'destination': f"{self.host}:{self.port}"
        }

    def reset_statistics(self):
        """Reset statistics."""
        self.messages_sent = 0
        self.last_send_time = 0

    def close(self):
        """Close the socket."""
        try:
            self.socket.close()
        except:
            pass


class UDPExporter:
    """
    Simple UDP exporter for raw data (non-OSC).
    Useful for custom protocols or simple string-based communication.
    """

    def __init__(self, host='127.0.0.1', port=8000):
        """
        Initialize UDP exporter.

        Args:
            host (str): Target IP address. Default: '127.0.0.1'
            port (int): Target UDP port. Default: 8000
        """
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.enabled = True
        self.messages_sent = 0

    def send_string(self, data):
        """
        Send a string over UDP.

        Args:
            data (str): String to send

        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            return False

        try:
            self.socket.sendto(data.encode('utf-8'), (self.host, self.port))
            self.messages_sent += 1
            return True
        except Exception as e:
            print(f"UDP send error: {e}")
            return False

    def send_bytes(self, data):
        """
        Send raw bytes over UDP.

        Args:
            data (bytes): Bytes to send

        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            return False

        try:
            self.socket.sendto(data, (self.host, self.port))
            self.messages_sent += 1
            return True
        except Exception as e:
            print(f"UDP send error: {e}")
            return False

    def send_json(self, data_dict):
        """
        Send JSON-formatted data over UDP.

        Args:
            data_dict (dict): Dictionary to send as JSON

        Returns:
            bool: True if sent successfully
        """
        import json
        try:
            json_str = json.dumps(data_dict)
            return self.send_string(json_str)
        except Exception as e:
            print(f"JSON encode error: {e}")
            return False

    def send_csv(self, values):
        """
        Send comma-separated values over UDP.

        Args:
            values (list): List of values to send

        Returns:
            bool: True if sent successfully
        """
        csv_str = ','.join(str(v) for v in values)
        return self.send_string(csv_str)

    def set_destination(self, host, port):
        """Change UDP destination."""
        self.host = host
        self.port = port

    def enable(self):
        """Enable UDP sending."""
        self.enabled = True

    def disable(self):
        """Disable UDP sending."""
        self.enabled = False

    def close(self):
        """Close the socket."""
        try:
            self.socket.close()
        except:
            pass


class MulticastExporter:
    """
    Export data to multiple destinations simultaneously.
    Useful for sending audio data to multiple applications.
    """

    def __init__(self):
        """Initialize multicast exporter."""
        self.exporters = {}

    def add_osc_destination(self, name, host, port):
        """
        Add an OSC destination.

        Args:
            name (str): Unique name for this destination
            host (str): Target IP address
            port (int): Target UDP port
        """
        self.exporters[name] = {
            'type': 'osc',
            'exporter': OSCExporter(host, port),
            'enabled': True
        }

    def add_udp_destination(self, name, host, port):
        """
        Add a UDP destination.

        Args:
            name (str): Unique name for this destination
            host (str): Target IP address
            port (int): Target UDP port
        """
        self.exporters[name] = {
            'type': 'udp',
            'exporter': UDPExporter(host, port),
            'enabled': True
        }

    def remove_destination(self, name):
        """Remove a destination."""
        if name in self.exporters:
            self.exporters[name]['exporter'].close()
            del self.exporters[name]

    def send_to_all(self, data_type, data):
        """
        Send data to all enabled destinations.

        Args:
            data_type (str): Type of data ('analysis', 'band', 'transient', etc.)
            data: Data to send (format depends on data_type)

        Returns:
            int: Number of successful sends
        """
        success_count = 0

        for name, dest in self.exporters.items():
            if not dest['enabled']:
                continue

            exporter = dest['exporter']

            try:
                if dest['type'] == 'osc':
                    if data_type == 'analysis':
                        exporter.send_analysis_data(data)
                        success_count += 1
                    elif data_type == 'transient':
                        exporter.send_transient(data.get('type'), data.get('strength'))
                        success_count += 1

                elif dest['type'] == 'udp':
                    if isinstance(data, dict):
                        exporter.send_json(data)
                    else:
                        exporter.send_string(str(data))
                    success_count += 1

            except Exception as e:
                print(f"Error sending to {name}: {e}")

        return success_count

    def enable_destination(self, name):
        """Enable a destination."""
        if name in self.exporters:
            self.exporters[name]['enabled'] = True

    def disable_destination(self, name):
        """Disable a destination."""
        if name in self.exporters:
            self.exporters[name]['enabled'] = False

    def get_destinations(self):
        """Get list of destination names."""
        return list(self.exporters.keys())

    def close_all(self):
        """Close all exporters."""
        for dest in self.exporters.values():
            dest['exporter'].close()
