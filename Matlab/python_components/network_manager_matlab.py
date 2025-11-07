#!/usr/bin/env python3
import numpy as np
import threading
import time
import os
import json
import random
from scapy.all import sniff, send, IP, Raw, TCP, UDP, ICMP
from scapy.arch import get_if_list
from matlab_integration import MATLABRFEmulator

print("=" * 70)
print("🚀 SimuRF with MATLAB Professional Wireless Emulator")
print("=" * 70)

class ProfessionalSimulationRFEmulator:
    def __init__(self, config_file='/simurf/config/matlab_channel_config.json'):
        self.matlab_emulator = MATLABRFEmulator(config_file)
        self.packets_processed = 0
        self.bytes_processed = 0
        self.simulation_start = time.time()
        
        print(f"🔧 MATLAB Professional RF Emulator Initialized")
        print(f"   🎛️  Using advanced signal processing")
        print(f"   📊 Professional channel models available")
        
    def process_packet_professional(self, ip_packet):
        """Process packet using MATLAB professional RF chain"""
        print(f"🔬 MATLAB RF Analysis starting...")
        
        # Use MATLAB for professional processing
        complex_samples, channel_info = self.matlab_emulator.process_packet_with_matlab(ip_packet)
        
        return complex_samples, channel_info

    def get_protocol_info(self, packet):
        """Extract protocol information"""
        if packet.haslayer(TCP):
            return "TCP", f"{packet[TCP].sport}→{packet[TCP].dport}"
        elif packet.haslayer(UDP):
            return "UDP", f"{packet[UDP].sport}→{packet[UDP].dport}"
        elif packet.haslayer(ICMP):
            return "ICMP", "echo"
        else:
            return "OTHER", ""

    def packet_handler(self, packet):
        """Handle captured packets with MATLAB professional simulation"""
        try:
            if packet.haslayer(IP):
                self.packets_processed += 1
                ip_layer = packet[IP]
                
                protocol, port_info = self.get_protocol_info(packet)
                packet_size = len(packet)
                self.bytes_processed += packet_size
                
                print(f"\n📨 [{self.packets_processed}] CAPTURED:")
                print(f"    📍 {ip_layer.src} → {ip_layer.dst}")
                print(f"    🔗 {protocol} {port_info}")
                print(f"    📦 Size: {packet_size} bytes")
                
                # Convert packet to bytes for processing
                ip_data = bytes(ip_layer)
                
                # Apply MATLAB professional wireless simulation
                complex_samples, channel_info = self.process_packet_professional(ip_data)
                
                # Save complex samples
                output_filename = f"/simurf/output/matlab_samples_{int(time.time()*1000)}.bin"
                self.matlab_emulator.save_complex_samples_matlab(complex_samples, output_filename)
                
                # Retransmit (simplified - in real implementation, you'd demodulate)
                self.retransmit_packet(ip_layer, ip_data)
                
                # Calculate simulation statistics
                elapsed = time.time() - self.simulation_start
                throughput = self.bytes_processed / elapsed if elapsed > 0 else 0
                
                print(f"    📤 RETRANSMITTED with MATLAB professional effects")
                print(f"    📊 Stats: {self.packets_processed} packets, {throughput:.1f} B/s")
                print("    " + "─" * 40)
                
        except Exception as e:
            print(f"    ❌ MATLAB simulation error: {e}")

    def retransmit_packet(self, ip_layer, ip_data):
        """Retransmit the processed packet"""
        try:
            # Create new packet (simplified retransmission)
            if hasattr(ip_layer, 'payload'):
                new_packet = IP(src=ip_layer.src, dst=ip_layer.dst)/ip_layer.payload
            else:
                new_packet = IP(src=ip_layer.src, dst=ip_layer.dst)/Raw(load=ip_data)
            
            send(new_packet, verbose=0)
            
        except Exception as e:
            print(f"    ❌ Retransmission error: {e}")

class NetworkManager:
    def __init__(self):
        self.simulator = ProfessionalSimulationRFEmulator()
        self.running = False
        self.interface = self.detect_interface()
        
    def detect_interface(self):
        """Detect available network interfaces"""
        print("🔍 Detecting network interfaces...")
        try:
            interfaces = get_if_list()
            print(f"✅ Found {len(interfaces)} interfaces:")
            for iface in interfaces:
                print(f"   - {iface}")
            
            # Prefer eth0, eth1, or use the first available
            for preferred in ['eth0', 'eth1', 'ens33', 'enp0s3']:
                if preferred in interfaces:
                    print(f"🎯 Using interface: {preferred}")
                    return preferred
            
            if interfaces:
                print(f"🎯 Using first available interface: {interfaces[0]}")
                return interfaces[0]
            else:
                print("❌ No network interfaces found!")
                return None
                
        except Exception as e:
            print(f"❌ Interface detection failed: {e}")
            return None

    def start_simulation(self):
        """Start the professional MATLAB simulation"""
        if not self.interface:
            print("❌ Cannot start simulation: No network interface available")
            return
            
        self.running = True
        print(f"\n🎯 Starting MATLAB Professional Wireless Simulation on {self.interface}...")
        print("💡 Features enabled:")
        print("   • 🎛️  Advanced modulation (QPSK, 16-QAM)")
        print("   • 🌊 Professional channel models (Rayleigh, Rician)")
        print("   • 📊 Real-time performance metrics (EVM, BER)")
        print("   • 🔬 MATLAB signal processing engine")
        print("\n📡 Listening for network traffic...")
        print("⏹️  Press Ctrl+C to stop simulation\n")
        
        def capture_packets():
            try:
                print(f"🔍 Starting packet capture on {self.interface}...")
                sniff(iface=self.interface, prn=self.simulator.packet_handler, store=0)
            except Exception as e:
                print(f"❌ Capture error: {e}")

        # Start packet capture
        capture_thread = threading.Thread(target=capture_packets)
        capture_thread.daemon = True
        capture_thread.start()
        
        # Keep main thread alive
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Simulation interrupted by user")
        
    def stop_simulation(self):
        """Stop the simulation"""
        self.running = False
        self.simulator.matlab_emulator.close()
        total_time = time.time() - self.simulator.simulation_start
        print(f"\n📈 MATLAB SIMULATION SUMMARY:")
        print(f"   📦 Total packets processed: {self.simulator.packets_processed}")
        print(f"   💾 Total bytes processed: {self.simulator.bytes_processed}")
        print(f"   ⏱️  Simulation duration: {total_time:.1f}s")
        if total_time > 0:
            print(f"   📊 Average throughput: {self.simulator.bytes_processed/total_time:.1f} B/s")
        print("🎉 Professional MATLAB simulation completed!")

if __name__ == "__main__":
    manager = NetworkManager()
    try:
        manager.start_simulation()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
    finally:
        manager.stop_simulation()