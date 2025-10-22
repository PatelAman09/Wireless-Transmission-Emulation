import numpy as np
import struct


class Transmitter:
    def __init__(self, config):
        self.config = config
        self.sample_rate = config['transmitter']['sample_rate']
        self.carrier_freq = config['transmitter']['carrier_freq']
        self.symbol_rate = config['transmitter']['symbol_rate']
        self.samples_per_symbol = int(self.sample_rate / self.symbol_rate)
        print(f"Transmitter: Samples per symbol = {self.samples_per_symbol}")

    def add_preamble(self, symbols):
        """Add simple but effective preamble"""
        # Use alternating 1,-1 pattern for easy detection
        preamble_length = 32
        preamble = []
        for i in range(preamble_length):
            if i % 2 == 0:
                preamble.append(1.0 + 0j)  # Real only for preamble
            else:
                preamble.append(-1.0 + 0j)

        # Simple SFD pattern
        sfd = [1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0]  # Repeated pattern
        sfd = [x + 0j for x in sfd]

        full_preamble = np.concatenate([preamble, sfd])
        print(f"Transmitter: Added preamble of {len(full_preamble)} symbols")

        return np.concatenate([full_preamble, symbols])

    def bytes_to_bits(self, data):
        """Convert bytes to list of bits"""
        bits = []
        for byte in data:
            bits.extend([(byte >> i) & 1 for i in range(7, -1, -1)])
        return bits

    def bits_to_symbols(self, bits):
        """Convert bits to QPSK symbols with simple mapping"""
        # Ensure even number of bits
        if len(bits) % 2 != 0:
            bits.append(0)

        symbols = []
        for i in range(0, len(bits), 2):
            bit1, bit2 = bits[i], bits[i + 1]

            # Simple QPSK mapping (no normalization yet)
            if bit1 == 0 and bit2 == 0:
                symbol = 1 + 1j  # 45°
            elif bit1 == 0 and bit2 == 1:
                symbol = 1 - 1j  # 315°
            elif bit1 == 1 and bit2 == 0:
                symbol = -1 + 1j  # 135°
            else:  # 1,1
                symbol = -1 - 1j  # 225°
            symbols.append(symbol)

        symbols = np.array(symbols)
        # Normalize to unit power
        rms = np.sqrt(np.mean(np.abs(symbols) ** 2))
        symbols = symbols / rms
        print(f"Transmitter: Symbol RMS power: {np.sqrt(np.mean(np.abs(symbols) ** 2)):.3f}")
        return symbols

    def create_pulse_filter(self):
        """Create simple rectangular pulse for debugging"""
        # Use rectangular pulses for now to avoid filter issues
        filter_taps = np.ones(self.samples_per_symbol)
        filter_taps = filter_taps / np.sqrt(np.sum(filter_taps ** 2))
        print(f"Transmitter: Using rectangular pulse, {len(filter_taps)} taps")
        return filter_taps

    def modulate(self, symbols):
        """Simple modulation with rectangular pulses"""
        # Upsample symbols (zero-order hold)
        upsampled = np.zeros(len(symbols) * self.samples_per_symbol, dtype=complex)
        for i in range(len(symbols)):
            start_idx = i * self.samples_per_symbol
            end_idx = start_idx + self.samples_per_symbol
            upsampled[start_idx:end_idx] = symbols[i]

        print(f"Transmitter: After upsampling: {len(upsampled)} samples")
        return upsampled

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

        # Debug: Show first few symbols and their expected bits
        print("Transmitter: First 5 data symbols (expected):")
        for i in range(min(5, len(symbols))):
            expected_bits = bits[i * 2:(i + 1) * 2]
            print(f"  Symbol {i}: bits {expected_bits} -> {symbols[i]}")

        # Add preamble for synchronization
        symbols_with_preamble = self.add_preamble(symbols)
        print(f"Transmitter: Total symbols with preamble: {len(symbols_with_preamble)}")

        # Modulate with simple rectangular pulses
        baseband_signal = self.modulate(symbols_with_preamble)

        # Add carrier
        transmitted_signal = self.add_carrier(baseband_signal)

        print(f"Transmitter: Final signal length = {len(transmitted_signal)} samples")

        return transmitted_signal, len(symbols)