import os
import json
import socket
import random
import time
from simurf_matlab_bridge import SimuRFMatlab
from config_loader import load_config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAT_CFG = os.path.join(BASE_DIR, "config", "matlab_channel_config.json")

class PacketManipulator:
    def __init__(self, config):
        self.packet_loss_prob = config.get('packet_loss_probability', 0.0)
        self.packet_delay_ms = config.get('packet_delay_ms', 0)
        self.packet_jitter_ms = config.get('packet_jitter_ms', 0)
        self.delayed_packets = []
    
    def should_drop_packet(self):
        return random.random() < self.packet_loss_prob
    
    def calculate_delay(self):
        base_delay = self.packet_delay_ms / 1000.0
        jitter = (random.random() - 0.5) * 2 * (self.packet_jitter_ms / 1000.0)
        return max(0, base_delay + jitter)
    
    def process_delayed_packets(self, current_time):
        packets_to_send = []
        remaining_packets = []
        
        for send_time, packet, addr in self.delayed_packets:
            if current_time >= send_time:
                packets_to_send.append((packet, addr))
            else:
                remaining_packets.append((send_time, packet, addr))
        
        self.delayed_packets = remaining_packets
        return packets_to_send


def save_iq_samples(iq_samples, packet_num, output_dir='output'):
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, f'iq_samples_pkt_{packet_num:06d}.bin')
    
    import numpy as np
    interleaved = np.zeros(2 * len(iq_samples), dtype=np.float32)
    interleaved[0::2] = iq_samples.real
    interleaved[1::2] = iq_samples.imag
    interleaved.tofile(filename)


def main():
    # Configuration
    impairments_cfg = {
        'packet_loss_probability': 0.01,
        'packet_delay_ms': 10,
        'packet_jitter_ms': 5,
    }
    
    # Initialize components
    simurf = SimuRFMatlab(MAT_CFG)
    manipulator = PacketManipulator(impairments_cfg)
    
    # Create UDP sockets
    # Listen for packets from sender
    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(('127.0.0.1', 5000))
    
    # Send to receiver
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Logging
    os.makedirs('logs', exist_ok=True)
    log_file = open('logs/simulator.log', 'w')
    metrics_file = open('logs/simulator_metrics.log', 'w')
    
    print("[SimuRF] RF Emulation Started (Localhost Mode)")
    print("[SimuRF] Listening on 127.0.0.1:5000")
    print("[SimuRF] Forwarding to receiver...")

    pkt_count = 0
    dropped_count = 0

    while True:
        try:
            # Process delayed packets
            current_time = time.time()
            ready_packets = manipulator.process_delayed_packets(current_time)
            for packet, addr in ready_packets:
                send_sock.sendto(packet, addr)
            
            # Receive new packet (non-blocking with timeout)
            recv_sock.settimeout(0.1)
            try:
                data, addr = recv_sock.recvfrom(65535)
            except socket.timeout:
                continue
            
            pkt_count += 1

            # Simulate packet loss
            if manipulator.should_drop_packet():
                dropped_count += 1
                print(f"[PKT {pkt_count}] DROPPED (simulated loss)")
                
                log_entry = {
                    'timestamp': time.time(),
                    'packet_num': pkt_count,
                    'action': 'dropped',
                    'size': len(data)
                }
                log_file.write(json.dumps(log_entry) + '\n')
                log_file.flush()
                continue

            # MATLAB RF simulation
            try:
                # Convert bytes to list for MATLAB
                payload_list = list(data)
                iq_samples, channel_info = simurf.simulate(bytes(payload_list))
                
                ber = channel_info["ber"]
                evm = channel_info["evm"]
                snr = channel_info["snr_db"]
                channel = channel_info["channel_model"]
                
                # Save IQ samples periodically
                if pkt_count % 100 == 0:
                    save_iq_samples(iq_samples, pkt_count)
                
                # LIVE SIMULATION FEEDBACK
                print(
                    f"[PKT {pkt_count}] "
                    f"Channel={channel} | "
                    f"SNR={snr} dB | "
                    f"BER={ber:.2e} | "
                    f"EVM={evm:.3f} | "
                    f"IQ={len(iq_samples)}"
                )
                
                # Log metrics
                metrics_entry = {
                    'timestamp': time.time(),
                    'packet_num': pkt_count,
                    'channel': channel,
                    'snr_db': snr,
                    'ber': float(ber),
                    'evm': float(evm),
                    'iq_samples': len(iq_samples),
                    'packet_size': len(data)
                }
                metrics_file.write(json.dumps(metrics_entry) + '\n')
                
            except Exception as e:
                print(f"[ERROR] MATLAB simulation failed: {e}")
                continue

            # Calculate delay and forward
            delay = manipulator.calculate_delay()
            send_time = current_time + delay
            
            # Forward to receiver (localhost)
            receiver_addr = ('127.0.0.1', 5000)
            
            if delay > 0:
                manipulator.delayed_packets.append((send_time, data, receiver_addr))
            else:
                send_sock.sendto(data, receiver_addr)
            
            # Periodic summary
            if pkt_count % 500 == 0:
                print(f"\n[SUMMARY] Packets: {pkt_count} | Dropped: {dropped_count}\n")
            
            metrics_file.flush()
            log_file.flush()
            
        except KeyboardInterrupt:
            print("\n[SimuRF] Stopped by user")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            continue
    
    # Cleanup
    recv_sock.close()
    send_sock.close()
    log_file.close()
    metrics_file.close()
    simurf.close()


if __name__ == "__main__":
    main()