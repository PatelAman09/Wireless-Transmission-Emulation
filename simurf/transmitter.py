"""
Wireless Transmitter Module
Converts IP packets to modulated complex baseband signals
"""

import numpy as np
import logging
from simurf.utils.modulation import ModulationSchemes

logger = logging.getLogger(__name__)


class WirelessTransmitter:
    def __init__(self, modulation: str = 'qpsk', sample_rate: float = 1e6,
                 carrier_freq: float = 2.4e9, symbol_rate: float = 1e5):
        """
        Initialize wireless transmitter

        Args:
            modulation: Modulation scheme ('bpsk', 'qpsk', '16qam')
            sample_rate: Sampling rate in Hz
            carrier_freq: Carrier frequency in Hz
            symbol_rate: Symbol rate in symbols/sec
        """
        self.modulation = modulation
        self.sample_rate = sample_rate
        self.carrier_freq = carrier_freq
        self.symbol_rate = symbol_rate
        self.samples_per_symbol = int(sample_rate / symbol_rate)

        # Initialize modulation scheme
        self.mod_scheme = ModulationSchemes()

        # Statistics
        self.packets_transmitted = 0
        self.bytes_transmitted = 0

        logger.info(f"Transmitter initialized: {modulation}, {sample_rate / 1e6:.1f} Msps")

    def packet_to_bits(self, packet_data: bytes) -> np.ndarray:
        """
        Convert packet bytes to bit array

        Args:
            packet_data: Input packet as bytes

        Returns:
            Bit array as numpy array
        """
        # Convert bytes to bit array
        bit_array = np.unpackbits(np.frombuffer(packet_data, dtype=np.uint8))

        # Add simple framing (start/stop sequences for synchronization)
        start_seq = np.array([1, 0, 1, 0, 1, 1, 0, 0], dtype=np.uint8)  # Sync pattern
        stop_seq = np.array([0, 0, 1, 1, 0, 1, 0, 1], dtype=np.uint8)  # End pattern

        # Add length information (16-bit length field)
        length_bits = np.unpackbits(
            np.array([len(packet_data)], dtype='>u2').view(np.uint8)
        )

        # Construct frame: [start_seq | length | data | stop_seq]
        framed_bits = np.concatenate([start_seq, length_bits, bit_array, stop_seq])

        logger.debug(f"Converted {len(packet_data)} bytes to {len(framed_bits)} bits")
        return framed_bits

    def bits_to_symbols(self, bits: np.ndarray) -> np.ndarray:
        """
        Convert bits to modulated symbols

        Args:
            bits: Input bit array

        Returns:
            Complex symbol array
        """
        if self.modulation == 'bpsk':
            symbols = self.mod_scheme.bpsk_modulate(bits)
        elif self.modulation == 'qpsk':
            symbols = self.mod_scheme.qpsk_modulate(bits)
        elif self.modulation == '16qam':
            symbols = self.mod_scheme.qam16_modulate(bits)
        else:
            raise ValueError(f"Unsupported modulation: {self.modulation}")

        logger.debug(f"Modulated {len(bits)} bits to {len(symbols)} symbols")
        return symbols

    def pulse_shape(self, symbols: np.ndarray) -> np.ndarray:
        """
        Apply pulse shaping to symbols

        Args:
            symbols: Input symbol array

        Returns:
            Pulse-shaped complex baseband signal
        """
        # Create root raised cosine filter
        filter_span = 6  # Filter span in symbols
        beta = 0.35  # Roll-off factor

        # Time vector for filter
        t = np.arange(-filter_span / 2, filter_span / 2, 1 / self.samples_per_symbol)

        # Root raised cosine impulse response
        rrc_filter = self._root_raised_cosine(t, beta, 1 / self.symbol_rate)

        # Upsample symbols by inserting zeros
        upsampled = np.zeros(len(symbols) * self.samples_per_symbol, dtype=complex)
        upsampled[::self.samples_per_symbol] = symbols

        # Apply pulse shaping filter
        shaped_signal = np.convolve(upsampled, rrc_filter, mode='same')

        logger.debug(f"Pulse shaped to {len(shaped_signal)} samples")
        return shaped_signal

    def _root_raised_cosine(self, t: np.ndarray, beta: float, T: float) -> np.ndarray:
        """
        Generate root raised cosine filter impulse response

        Args:
            t: Time vector
            beta: Roll-off factor
            T: Symbol period

        Returns:
            Filter impulse response
        """
        # Avoid division by zero
        idx_zero = np.where(np.abs(t) < 1e-10)[0]
        idx_beta = np.where(np.abs(np.abs(t) - T / (4 * beta)) < 1e-10)[0]

        h = np.zeros_like(t)

        # Handle special cases
        if len(idx_zero) > 0:
            h[idx_zero] = (1 / T) * (1 + beta * (4 / np.pi - 1))

        if len(idx_beta) > 0:
            h[idx_beta] = (beta / (T * np.sqrt(2))) * \
                          ((1 + 2 / np.pi) * np.sin(np.pi / (4 * beta)) +
                           (1 - 2 / np.pi) * np.cos(np.pi / (4 * beta)))

        # General case
        idx_general = np.where((np.abs(t) > 1e-10) &
                               (np.abs(np.abs(t) - T / (4 * beta)) > 1e-10))[0]

        if len(idx_general) > 0:
            numerator = np.sin(np.pi * t[idx_general] / T * (1 - beta)) + \
                        4 * beta * t[idx_general] / T * \
                        np.cos(np.pi * t[idx_general] / T * (1 + beta))

            denominator = np.pi * t[idx_general] / T * \
                          (1 - (4 * beta * t[idx_general] / T) ** 2)

            h[idx_general] = (1 / T) * numerator / denominator

        return h

    def transmit(self, packet_data: bytes) -> np.ndarray:
        """
        Complete transmission chain: packet -> bits -> symbols -> baseband signal

        Args:
            packet_data: Input packet as bytes

        Returns:
            Complex baseband signal
        """
        try:
            # Step 1: Convert packet to bits
            bits = self.packet_to_bits(packet_data)

            # Step 2: Modulate bits to symbols
            symbols = self.bits_to_symbols(bits)

            # Step 3: Apply pulse shaping
            baseband_signal = self.pulse_shape(symbols)

            # Update statistics
            self.packets_transmitted += 1
            self.bytes_transmitted += len(packet_data)

            logger.debug(f"Transmitted packet: {len(packet_data)} bytes -> "
                         f"{len(baseband_signal)} samples")

            return baseband_signal

        except Exception as e:
            logger.error(f"Transmission error: {e}")
            raise

    def get_stats(self) -> dict:
        """Get transmitter statistics"""
        return {
            'packets_transmitted': self.packets_transmitted,
            'bytes_transmitted': self.bytes_transmitted,
            'modulation': self.modulation,
            'sample_rate': self.sample_rate,
            'symbol_rate': self.symbol_rate
        }

    def reset_stats(self):
        """Reset statistics counters"""
        self.packets_transmitted = 0
        self.bytes_transmitted = 0
