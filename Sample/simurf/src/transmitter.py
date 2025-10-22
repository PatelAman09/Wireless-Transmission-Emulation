import numpy as np
import struct


class Transmitter:
    def __init__(self, config):
        self.config = config
        self.sample_rate = config['transmitter']['sample_rate']
        self.carrier_freq = config['transmitter']['carrier_freq']
        self.symbol_rate = config['transmitter']['symbol_rate']
        self.samples_per_symbol = int(self.sample_rate / self.symbol_rate)

    def add_preamble(self, symbols):
        """Add synchronization preamble"""
        # BPSK preamble for better synchronization: alternating 1, -1
        preamble_length = 16
        preamble = [1, -1] * (preamble_length // 2)  # Alternating pattern
        preamble = [x * (1 + 1j) / np.sqrt(2) for x in preamble]  # Convert to complex

        # Add start frame delimiter
        sfd = [1, 1, -1, -1, 1, 1, -1, -1]  # Specific pattern
        sfd = [x * (1 + 1j) / np.sqrt(2) for x in sfd]

        return np.concatenate([preamble, sfd, symbols])

    def bytes_to_bits(self, data):
        """Convert bytes to list of bits"""
        bits = []
        for byte in data:
            bits.extend([(byte >> i) & 1 for i in range(7, -1, -1)])
        return bits

    def bits_to_symbols(self, bits):
        """Convert bits to QPSK symbols with proper padding"""
        # Ensure even number of bits
        if len(bits) % 2 != 0:
            bits.append(0)  # Add padding bit

        symbols = []
        for i in range(0, len(bits), 2):
            bit1, bit2 = bits[i], bits[i + 1]
            # QPSK mapping with normalized power
            if bit1 == 0 and bit2 == 0:
                symbol = (1 + 1j) / np.sqrt(2)
            elif bit1 == 0 and bit2 == 1:
                symbol = (1 - 1j) / np.sqrt(2)
            elif bit1 == 1 and bit2 == 0:
                symbol = (-1 + 1j) / np.sqrt(2)
            else:  # 1,1
                symbol = (-1 - 1j) / np.sqrt(2)
            symbols.append(symbol)

        return np.array(symbols)

    def create_pulse_filter(self, span=6):
        """Create raised cosine filter with reduced span for less delay"""
        t = np.arange(-span * self.samples_per_symbol, span * self.samples_per_symbol + 1)
        t_norm = t / self.samples_per_symbol

        # Raised cosine filter
        beta = 0.35  # Roll-off factor
        with np.errstate(divide='ignore', invalid='ignore'):
            sinc_part = np.sinc(t_norm)
            cos_part = np.cos(np.pi * beta * t_norm)
            denom = 1 - (2 * beta * t_norm) ** 2

            filter_taps = sinc_part * cos_part / denom
            filter_taps[np.isnan(filter_taps)] = 1.0  # Handle division by zero

        # Normalize filter energy
        filter_taps = filter_taps / np.sqrt(np.sum(filter_taps ** 2))
        return filter_taps

    def modulate(self, symbols):
        """Upsample and apply pulse shaping with proper delay handling"""
        # Upsample symbols
        upsampled = np.zeros(len(symbols) * self.samples_per_symbol, dtype=complex)
        upsampled[::self.samples_per_symbol] = symbols

        # Apply pulse shaping
        filter_taps = self.create_pulse_filter()

        # Use 'full' convolution and trim to maintain timing
        shaped_signal = np.convolve(upsampled, filter_taps, mode='full')

        # Trim to remove the filter transient at the beginning
        # Keep the main part of the signal
        trim_start = len(filter_taps) // 2
        trim_end = -(len(filter_taps) // 2)
        if trim_end == 0:
            trim_end = None

        shaped_signal = shaped_signal[trim_start:trim_end]

        return shaped_signal

    def add_carrier(self, baseband_signal):
        """Add carrier frequency"""
        t = np.arange(len(baseband_signal)) / self.sample_rate
        carrier = np.exp(2j * np.pi * self.carrier_freq * t)
        return baseband_signal * carrier

    def transmit(self, data):
        """Main transmission function"""
        print(f"Transmitter: Processing {len(data)} bytes: '{data.decode()}'")

        # Convert data to bits
        bits = self.bytes_to_bits(data)
        print(f"Transmitter: Generated {len(bits)} bits")

        # Convert to symbols
        symbols = self.bits_to_symbols(bits)
        print(f"Transmitter: Generated {len(symbols)} QPSK symbols")

        # Add preamble for synchronization
        symbols_with_preamble = self.add_preamble(symbols)
        print(f"Transmitter: Total symbols with preamble: {len(symbols_with_preamble)}")

        # Modulate
        baseband_signal = self.modulate(symbols_with_preamble)
        print(f"Transmitter: Baseband signal length = {len(baseband_signal)}")

        # Add carrier
        transmitted_signal = self.add_carrier(baseband_signal)

        return transmitted_signal, len(symbols)  # Return original symbol count for receiver
