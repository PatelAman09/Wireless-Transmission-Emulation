"""
utils/modulation.py
Modulation and demodulation schemes for digital communications
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


class ModulationSchemes:
    """Digital modulation and demodulation schemes"""

    def __init__(self):
        # 16-QAM constellation mapping
        self.qam16_constellation = np.array([
            -3 - 3j, -3 - 1j, -3 + 1j, -3 + 3j,
            -1 - 3j, -1 - 1j, -1 + 1j, -1 + 3j,
            +1 - 3j, +1 - 1j, +1 + 1j, +1 + 3j,
            +3 - 3j, +3 - 1j, +3 + 1j, +3 + 3j
        ]) / np.sqrt(10)  # Normalized for unit average power

        # Gray coding mapping for 16-QAM
        self.qam16_gray_map = {
            0: 0b0000, 1: 0b0001, 2: 0b0011, 3: 0b0010,
            4: 0b0100, 5: 0b0101, 6: 0b0111, 7: 0b0110,
            8: 0b1100, 9: 0b1101, 10: 0b1111, 11: 0b1110,
            12: 0b1000, 13: 0b1001, 14: 0b1011, 15: 0b1010
        }

        # Reverse mapping for demodulation
        self.qam16_gray_demap = {v: k for k, v in self.qam16_gray_map.items()}

    def bpsk_modulate(self, bits: np.ndarray) -> np.ndarray:
        """
        Binary Phase Shift Keying modulation

        Args:
            bits: Input bit array

        Returns:
            Complex BPSK symbols
        """
        # Map 0 -> +1, 1 -> -1
        symbols = 1 - 2 * bits.astype(float)
        return symbols.astype(complex)

    def bpsk_demodulate(self, symbols: np.ndarray) -> np.ndarray:
        """
        BPSK demodulation using hard decision

        Args:
            symbols: Received complex symbols

        Returns:
            Demodulated bits
        """
        # Take real part and make hard decision
        bits = (np.real(symbols) < 0).astype(np.uint8)
        return bits

    def qpsk_modulate(self, bits: np.ndarray) -> np.ndarray:
        """
        Quadrature Phase Shift Keying modulation

        Args:
            bits: Input bit array (length must be even)

        Returns:
            Complex QPSK symbols
        """
        # Ensure even number of bits
        if len(bits) % 2 != 0:
            bits = np.append(bits, 0)  # Pad with zero

        # Group bits into pairs
        bit_pairs = bits.reshape(-1, 2)

        # Map bit pairs to symbols using Gray coding
        # 00 -> +1+1j, 01 -> -1+1j, 11 -> -1-1j, 10 -> +1-1j
        i_bits = 1 - 2 * bit_pairs[:, 0]  # I component
        q_bits = 1 - 2 * bit_pairs[:, 1]  # Q component

        symbols = (i_bits + 1j * q_bits) / np.sqrt(2)  # Normalize for unit energy
        return symbols

    def qpsk_demodulate(self, symbols: np.ndarray) -> np.ndarray:
        """
        QPSK demodulation using hard decision

        Args:
            symbols: Received complex symbols

        Returns:
            Demodulated bits
        """
        # Extract I and Q components
        i_component = np.real(symbols)
        q_component = np.imag(symbols)

        # Hard decision
        i_bits = (i_component < 0).astype(np.uint8)
        q_bits = (q_component < 0).astype(np.uint8)

        # Interleave I and Q bits
        bits = np.zeros(2 * len(symbols), dtype=np.uint8)
        bits[0::2] = i_bits
        bits[1::2] = q_bits

        return bits

    def qam16_modulate(self, bits: np.ndarray) -> np.ndarray:
        """
        16-QAM modulation with Gray mapping

        Args:
            bits: Input bit array (length must be multiple of 4)

        Returns:
            Complex 16-QAM symbols
        """
        # Ensure multiple of 4 bits
        remainder = len(bits) % 4
        if remainder != 0:
            bits = np.append(bits, np.zeros(4 - remainder, dtype=np.uint8))

        # Group bits into 4-bit symbols
        bit_groups = bits.reshape(-1, 4)

        symbols = np.zeros(len(bit_groups), dtype=complex)

        for i, bit_group in enumerate(bit_groups):
            # Convert 4 bits to integer
            bit_value = (bit_group[0] << 3) + (bit_group[1] << 2) + \
                        (bit_group[2] << 1) + bit_group[3]

            # Map to constellation point using Gray coding
            constellation_idx = self.qam16_gray_demap[bit_value]
            symbols[i] = self.qam16_constellation[constellation_idx]

        return symbols

    def qam16_demodulate(self, symbols: np.ndarray) -> np.ndarray:
        """
        16-QAM demodulation using minimum distance

        Args:
            symbols: Received complex symbols

        Returns:
            Demodulated bits
        """
        bits = np.zeros(4 * len(symbols), dtype=np.uint8)

        for i, symbol in enumerate(symbols):
            # Find the closest constellation point
            distances = np.abs(symbol - self.qam16_constellation)
            closest_idx = np.argmin(distances)

            # Get corresponding bit pattern using Gray mapping
            bit_value = self.qam16_gray_map[closest_idx]

            # Convert to 4 bits
            bits[4 * i] = (bit_value >> 3) & 1
            bits[4 * i + 1] = (bit_value >> 2) & 1
            bits[4 * i + 2] = (bit_value >> 1) & 1
            bits[4 * i + 3] = bit_value & 1

        return bits

    def soft_qpsk_demodulate(self, symbols: np.ndarray, noise_var: float) -> np.ndarray:
        """
        Soft QPSK demodulation (returns LLRs)

        Args:
            symbols: Received complex symbols
            noise_var: Noise variance estimate

        Returns:
            Log-likelihood ratios for each bit
        """
        # LLR = 4 * Re(y*conj(s)) / noise_var for QPSK
        # where s is the reference constellation point

        llrs = np.zeros(2 * len(symbols))

        for i, symbol in enumerate(symbols):
            # I-component LLR (bit 0)
            llrs[2 * i] = 4 * np.real(symbol) / noise_var

            # Q-component LLR (bit 1)
            llrs[2 * i + 1] = 4 * np.imag(symbol) / noise_var

        return llrs

    def constellation_plot_data(self, modulation: str) -> tuple:
        """
        Get constellation points for plotting

        Args:
            modulation: Modulation type ('bpsk', 'qpsk', '16qam')

        Returns:
            (I_points, Q_points, labels)
        """
        if modulation == 'bpsk':
            points = np.array([-1, 1])
            return np.real(points), np.zeros_like(points), ['1', '0']

        elif modulation == 'qpsk':
            points = np.array([1 + 1j, -1 + 1j, -1 - 1j, 1 - 1j]) / np.sqrt(2)
            labels = ['00', '01', '11', '10']  # Gray coding
            return np.real(points), np.imag(points), labels

        elif modulation == '16qam':
            labels = []
            for i in range(16):
                bit_val = self.qam16_gray_map[i]
                labels.append(f'{bit_val:04b}')

            return (np.real(self.qam16_constellation),
                    np.imag(self.qam16_constellation),
                    labels)

        else:
            raise ValueError(f"Unknown modulation: {modulation}")

    def calculate_theoretical_ber(self, modulation: str, snr_db: float) -> float:
        """
        Calculate theoretical BER for AWGN channel

        Args:
            modulation: Modulation type
            snr_db: SNR in dB

        Returns:
            Theoretical BER
        """
        from scipy.special import erfc

        snr_linear = 10 ** (snr_db / 10.0)

        if modulation == 'bpsk':
            # BER = Q(sqrt(2*Eb/N0)) = 0.5 * erfc(sqrt(Eb/N0))
            return 0.5 * erfc(np.sqrt(snr_linear))

        elif modulation == 'qpsk':
            # Same as BPSK for Gray coding
            return 0.5 * erfc(np.sqrt(snr_linear))

        elif modulation == '16qam':
            # Approximation for 16-QAM with Gray coding
            return 0.375 * erfc(np.sqrt(0.4 * snr_linear))

        else:
            return None

    def get_modulation_info(self, modulation: str) -> dict:
        """
        Get information about modulation scheme

        Args:
            modulation: Modulation type

        Returns:
            Dictionary with modulation information
        """
        info = {
            'bpsk': {
                'name': 'Binary Phase Shift Keying',
                'bits_per_symbol': 1,
                'constellation_size': 2,
                'peak_to_avg_power': 1.0,
                'spectral_efficiency': 1.0
            },
            'qpsk': {
                'name': 'Quadrature Phase Shift Keying',
                'bits_per_symbol': 2,
                'constellation_size': 4,
                'peak_to_avg_power': 1.0,
                'spectral_efficiency': 2.0
            },
            '16qam': {
                'name': '16-ary Quadrature Amplitude Modulation',
                'bits_per_symbol': 4,
                'constellation_size': 16,
                'peak_to_avg_power': 1.8,
                'spectral_efficiency': 4.0
            }
        }

        return info.get(modulation, {})
