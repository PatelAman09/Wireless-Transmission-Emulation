import numpy as np
import struct


class Transmitter:
    def __init__(self, config):
        self.config = config
        self.sample_rate = config['transmitter']['sample_rate']
        self.carrier_freq = config['transmitter']['carrier_freq']
        self.symbol_rate = config['transmitter']['symbol_rate']
        self.samples_per_symbol = int(self.sample_rate / self.symbol_rate)

    def bytes_to_bits(self, data):
        """Convert bytes to list of bits"""
        bits = []
        for byte in data:
            # Convert each byte to 8 bits (MSB first)
            bits.extend([(byte >> i) & 1 for i in range(7, -1, -1)])
        return bits

    def bits_to_symbols(self, bits):
        """Convert bits to QPSK symbols"""
        symbols = []
        # Ensure even number of bits for QPSK
        if len(bits) % 2 != 0:
            bits.append(0)  # Padding if odd number

        for i in range(0, len(bits), 2):
            bit1, bit2 = bits[i], bits[i + 1]
            # QPSK mapping with normalized power
            symbol_map = {
                (0, 0): (1 + 1j) / np.sqrt(2),
                (0, 1): (1 - 1j) / np.sqrt(2),
                (1, 0): (-1 + 1j) / np.sqrt(2),
                (1, 1): (-1 - 1j) / np.sqrt(2)
            }
            symbols.append(symbol_map[(bit1, bit2)])

        return np.array(symbols)

    def create_pulse_filter(self, span=8):
        """Create raised cosine filter"""
        t = np.arange(-span * self.samples_per_symbol, span * self.samples_per_symbol + 1)
        t_norm = t / self.samples_per_symbol

        # Avoid division by zero
        with np.errstate(divide='ignore', invalid='ignore'):
            sinc_part = np.sinc(t_norm)
            cos_part = np.cos(np.pi * 0.35 * t_norm)
            denom = 1 - (0.7 * t_norm) ** 2

            # Handle cases where denominator is zero
            filter_taps = sinc_part * cos_part / denom
            filter_taps[np.isnan(filter_taps)] = 1.0  # lim x->0: sin(x)/x = 1

        # Normalize filter
        filter_taps = filter_taps / np.sqrt(np.sum(filter_taps ** 2))
        return filter_taps

    def modulate(self, symbols):
        """Upsample and apply pulse shaping"""
        # Upsample symbols
        upsampled = np.zeros(len(symbols) * self.samples_per_symbol, dtype=complex)
        upsampled[::self.samples_per_symbol] = symbols

        # Apply pulse shaping
        filter_taps = self.create_pulse_filter()
        shaped_signal = np.convolve(upsampled, filter_taps, mode='same')

        return shaped_signal

    def add_carrier(self, baseband_signal):
        """Add carrier frequency"""
        t = np.arange(len(baseband_signal)) / self.sample_rate
        carrier = np.exp(2j * np.pi * self.carrier_freq * t)
        return baseband_signal * carrier

    def transmit(self, data):
        """Main transmission function"""
        print(f"Transmitter: Processing {len(data)} bytes")

        # Convert data to bits
        bits = self.bytes_to_bits(data)
        print(f"Transmitter: Generated {len(bits)} bits")

        # Convert to symbols
        symbols = self.bits_to_symbols(bits)
        print(f"Transmitter: Generated {len(symbols)} QPSK symbols")

        # Modulate
        baseband_signal = self.modulate(symbols)
        print(f"Transmitter: Baseband signal length = {len(baseband_signal)}")

        # Add carrier
        transmitted_signal = self.add_carrier(baseband_signal)

        return transmitted_signal