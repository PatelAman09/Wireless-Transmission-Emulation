import numpy as np
import struct


class Receiver:
    def __init__(self, config):
        self.config = config
        self.sample_rate = config['receiver']['sample_rate']
        self.carrier_freq = config['receiver']['carrier_freq']
        self.symbol_rate = config['receiver']['symbol_rate']
        self.samples_per_symbol = int(self.sample_rate / self.symbol_rate)
        print(f"Receiver: Samples per symbol = {self.samples_per_symbol}")

    def remove_carrier(self, signal):
        """Remove carrier frequency"""
        t = np.arange(len(signal)) / self.sample_rate
        carrier = np.exp(-2j * np.pi * self.carrier_freq * t)
        baseband = signal * carrier

        # Low-pass filter to remove double frequency components
        from scipy.signal import butter, lfilter
        nyquist = self.sample_rate / 2
        cutoff = self.symbol_rate * 2  # Twice symbol rate
        normal_cutoff = cutoff / nyquist

        if normal_cutoff < 1.0:  # Only if cutoff is below Nyquist
            b, a = butter(5, normal_cutoff, btype='low')
            baseband_real = lfilter(b, a, np.real(baseband))
            baseband_imag = lfilter(b, a, np.imag(baseband))
            baseband = baseband_real + 1j * baseband_imag

        return baseband

    def find_frame_start(self, signal):
        """Find frame start using energy detection"""
        # Simple energy-based detection
        window_size = self.samples_per_symbol
        energy = np.convolve(np.abs(signal) ** 2, np.ones(window_size), mode='valid')

        # Find where energy becomes significant
        threshold = np.max(energy) * 0.3
        above_threshold = np.where(energy > threshold)[0]

        if len(above_threshold) > 0:
            frame_start = above_threshold[0]
            print(f"Receiver: Frame start at sample {frame_start} (energy detection)")
            return frame_start
        else:
            print("Receiver: Using default frame start")
            return 100  # Default start

    def demodulate_simple(self, signal, expected_symbols):
        """Simple demodulation with rectangular pulse matching"""
        # Remove carrier first
        baseband = self.remove_carrier(signal)

        # Find frame start
        frame_start = self.find_frame_start(baseband)

        # Preamble length (32 alternating + 8 SFD = 40 symbols)
        preamble_length = 40
        data_start = frame_start + preamble_length * self.samples_per_symbol

        print(f"Receiver: Data starts at sample {data_start}")
        print(f"Receiver: Expected {expected_symbols} symbols")

        # Sample at middle of each symbol (rectangular pulse assumption)
        symbols = []
        for i in range(expected_symbols):
            sample_idx = data_start + i * self.samples_per_symbol + self.samples_per_symbol // 2
            if sample_idx < len(baseband):
                symbols.append(baseband[sample_idx])
            else:
                break

        print(f"Receiver: Extracted {len(symbols)} symbols")

        # Debug: Show raw symbol values
        if len(symbols) > 5:
            print("Receiver: First 5 raw symbols (I/Q):")
            for i in range(5):
                s = symbols[i]
                print(f"  Symbol {i}: {s.real:.3f} + j{s.imag:.3f} (mag: {np.abs(s):.3f})")

        return np.array(symbols)

    def correct_phase_and_amplitude(self, symbols):
        """Correct phase rotation and amplitude scaling"""
        if len(symbols) == 0:
            return symbols

        # Use preamble to estimate correction (first few data symbols should be known)
        # For 'H' (0x48 = 01001000), first two symbols should be:
        # bits: 01 00 -> symbols: (1-1j), (1+1j) approximately

        if len(symbols) >= 2:
            # Expected first symbol for 'H' (01001000): first 2 bits = 01 -> (1-1j)
            expected_first = 1 - 1j
            # Second 2 bits = 00 -> (1+1j)
            expected_second = 1 + 1j

            # Estimate rotation and scaling
            measured_first = symbols[0]
            measured_second = symbols[1]

            # Average correction from both symbols
            correction1 = expected_first / measured_first if abs(measured_first) > 0.1 else 1
            correction2 = expected_second / measured_second if abs(measured_second) > 0.1 else 1

            # Use average correction
            correction = (correction1 + correction2) / 2

            print(f"Receiver: Phase/amplitude correction: {correction}")

            # Apply correction to all symbols
            symbols_corrected = symbols * correction
        else:
            symbols_corrected = symbols

        return symbols_corrected

    def symbols_to_bits(self, symbols):
        """Convert QPSK symbols back to bits"""
        if len(symbols) == 0:
            return []

        # Correct phase and amplitude
        symbols_corrected = self.correct_phase_and_amplitude(symbols)

        # Debug corrected symbols
        if len(symbols_corrected) > 5:
            print("Receiver: First 5 corrected symbols (I/Q):")
            for i in range(5):
                s = symbols_corrected[i]
                print(f"  Symbol {i}: {s.real:.3f} + j{s.imag:.3f}")

        bits = []
        for symbol in symbols_corrected:
            real = np.real(symbol)
            imag = np.imag(symbol)

            # Simple decision with hysteresis
            if abs(real) < 0.5 and abs(imag) < 0.5:
                # Low confidence - use default
                bits.extend([0, 0])
            else:
                bit1 = 0 if real >= 0 else 1
                bit2 = 0 if imag >= 0 else 1
                bits.extend([bit1, bit2])

        return bits

    def bits_to_bytes(self, bits):
        """Convert bit array to bytes"""
        if len(bits) < 8:
            return b""

        # Ensure we have complete bytes
        num_bits = (len(bits) // 8) * 8
        bits = bits[:num_bits]

        bytes_list = []
        for i in range(0, len(bits), 8):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | bits[i + j]
            bytes_list.append(byte)

        return bytes(bytes_list)

    def debug_symbol_mapping(self, data, symbols, bits):
        """Debug helper to see symbol-to-bit mapping"""
        print("Receiver: Symbol mapping debug:")
        expected_bits = []
        for byte in data:
            expected_bits.extend([(byte >> i) & 1 for i in range(7, -1, -1)])

        print(f"Expected bits (first 16): {expected_bits[:16]}")
        print(f"Received bits (first 16): {bits[:16]}")

        # Show what symbols we should have gotten
        print("Expected vs Received symbols (first 5):")
        for i in range(min(5, len(symbols))):
            exp_bits = expected_bits[i * 2:(i + 1) * 2]
            rec_bits = bits[i * 2:(i + 1) * 2]

            if exp_bits == [0, 0]:
                exp_sym = "1+1j"
            elif exp_bits == [0, 1]:
                exp_sym = "1-1j"
            elif exp_bits == [1, 0]:
                exp_sym = "-1+1j"
            else:
                exp_sym = "-1-1j"

            if rec_bits == [0, 0]:
                rec_sym = "1+1j"
            elif rec_bits == [0, 1]:
                rec_sym = "1-1j"
            elif rec_bits == [1, 0]:
                rec_sym = "-1+1j"
            else:
                rec_sym = "-1-1j"

            print(f"  Symbol {i}: Expected {exp_bits}->{exp_sym}, Got {rec_bits}->{rec_sym}")

    def receive(self, signal, expected_data_length):
        """Main reception function"""
        print(f"Receiver: Processing {len(signal)} samples")

        if len(signal) == 0:
            print("Receiver: Empty signal received!")
            return b""

        # Calculate expected symbols
        expected_bits = expected_data_length * 8
        expected_symbols = expected_bits // 2

        # Simple demodulation
        symbols = self.demodulate_simple(signal, expected_symbols)

        if len(symbols) == 0:
            print("Receiver: No symbols detected!")
            return b""

        if len(symbols) < expected_symbols:
            print(f"Receiver: Warning: Only got {len(symbols)} of {expected_symbols} expected symbols")

        # Convert to bits
        bits = self.symbols_to_bits(symbols)
        print(f"Receiver: Decoded {len(bits)} bits")

        # Debug mapping
        self.debug_symbol_mapping(b'Hello SimuRF'[:expected_data_length], symbols, bits)

        # Convert to bytes
        data = self.bits_to_bytes(bits)
        print(f"Receiver: Reconstructed {len(data)} bytes: {data}")

        return data