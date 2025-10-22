import numpy as np
import struct


class Receiver:
    def __init__(self, config):
        self.config = config
        self.sample_rate = config['receiver']['sample_rate']
        self.carrier_freq = config['receiver']['carrier_freq']
        self.symbol_rate = config['receiver']['symbol_rate']
        self.samples_per_symbol = int(self.sample_rate / self.symbol_rate)

    def remove_carrier(self, signal):
        """Remove carrier frequency"""
        t = np.arange(len(signal)) / self.sample_rate
        carrier = np.exp(-2j * np.pi * self.carrier_freq * t)
        return signal * carrier

    def create_matched_filter(self, span=8):
        """Create matched filter (same as transmitter filter)"""
        t = np.arange(-span * self.samples_per_symbol, span * self.samples_per_symbol + 1)
        t_norm = t / self.samples_per_symbol

        with np.errstate(divide='ignore', invalid='ignore'):
            sinc_part = np.sinc(t_norm)
            cos_part = np.cos(np.pi * 0.35 * t_norm)
            denom = 1 - (0.7 * t_norm) ** 2

            filter_taps = sinc_part * cos_part / denom
            filter_taps[np.isnan(filter_taps)] = 1.0

        filter_taps = filter_taps / np.sqrt(np.sum(filter_taps ** 2))
        return filter_taps

    def demodulate(self, signal):
        """Demodulate and downsample to symbols"""
        # Remove carrier
        baseband = self.remove_carrier(signal)

        # Apply matched filter
        filter_taps = self.create_matched_filter()
        filtered = np.convolve(baseband, filter_taps, mode='same')

        # Find optimal sampling point (middle of symbol)
        sample_offset = len(filter_taps) // 2
        symbols = filtered[sample_offset::self.samples_per_symbol]

        # Remove edge effects
        symbols = symbols[8:-8] if len(symbols) > 16 else symbols

        return symbols

    def symbols_to_bits(self, symbols):
        """Convert QPSK symbols back to bits"""
        bits = []
        for symbol in symbols:
            # Decision based on quadrant
            real = np.real(symbol)
            imag = np.imag(symbol)

            if real >= 0 and imag >= 0:
                bits.extend([0, 0])
            elif real >= 0 and imag < 0:
                bits.extend([0, 1])
            elif real < 0 and imag >= 0:
                bits.extend([1, 0])
            else:
                bits.extend([1, 1])

        return bits

    def bits_to_bytes(self, bits):
        """Convert bit array to bytes"""
        # Ensure multiple of 8 bits
        if len(bits) % 8 != 0:
            bits = bits[:-(len(bits) % 8)]

        bytes_list = []
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | bits[i + j]
            bytes_list.append(byte)

        return bytes(bytes_list)

    def receive(self, signal):
        """Main reception function"""
        print(f"Receiver: Processing {len(signal)} samples")

        # Demodulate
        symbols = self.demodulate(signal)
        print(f"Receiver: Demodulated {len(symbols)} symbols")

        if len(symbols) == 0:
            print("Receiver: No symbols detected!")
            return b""

        # Convert to bits
        bits = self.symbols_to_bits(symbols)
        print(f"Receiver: Decoded {len(bits)} bits")

        # Convert to bytes
        data = self.bits_to_bytes(bits)
        print(f"Receiver: Reconstructed {len(data)} bytes")

        return data