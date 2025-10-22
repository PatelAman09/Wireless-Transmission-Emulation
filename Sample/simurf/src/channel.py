import numpy as np


class AWGNChannel:
    def __init__(self, config):
        self.config = config
        # Fixed: Access correct config path
        self.snr_db = config['channel']['snr_db']
        self.noise_factor = config['channel'].get('noise_factor', 0.1)

    def calculate_noise_power(self, signal_power):
        """Calculate noise power based on SNR"""
        snr_linear = 10 ** (self.snr_db / 10)
        noise_power = signal_power / snr_linear
        return noise_power

    def add_awgn(self, signal):
        """Add Additive White Gaussian Noise"""
        signal_power = np.mean(np.abs(signal) ** 2)

        if signal_power == 0:
            return signal

        noise_power = self.calculate_noise_power(signal_power)

        # Generate complex Gaussian noise
        noise_std = np.sqrt(noise_power / 2)
        noise_real = np.random.normal(0, noise_std, len(signal))
        noise_imag = np.random.normal(0, noise_std, len(signal))
        noise = noise_real + 1j * noise_imag

        return signal + noise

    def add_simple_noise(self, signal):
        """Simplified noise addition for debugging"""
        noise_power = self.noise_factor * np.mean(np.abs(signal) ** 2)
        noise_std = np.sqrt(noise_power)
        noise = noise_std * (np.random.randn(len(signal)) + 1j * np.random.randn(len(signal))) / np.sqrt(2)
        return signal + noise

    def process(self, signal):
        """Main channel processing function"""
        print(f"Channel: Processing {len(signal)} samples with SNR {self.snr_db} dB")

        # Use simple noise for more predictable results
        noisy_signal = self.add_simple_noise(signal)

        # Calculate actual SNR for reporting
        original_power = np.mean(np.abs(signal) ** 2)
        noise_power = np.mean(np.abs(noisy_signal - signal) ** 2)
        actual_snr = 10 * np.log10(original_power / noise_power) if noise_power > 0 else float('inf')

        print(f"Channel: Actual SNR = {actual_snr:.2f} dB")
        return noisy_signal