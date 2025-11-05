import socket
import struct
import numpy as np
import threading
import time
import os
import json
from scapy.all import sniff, send, IP, Raw
from scapy.config import conf

class NetworkManager:
    def __init__(self, config_file='/simurf/config/network_config.json'):
        self.load_config(config_file)
        self.running = False
        
    def load_config(self, config_file):
        """Load network configuration"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            self.input_interface = config.get('input_interface', 'eth0')
            self.output_interface = config.get('output_interface', 'eth1')
            self.destination_ip = config.get('destination_ip', '192.168.1.100')
            self.packet_timeout = config.get('packet_timeout', 0.1)
            
        except Exception as e:
            print(f"Error loading config, using defaults: {e}")
            self.input_interface = 'eth0'
            self.output_interface = 'eth1'
            self.destination_ip = '192.168.1.100'
            self.packet_timeout = 0.1
    
    def start_capture(self):
        """Capture IP packets from network interface"""
        self.running = True
        print(f"Starting packet capture on {self.input_interface}")
        
        def packet_handler(packet):
            try:
                if packet.haslayer(IP):
                    ip_layer = packet[IP]
                    # Convert packet to bytes
                    ip_data = bytes(ip_layer)
                    
                    # Ensure input directory exists
                    os.makedirs('/simurf/input', exist_ok=True)
                    
                    # Save to input directory for MATLAB processing
                    input_file = f'/simurf/input/ip_packet_{int(time.time()*1000)}.bin'
                    with open(input_file, 'wb') as f:
                        f.write(ip_data)
                    
                    print(f"Captured IP packet: {ip_layer.src} -> {ip_layer.dst}, Length: {len(ip_data)}")
                    
            except Exception as e:
                print(f"Error processing packet: {e}")
        
        # Start sniffing in background thread
        def sniff_thread():
            try:
                sniff(iface=self.input_interface, prn=packet_handler, stop_filter=lambda x: not self.running)
            except Exception as e:
                print(f"Sniffing error: {e}")
        
        sniff_thread = threading.Thread(target=sniff_thread)
        sniff_thread.daemon = True
        sniff_thread.start()
        return sniff_thread
    
    def transmit_packet(self, payload, destination_ip=None):
        """Transmit IP packet to destination"""
        try:
            if destination_ip is None:
                destination_ip = self.destination_ip
                
            # Create IP packet
            ip_packet = IP(dst=destination_ip)/Raw(load=payload)
            
            # Send packet
            send(ip_packet, iface=self.output_interface, verbose=0)
            print(f"Transmitted packet to {destination_ip}, Length: {len(payload)}")
            
        except Exception as e:
            print(f"Error transmitting packet: {e}")
    
    def simple_demodulate(self, complex_samples):
        """Simple demodulation (reverse of QPSK)"""
        try:
            # QPSK constellation points
            constellation = np.array([1+1j, -1+1j, -1-1j, 1-1j]) / np.sqrt(2)
            
            # Find closest constellation point for each sample
            symbols = []
            for sample in complex_samples:
                distances = np.abs(constellation - sample)
                symbol_idx = np.argmin(distances)
                symbols.append(symbol_idx)
            
            # Convert symbols back to bits
            bits = []
            for symbol in symbols:
                if symbol == 0:    # 00
                    bits.extend([0, 0])
                elif symbol == 1:  # 01
                    bits.extend([0, 1])
                elif symbol == 2:  # 11
                    bits.extend([1, 1])
                elif symbol == 3:  # 10
                    bits.extend([1, 0])
            
            return np.array(bits, dtype=np.uint8)
            
        except Exception as e:
            print(f"Demodulation error: {e}")
            return np.array([], dtype=np.uint8)
    
    def bits_to_bytes(self, bits):
        """Convert bit array to bytes"""
        try:
            # Ensure multiple of 8
            if len(bits) % 8 != 0:
                bits = bits[:len(bits)//8*8]
            
            # Reshape and convert to bytes
            bytes_array = np.packbits(bits.reshape(-1, 8))
            return bytes_array.tobytes()
            
        except Exception as e:
            print(f"Error converting bits to bytes: {e}")
            return b''
    
    def process_complex_samples(self):
        """Process complex samples from MATLAB and convert back to IP packets"""
        samples_dir = '/simurf/output'
        
        while self.running:
            try:
                # Check for sample files
                if os.path.exists(samples_dir):
                    sample_files = [f for f in os.listdir(samples_dir) if f.endswith('.bin')]
                    
                    for sample_file in sample_files:
                        sample_path = os.path.join(samples_dir, sample_file)
                        try:
                            # Read complex samples
                            with open(sample_path, 'rb') as f:
                                data = np.fromfile(f, dtype=np.float32)
                            
                            if len(data) % 2 != 0:
                                print(f"Warning: Odd number of floats in {sample_file}")
                                continue
                                
                            # Convert to complex samples
                            real_part = data[0::2]
                            imag_part = data[1::2]
                            complex_samples = real_part + 1j * imag_part
                            
                            # Demodulate
                            demodulated_bits = self.simple_demodulate(complex_samples)
                            
                            # Convert to bytes
                            reconstructed_data = self.bits_to_bytes(demodulated_bits)
                            
                            if reconstructed_data:
                                # Transmit reconstructed packet
                                self.transmit_packet(reconstructed_data)
                            
                            # Clean up processed file
                            os.remove(sample_path)
                            print(f"Processed and transmitted {sample_file}")
                            
                        except Exception as e:
                            print(f"Error processing {sample_file}: {e}")
                
                time.sleep(self.packet_timeout)
                
            except Exception as e:
                print(f"Error in sample processing loop: {e}")
                time.sleep(1)
    
    def start(self):
        """Start the network manager"""
        print("Starting Network Manager...")
        
        # Create necessary directories
        os.makedirs('/simurf/input', exist_ok=True)
        os.makedirs('/simurf/output', exist_ok=True)
        os.makedirs('/simurf/logs', exist_ok=True)
        
        # Start packet capture
        capture_thread = self.start_capture()
        
        # Start sample processing thread
        processing_thread = threading.Thread(target=self.process_complex_samples)
        processing_thread.daemon = True
        processing_thread.start()
        
        print("Network Manager started successfully")
        print(f"Input interface: {self.input_interface}")
        print(f"Output interface: {self.output_interface}")
        print(f"Destination IP: {self.destination_ip}")
        
        return capture_thread, processing_thread
    
    def stop(self):
        """Stop the network manager"""
        self.running = False
        print("Network Manager stopped")

if __name__ == "__main__":
    manager = NetworkManager()
    try:
        capture_thread, processing_thread = manager.start()
        
        # Keep main thread alive
        while manager.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        manager.stop()