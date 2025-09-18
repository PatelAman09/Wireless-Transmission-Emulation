"""
Wireless Channel Model
Applies various channel effects to transmitted signals
"""

import numpy as np
import logging

from scipy import signal

logger = logging.getLogger(__name__)


class ChannelModel:
    def __init__(self, channel_type: str = 'awgn', snr_db: float = 10.0,
                 doppler_freq: float = 100.0, delay_spread: float = 1e-6):
        """
        Initialize channel model

        Args:
            channel_type: Type of channel ('awgn', 'rayleigh', 'rician')
            snr_db: Signal-to-noise ratio in dB
            doppler_freq: Maximum Doppler frequency in Hz
            delay_spread: RMS delay spread in seconds
        """
        self.channel_type = channel_type
        self.snr_db = snr_db
        self.doppler_freq = doppler_freq
        self.delay_spread = delay_spread

        # Convert SNR to linear scale
        self.snr_linear = 10 ** (snr_db / 10.0)

        # Statistics
        self.signals_processed = 0
        self.total_noise_power = 0.0

        # Fading state for time-correlated channels
        self.fading_state = None
        self.prev_time = 0

        logger.info(f"Channel initialized: {channel_type}, SNR = {snr_db} dB")

    def apply_channel(self, tx_signal: np.ndarray, sample_rate: float = 1e6) -> np.ndarray:
        """
        Apply channel effects to transmitted signal

        Args:
            tx_signal: Input complex baseband signal
            sample_rate: Sampling rate in Hz

        Returns:
            Signal after channel effects
        """
        rx_signal = tx_signal.copy()

        # Apply fading if specified
        if self.channel_type in ['rayleigh', 'rician']:
            rx_signal = self._apply_fading(rx_signal, sample_rate)

        # Apply multipath if delay spread is specified
        if self.delay_spread > 0:
            rx_signal = self._apply_multipath(rx_signal, sample_rate)

        # Always apply AWGN noise
        rx_signal = self._add_awgn_noise(rx_signal)

        self.signals_processed += 1
        logger.debug(f"Applied {self.channel_type} channel effects")

        return rx_signal

    def _add_awgn_noise(self, signal: np.ndarray) -> np.ndarray:
        """
        Add Additive White Gaussian Noise (AWGN)

        Args:
            signal: Input signal

        Returns:
            Signal with AWGN noise
        """
        # Calculate signal power
        signal_power = np.mean(np.abs(signal) ** 2)

        # Calculate noise power based on SNR
        noise_power = signal_power / self.snr_linear

        # Generate complex AWGN
        noise_real = np.random.normal(0, np.sqrt(noise_power / 2), len(signal))
        noise_imag = np.random.normal(0, np.sqrt(noise_power / 2), len(signal))
        noise = noise_real + 1j * noise_imag

        self.total_noise_power += np.sum(np.abs(noise) ** 2)

        return signal + noise

    def _apply_fading(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        """
        Apply Rayleigh or Rician fading

        Args:
            signal: Input signal
            sample_rate: Sampling rate

        Returns:
            Signal after fading
        """
        # Time vector
        dt = 1 / sample_rate
        t = np.arange(len(signal)) * dt

        if self.channel_type == 'rayleigh':
            fading_coeff = self._generate_rayleigh_fading(t, sample_rate)
        elif self.channel_type == 'rician':
            fading_coeff = self._generate_rician_fading(t, sample_rate, k_factor=10)
        else:
            return signal  # No fading

        return signal * fading_coeff

    def _generate_rayleigh_fading(self, t: np.ndarray, sample_rate: float) -> np.ndarray:
        """
        Generate Rayleigh fading coefficients using Jake's model

        Args:
            t: Time vector
            sample_rate: Sampling rate

        Returns:
            Complex fading coefficients
        """
        # Number of sinusoids for Jake's model
        N = 16

        # Generate multiple sinusoids with different phases and frequencies
        h = np.zeros(len(t), dtype=complex)

        for n in range(N):
            # Random phase
            phi_n = np.random.uniform(0, 2 * np.pi)

            # Doppler frequency component
            f_n = self.doppler_freq * np.cos(2 * np.pi * n / N)

            # Real and imaginary components
            h += np.exp(1j * (2 * np.pi * f_n * t + phi_n))

        # Normalize
        h = h / np.sqrt(N)

        return h

    def _generate_rician_fading(self, t: np.ndarray, sample_rate: float,
                                k_factor: float) -> np.ndarray:
        """
        Generate Rician fading coefficients

        Args:
            t: Time vector
            sample_rate: Sampling rate
            k_factor: Rician K-factor (ratio of LOS to NLOS power)

        Returns:
            Complex fading coefficients
        """
        # Generate Rayleigh component
        rayleigh_component = self._generate_rayleigh_fading(t, sample_rate)

        # Add line-of-sight (LOS) component
        los_component = np.sqrt(k_factor / (k_factor + 1))
        nlos_component = np.sqrt(1 / (k_factor + 1)) * rayleigh_component

        return los_component + nlos_component

    def _apply_multipath(self, signal: np.ndarray, sample_rate: float) -> np.ndarray:
        """
        Apply multipath effects using exponential delay profile

        Args:
            signal: Input signal
            sample_rate: Sampling rate

        Returns:
            Signal after multipath propagation
        """
        # Create exponential delay profile
        max_delay_samples = int(self.delay_spread * sample_rate * 5)  # 5 times RMS
        delays = np.arange(max_delay_samples)

        # Exponential power delay profile
        rms_samples = self.delay_spread * sample_rate
        powers = np.exp(-delays / rms_samples)
        powers = powers / np.sum(powers)  # Normalize

        # Create channel impulse response
        h = np.sqrt(powers) * (np.random.randn(max_delay_samples) +
                               1j * np.random.randn(max_delay_samples)) / np.sqrt(2)

        # Apply multipath using convolution
        multipath_signal = np.convolve(signal, h, mode='same')

        return multipath_signal

    def set_snr(self, snr_db: float):
        """Update SNR value"""
        self.snr_db = snr_db
        self.snr_linear = 10 ** (snr_db / 10.0)
        logger.info(f"SNR updated to {snr_db} dB")

    def set_doppler(self, doppler_freq: float):
        """Update Doppler frequency"""
        self.doppler_freq = doppler_freq
        logger.info(f"Doppler frequency updated to {doppler_freq} Hz")

    def get_channel_response(self, num_taps: int = 64) -> np.ndarray:
        """
        Get current channel frequency response

        Args:
            num_taps: Number of frequency points

        Returns:
            Complex channel frequency response
        """
        if self.channel_type == 'awgn':
            return np.ones(num_taps, dtype=complex)
        else:
            # This is simplified - in practice would depend on current fading state
            w, h = signal.freqz(np.array([1.0]), np.array([1.0]), worN=num_taps)
            return h

    def get_stats(self) -> dict:
        """Get channel statistics"""
        avg_noise_power = (self.total_noise_power / self.signals_processed
                           if self.signals_processed > 0 else 0)

        return {
            'signals_processed': self.signals_processed,
            'channel_type': self.channel_type,
            'snr_db': self.snr_db,
            'doppler_freq': self.doppler_freq,
            'delay_spread': self.delay_spread,
            'avg_noise_power': avg_noise_power
        }

    def reset_stats(self):
        """Reset statistics counters"""
        self.signals_processed = 0
        self.total_noise_power = 0.0
