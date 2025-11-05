#!/usr/bin/env python3
import numpy as np
import json
import os
import time

class RFEmulator:
    def __init__(self, config_file='/simurf/config/channel_config.json'):
        self.load_config(config_file)
        
    def load_config(self, config_file):
        """Load channel configuration"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            self.snr_db = config.get('snr_db', 20)
            self.multipath_enabled = config.get('multipath_enabled', True)
            self.freq_offset = config.get('freq_offset', 0.01)
            self.delay_taps = config.get('delay_taps', [1.0, 0.5, 0.2])
            
        except Exception as e:
            print(f"Error loading config, using defaults: {e}")
            self.snr_db = 20
            self.multipath_enabled = True
            self.freq_offset = 0.01
            self.delay_taps = [1.0, 0.5, 0.2]
    
    def ip_to_binary(self, ip_packet):
        """Convert IP packet to binary stream"""
        binary_data = []
        for byte in ip_packet:
            binary_data.extend([int(bit) for bit in format(byte, '08b')])
        return np.array(binary_data, dtype=np.uint8)
    
    def qpsk_modulation(self, binary_data):
        """QPSK Modulation"""
        # Ensure even number of bits
        if len(binary_data) % 2 != 0:
            binary_data = np.append(binary_data, 0)
        
        # Reshape into symbol pairs
        symbols = binary_data.reshape(-1, 2)
        
        # Map to QPSK constellation
        constellation = np.array([1+1j, -1+1j, -1-1j, 1-1j]) / np.sqrt(2)
        
        modulated = np.zeros(len(symbols), dtype=complex)
        for i, bits in enumerate(symbols):
            if bits[0] == 0 and bits[1] == 0:
                modulated[i] = constellation[0]
            elif bits[0] == 0 and bits[1] == 1:
                modulated[i] = constellation[1]
            elif bits[0] == 1 and bits[1] == 1:
                modulated[i] = constellation[2]
            elif bits[0] == 1 and bits[1] == 0:
                modulated[i] = constellation[3]
        
        return modulated
    
    def apply_channel_effects(self, signal):
        """Apply wireless channel effects"""
        # Add AWGN
        snr_linear = 10**(self.snr_db / 10)
        signal_power = np.mean(np.abs(signal)**2)
        noise_power = signal_power / snr_linear
        noise = np.sqrt(noise_power/2) * (np.random.randn(len(signal)) + 1j*np.random.randn(len(signal)))
        
        # Apply multipath
        if self.multipath_enabled:
            channel_taps = np.array(self.delay_taps)
            channel_taps = channel_taps / np.sqrt(np.sum(channel_taps**2))  # Normalize
            signal = np.convolve(signal, channel_taps, mode='same')
        
        # Apply frequency offset
        if self.freq_offset != 0:
            t = np.arange(len(signal))
            freq_shift = np.exp(1j * 2 * np.pi * self.freq_offset * t)
            signal = signal * freq_shift
        
        return signal + noise
    
    def generate_complex_samples(self, signal):
        """Generate complex samples for output"""
        return signal
    
    def save_complex_samples(self, samples, filename):
        """Save complex samples to binary file"""
        # Interleave real and imaginary parts
        interleaved = np.zeros(2 * len(samples), dtype=np.float32)
        interleaved[0::2] = np.real(samples)
        interleaved[1::2] = np.imag(samples)
        
        with open(filename, 'wb') as f:
            interleaved.tofile(f)
    
    def process_packet(self, ip_packet):
        """Process IP packet through RF chain"""
        print(f"Processing IP packet, length: {len(ip_packet)} bytes")
        
        # Convert to binary
        binary_data = self.ip_to_binary(ip_packet)
        print(f"Binary data length: {len(binary_data)} bits")
        
        # Modulate
        modulated_signal = self.qpsk_modulation(binary_data)
        print(f"Modulated symbols: {len(modulated_signal)}")
        
        # Apply channel effects
        channel_output = self.apply_channel_effects(modulated_signal)
        
        # Generate complex samples
        complex_samples = self.generate_complex_samples(channel_output)
        
        return complex_samples

def run_emulator():
    """Main RF emulator loop"""
    emulator = RFEmulator()
    
    print("Starting Python RF Emulator...")
    print(f"SNR: {emulator.snr_db} dB, Multipath: {emulator.multipath_enabled}")
    
    while True:
        try:
            # Check for new IP packets
            input_dir = '/simurf/input'
            if os.path.exists(input_dir):
                files = [f for f in os.listdir(input_dir) if f.startswith('ip_packet_')]
                
                for filename in files:
                    filepath = os.path.join(input_dir, filename)
                    
                    # Read IP packet
                    with open(filepath, 'rb') as f:
                        ip_packet = f.read()
                    
                    # Process through RF emulator
                    complex_samples = emulator.process_packet(ip_packet)
                    
                    # Save complex samples
                    output_filename = f"/simurf/output/samples_{int(time.time()*1000)}.bin"
                    emulator.save_complex_samples(complex_samples, output_filename)
                    
                    # Clean up input file
                    os.remove(filepath)
                    
                    print(f"Processed {filename} -> {output_filename}")
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error in RF emulator: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_emulator()