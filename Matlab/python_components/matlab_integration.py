#!/usr/bin/env python3
import matlab.engine
import numpy as np
import json
import time
import os

class MATLABRFEmulator:
    def __init__(self, config_file='/simurf/config/matlab_channel_config.json'):
        self.config_file = config_file
        self.engine = None
        self.start_matlab_engine()
        
    def start_matlab_engine(self):
        """Start MATLAB engine"""
        print("🔧 Starting MATLAB Engine...")
        try:
            self.engine = matlab.engine.start_matlab()
            # Add MATLAB components to path
            matlab_path = '/simurf/matlab_components'
            self.engine.addpath(matlab_path, nargout=0)
            print("✅ MATLAB Engine started successfully")
        except Exception as e:
            print(f"❌ Failed to start MATLAB Engine: {e}")
            raise
    
    def process_packet_with_matlab(self, ip_packet):
        """Process IP packet using MATLAB RF emulator"""
        try:
            print("🎛️  Sending to MATLAB for professional RF processing...")
            
            # Convert to MATLAB compatible format
            ml_packet = matlab.uint8(ip_packet.tolist())
            
            # Call MATLAB function
            start_time = time.time()
            result = self.engine.professional_rf_emulator(
                ml_packet, 
                self.config_file, 
                nargout=2
            )
            processing_time = time.time() - start_time
            
            complex_samples, channel_info = result
            
            # Convert MATLAB output to Python
            samples_real = np.array(complex_samples[0], dtype=np.float32)
            samples_imag = np.array(complex_samples[1], dtype=np.float32) if len(complex_samples) > 1 else np.zeros_like(samples_real)
            complex_samples_py = samples_real + 1j * samples_imag
            
            # Parse channel info
            channel_stats = {
                'snr_db': channel_info['snr_db'],
                'channel_model': channel_info['channel_model'],
                'evm_percent': channel_info['evm'] * 100,
                'ber': channel_info['ber'],
                'processing_time': processing_time
            }
            
            print(f"✅ MATLAB Processing complete:")
            print(f"   📊 SNR: {channel_stats['snr_db']} dB")
            print(f"   🌊 Channel: {channel_stats['channel_model']}")
            print(f"   📶 EVM: {channel_stats['evm_percent']:.2f}%")
            print(f"   🔗 BER: {channel_stats['ber']:.2e}")
            print(f"   ⏱️  Processing time: {processing_time:.3f}s")
            
            return complex_samples_py, channel_stats
            
        except Exception as e:
            print(f"❌ MATLAB processing error: {e}")
            raise
    
    def save_complex_samples_matlab(self, complex_samples, filename):
        """Save complex samples using MATLAB"""
        try:
            # Convert to MATLAB format
            ml_real = matlab.single(np.real(complex_samples).tolist())
            ml_imag = matlab.single(np.imag(complex_samples).tolist())
            ml_complex = [ml_real, ml_imag]
            
            # Call MATLAB save function
            self.engine.save_complex_samples(ml_complex, filename, nargout=0)
            print(f"💾 MATLAB saved samples to {filename}")
            
        except Exception as e:
            print(f"❌ MATLAB save error: {e}")
            raise
    
    def close(self):
        """Close MATLAB engine"""
        if self.engine:
            self.engine.quit()
            print("🔚 MATLAB Engine closed")