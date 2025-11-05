"""
SimuRF Packet Handler
Captures IP packets, sends to MATLAB for channel simulation, and forwards
"""

import os
import sys
import time
import socket
import struct
import subprocess
import json
from scapy.all import *
from threading import Thread
import numpy as np

# MATLAB Engine API
try:
    import matlab.engine
    MATLAB_AVAILABLE = True
except ImportError:
    print("Warning: MATLAB Engine API not available. Using simulation mode.")
    MATLAB_AVAILABLE = False


class SimuRFEngine:
    def __init__(self, config_file='config.json'):
        self.config = self.load_config(config_file)
        self.matlab_engine = None
        self.stats = {
            'packets_processed': 0,
            'bytes_processed': 0,
            'dropped_packets': 0,
            'start_time': time.time()
        }
        
        # Initialize MATLAB
        if MATLAB_AVAILABLE:
            print("Starting MATLAB Engine...")
            self.matlab_engine = matlab.engine.start_matlab()
            print("MATLAB Engine started successfully")
        
    def load_config(self, config_file):
        """Load configuration from JSON file"""
        default_config = {
            'source_ip': '0.0.0.0',
            'dest_ip': '0.0.0.0',
            'interface': 'eth0',
            'channel_params': {
                'carrier_freq': 2.4e9,
                'sample_rate': 20e6,
                'snr': 15,
                'delay_spread': 50e-9,
                'doppler': 10
            },
            'enable_channel_sim': True,
            'packet_loss_rate': 0.0,  # Additional packet loss (0-1)
            'latency_ms': 0  # Additional fixed latency
        }
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def simulate_channel(self, packet_data):
        """
        Simulate wireless channel using MATLAB
        
        Args:
            packet_data: Raw packet bytes
            
        Returns:
            Processed packet bytes after channel simulation
        """
        if not self.config['enable_channel_sim']:
            return packet_data
        
        # Convert packet to uint8 array
        input_array = np.frombuffer(packet_data, dtype=np.uint8)
        
        if MATLAB_AVAILABLE and self.matlab_engine:
            try:
                # Create MATLAB-compatible parameters
                params = matlab.double([
                    self.config['channel_params']['carrier_freq'],
                    self.config['channel_params']['sample_rate'],
                    self.config['channel_params']['snr'],
                    self.config['channel_params']['delay_spread'],
                    self.config['channel_params']['doppler']
                ])
                
                # Convert numpy array to MATLAB array
                matlab_input = matlab.uint8(input_array.tolist())
                
                # Call MATLAB function
                result = self.matlab_engine.matlab_channel_sim(
                    matlab_input, 
                    nargout=1
                )
                
                # Convert back to bytes
                output_array = np.array(result, dtype=np.uint8)
                return output_array.tobytes()
                
            except Exception as e:
                print(f"MATLAB simulation error: {e}")
                return packet_data
        else:
            # Fallback: Simple noise simulation without MATLAB
            return self.simulate_simple_channel(input_array)
    
    def simulate_simple_channel(self, packet_array):
        """Simple channel simulation without MATLAB (fallback)"""
        # Add random bit errors based on SNR
        snr_db = self.config['channel_params']['snr']
        ber = 0.5 * np.exp(-snr_db/10)  # Approximate BER
        
        # Random bit flips
        for i in range(len(packet_array)):
            if np.random.random() < ber:
                bit_pos = np.random.randint(0, 8)
                packet_array[i] ^= (1 << bit_pos)
        
        return packet_array.tobytes()
    
    def packet_loss_simulation(self):
        """Determine if packet should be dropped"""
        return np.random.random() < self.config['packet_loss_rate']
    
    def process_packet(self, packet):
        """Process a single packet through the wireless channel"""
        try:
            if IP in packet:
                # Check if packet should be dropped
                if self.packet_loss_simulation():
                    self.stats['dropped_packets'] += 1
                    print(f"Packet dropped (simulated loss)")
                    return
                
                # Extract IP packet
                ip_layer = packet[IP]
                
                # Get raw packet data
                raw_packet = bytes(packet)
                
                print(f"\n--- Processing Packet ---")
                print(f"Source: {ip_layer.src} -> Destination: {ip_layer.dst}")
                print(f"Protocol: {ip_layer.proto}, Length: {len(raw_packet)} bytes")
                
                # Simulate channel
                start_time = time.time()
                processed_packet = self.simulate_channel(raw_packet)
                processing_time = (time.time() - start_time) * 1000
                
                print(f"Channel simulation time: {processing_time:.2f} ms")
                
                # Add configured latency
                if self.config['latency_ms'] > 0:
                    time.sleep(self.config['latency_ms'] / 1000.0)
                
                # Send processed packet
                send(Raw(load=processed_packet), verbose=0)
                
                # Update statistics
                self.stats['packets_processed'] += 1
                self.stats['bytes_processed'] += len(raw_packet)
                
                print(f"Packet forwarded successfully")
                
        except Exception as e:
            print(f"Error processing packet: {e}")
            import traceback
            traceback.print_exc()
    
    def start_capture(self):
        """Start packet capture and processing"""
        print("\n=== SimuRF Wireless Channel Emulator ===")
        print(f"Interface: {self.config['interface']}")
        print(f"Channel Simulation: {'Enabled' if self.config['enable_channel_sim'] else 'Disabled'}")
        print(f"SNR: {self.config['channel_params']['snr']} dB")
        print(f"Packet Loss Rate: {self.config['packet_loss_rate']*100:.1f}%")
        print(f"Additional Latency: {self.config['latency_ms']} ms")
        print("\nStarting packet capture...\n")
        
        # Build filter
        filter_str = "ip"
        if self.config['source_ip'] != '0.0.0.0':
            filter_str += f" and src {self.config['source_ip']}"
        if self.config['dest_ip'] != '0.0.0.0':
            filter_str += f" and dst {self.config['dest_ip']}"
        
        try:
            # Start sniffing
            sniff(
                iface=self.config['interface'],
                filter=filter_str,
                prn=self.process_packet,
                store=0
            )
        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self.print_statistics()
        except Exception as e:
            print(f"Capture error: {e}")
            import traceback
            traceback.print_exc()
    
    def print_statistics(self):
        """Print processing statistics"""
        runtime = time.time() - self.stats['start_time']
        print("\n=== SimuRF Statistics ===")
        print(f"Runtime: {runtime:.1f} seconds")
        print(f"Packets Processed: {self.stats['packets_processed']}")
        print(f"Bytes Processed: {self.stats['bytes_processed']}")
        print(f"Packets Dropped: {self.stats['dropped_packets']}")
        if runtime > 0:
            print(f"Throughput: {self.stats['bytes_processed']/runtime/1024:.2f} KB/s")
        
        if self.matlab_engine:
            self.matlab_engine.quit()


def main():
    """Main entry point"""
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    
    engine = SimuRFEngine(config_file)
    engine.start_capture()


if __name__ == '__main__':
    main()