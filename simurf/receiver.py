"""
Wireless Receiver Module
Recovers IP packets from received complex baseband signals
"""

import numpy as np
import logging
from typing import Optional
from simurf.utils.modulation import ModulationSchemes

logger = logging.getLogger(__name__)


class WirelessReceiver:
    def __init__(self, modulation: str = 'qpsk', sample_rate: float = 1e6,
                 symbol_rate: float = 1e5, sync_threshold: float = 0.7):
        """
        Initialize wireless receiver

        Args:
            modulation: Modulation scheme ('bpsk', 'qpsk', '16qam')
            sample_rate: Sampling rate in Hz
            symbol_rate: Symbol rate in symbols/sec
            sync_threshold: Synchronization threshold for frame detection
        """
        self.modulation = modulation
        self.sample_rate = sample_rate
        self.symbol_rate = symbol_rate
        self.samples_per_symbol = int(sample_rate / symbol_rate)
        self.sync_threshold = sync_threshold

        # Initialize demodulation scheme
        self.demod_scheme = ModulationSchemes()

        # Synchronization patterns (must match transmitter)
        self.start_seq = np.array([1, 0, 1, 0, 1, 1, 0, 0], dtype=np.uint8)
        self.stop_seq = np.array([0, 0, 1, 1, 0, 1, 0, 1], dtype=np.uint8)

        # Statistics
        self.packets_received = 0
        self.packets_decoded = 0
        self.bytes_received = 0
        self.bit_errors = 0

        logger.info(f"Receiver initialized: {modulation}, {sample_rate / 1e6:.1f} Msps")

    def receive(self, rx_signal: np.ndarray) -> Optional[bytes]:
        """
        Complete reception chain: baseband signal -> symbols -> bits -> packet

        Args:
            rx_signal: Received complex baseband signal

        Returns:
            Recovered packet bytes or None if reception failed
        """
        try:
            # Step 1: Match filtering and timing recovery
            symbols = self.signal_to_symbols(rx_signal)

            if symbols is None:
                return None

            # Step 2: Demodulate symbols to bits
            bits = self.symbols_to_bits(symbols)

            if bits is None:
                return None

            # Step 3: Frame synchronization and packet extraction
            packet_data = self.bits_to_packet(bits)

            if packet_data is not None:
                self.packets_received += 1
                self.packets_decoded += 1
                self.bytes_received += len(packet_data)
                logger.debug(f"Successfully received packet: {len(packet_data)} bytes")

            return packet_data

        except Exception as e:
            logger.error(f"Reception error: {e}")
            return None

    def signal_to_symbols(self, rx_signal: np.ndarray) -> Optional[np.ndarray]:
        """
        Convert received signal to symbol estimates

        Args:
            rx_signal: Input complex baseband signal

        Returns:
            Symbol estimates or None if processing failed
        """
        try:
            # Step 1: Matched filtering (same as pulse shaping filter)
            matched_filter = self._get_matched_filter()
            filtered_signal = np.convolve(rx_signal, matched_filter, mode='same')

            # Step 2: Symbol timing recovery (simple maximum energy method)
            timing_offset = self._symbol_timing_recovery(filtered_signal)

            # Step 3: Downsample to symbol rate
            symbol_start = timing_offset
            symbol_indices = np.arange(symbol_start, len(filtered_signal),
                                       self.samples_per_symbol, dtype=int)

            # Ensure we don't go out of bounds
            symbol_indices = symbol_indices[symbol_indices < len(filtered_signal)]

            if len(symbol_indices) == 0:
                logger.warning("No symbols recovered from signal")
                return None

            symbols = filtered_signal[symbol_indices]

            logger.debug(f"Recovered {len(symbols)} symbols from {len(rx_signal)} samples")
            return symbols

        except Exception as e:
            logger.error(f"Symbol recovery error: {e}")
            return None

    def _get_matched_filter(self) -> np.ndarray:
        """
        Generate matched filter (same as transmit pulse shaping filter)

        Returns:
            Matched filter impulse response
        """
        filter_span = 6
        beta = 0.35
        t = np.arange(-filter_span / 2, filter_span / 2, 1 / self.samples_per_symbol)
        return self._root_raised_cosine(t, beta, 1 / self.symbol_rate)

    def _root_raised_cosine(self, t: np.ndarray, beta: float, T: float) -> np.ndarray:
        """Generate root raised cosine filter (same as in transmitter)"""
        idx_zero = np.where(np.abs(t) < 1e-10)[0]
        idx_beta = np.where(np.abs(np.abs(t) - T / (4 * beta)) < 1e-10)[0]

        h = np.zeros_like(t)

        if len(idx_zero) > 0:
            h[idx_zero] = (1 / T) * (1 + beta * (4 / np.pi - 1))

        if len(idx_beta) > 0:
            h[idx_beta] = (beta / (T * np.sqrt(2))) * \
                          ((1 + 2 / np.pi) * np.sin(np.pi / (4 * beta)) +
                           (1 - 2 / np.pi) * np.cos(np.pi / (4 * beta)))

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

    def _symbol_timing_recovery(self, signal: np.ndarray) -> int:
        """
        Simple symbol timing recovery using maximum energy method

        Args:
            signal: Filtered received signal

        Returns:
            Optimal timing offset in samples
        """
        # Calculate energy for each possible timing offset
        energy = np.zeros(self.samples_per_symbol)

        for offset in range(self.samples_per_symbol):
            indices = np.arange(offset, len(signal), self.samples_per_symbol)
            if len(indices) > 0:
                energy[offset] = np.sum(np.abs(signal[indices]) ** 2)

        # Find offset with maximum energy
        optimal_offset = np.argmax(energy)

        logger.debug(f"Symbol timing offset: {optimal_offset} samples")
        return optimal_offset

    def symbols_to_bits(self, symbols: np.ndarray) -> Optional[np.ndarray]:
        """
        Demodulate symbols to recover bit stream

        Args:
            symbols: Received symbol estimates

        Returns:
            Demodulated bits or None if demodulation failed
        """
        try:
            if self.modulation == 'bpsk':
                bits = self.demod_scheme.bpsk_demodulate(symbols)
            elif self.modulation == 'qpsk':
                bits = self.demod_scheme.qpsk_demodulate(symbols)
            elif self.modulation == '16qam':
                bits = self.demod_scheme.qam16_demodulate(symbols)
            else:
                raise ValueError(f"Unsupported modulation: {self.modulation}")

            logger.debug(f"Demodulated {len(symbols)} symbols to {len(bits)} bits")
            return bits

        except Exception as e:
            logger.error(f"Demodulation error: {e}")
            return None

    def bits_to_packet(self, bits: np.ndarray) -> Optional[bytes]:
        """
        Extract packet from bit stream using frame synchronization

        Args:
            bits: Demodulated bit stream

        Returns:
            Recovered packet bytes or None if frame not found
        """
        try:
            # Find start sequence
            start_pos = self._find_sync_pattern(bits, self.start_seq)
            if start_pos == -1:
                logger.warning("Start sequence not found")
                return None

            # Extract length field (16 bits after start sequence)
            length_start = start_pos + len(self.start_seq)
            if length_start + 16 > len(bits):
                logger.warning("Not enough bits for length field")
                return None

            length_bits = bits[length_start:length_start + 16]
            length_bytes = np.packbits(length_bits).view('>u2')[0]

            # Extract data bits
            data_start = length_start + 16
            data_end = data_start + length_bytes * 8

            if data_end > len(bits):
                logger.warning(f"Not enough bits for data: need {data_end}, have {len(bits)}")
                return None

            data_bits = bits[data_start:data_end]

            # Verify stop sequence
            stop_start = data_end
            stop_end = stop_start + len(self.stop_seq)

            if stop_end > len(bits):
                logger.warning("Not enough bits for stop sequence")
                return None

            stop_bits = bits[stop_start:stop_end]

            if not np.array_equal(stop_bits, self.stop_seq):
                logger.warning("Stop sequence mismatch")
                return None

            # Convert data bits to bytes
            # Pad to multiple of 8 bits if necessary
            if len(data_bits) % 8 != 0:
                padding = 8 - (len(data_bits) % 8)
                data_bits = np.concatenate([data_bits, np.zeros(padding, dtype=np.uint8)])

            packet_bytes = np.packbits(data_bits).tobytes()[:length_bytes]

            logger.debug(f"Extracted packet: {len(packet_bytes)} bytes")
            return packet_bytes

        except Exception as e:
            logger.error(f"Packet extraction error: {e}")
            return None

    def _find_sync_pattern(self, bits: np.ndarray, pattern: np.ndarray) -> int:
        """
        Find synchronization pattern in bit stream using correlation

        Args:
            bits: Input bit stream
            pattern: Sync pattern to find

        Returns:
            Position of pattern start or -1 if not found
        """
        if len(bits) < len(pattern):
            return -1

        # Convert to bipolar for correlation
        bits_bipolar = 2 * bits.astype(float) - 1
        pattern_bipolar = 2 * pattern.astype(float) - 1

        # Cross-correlation
        correlation = np.correlate(bits_bipolar, pattern_bipolar, mode='valid')

        # Find peak correlation
        max_corr_idx = np.argmax(np.abs(correlation))
        max_corr_value = np.abs(correlation[max_corr_idx]) / len(pattern)

        if max_corr_value > self.sync_threshold:
            logger.debug(f"Sync pattern found at position {max_corr_idx}, "
                         f"correlation = {max_corr_value:.3f}")
            return max_corr_idx
        else:
            logger.debug(f"Sync pattern not found, max correlation = {max_corr_value:.3f}")
            return -1

    def estimate_ber(self, known_bits: np.ndarray, received_bits: np.ndarray) -> float:
        """
        Estimate bit error rate by comparing with known sequence

        Args:
            known_bits: Known transmitted bits
            received_bits: Received bit estimates

        Returns:
            Bit error rate
        """
        if len(known_bits) != len(received_bits):
            logger.warning("Bit sequences have different lengths")
            min_len = min(len(known_bits), len(received_bits))
            known_bits = known_bits[:min_len]
            received_bits = received_bits[:min_len]

        bit_errors = np.sum(known_bits != received_bits)
        ber = bit_errors / len(known_bits) if len(known_bits) > 0 else 1.0

        self.bit_errors += bit_errors

        logger.debug(f"BER estimate: {ber:.6f} ({bit_errors}/{len(known_bits)} errors)")
        return ber

    def get_stats(self) -> dict:
        """Get receiver statistics"""
        packet_error_rate = (1 - self.packets_decoded / self.packets_received
                             if self.packets_received > 0 else 0)

        total_bits = self.bytes_received * 8
        bit_error_rate = self.bit_errors / total_bits if total_bits > 0 else 0

        return {
            'packets_received': self.packets_received,
            'packets_decoded': self.packets_decoded,
            'bytes_received': self.bytes_received,
            'packet_error_rate': packet_error_rate,
            'bit_error_rate': bit_error_rate,
            'bit_errors': self.bit_errors,
            'modulation': self.modulation
        }

    def reset_stats(self):
        """Reset statistics counters"""
        self.packets_received = 0
        self.packets_decoded = 0
        self.bytes_received = 0
        self.bit_errors = 0
