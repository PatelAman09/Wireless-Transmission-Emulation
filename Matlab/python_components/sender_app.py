import socket
import time
import struct
import os
import json
import random
from datetime import datetime

class WirelessSender:
    def __init__(self):
        self.dest_ip = os.getenv('DESTINATION_IP', '172.20.0.50')
        self.dest_port = int(os.getenv('DESTINATION_PORT', 5000))
        self.packet_rate = int(os.getenv('PACKET_RATE', 10))
        self.payload_size = int(os.getenv('PAYLOAD_SIZE', 1024))
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sequence_number = 0
        
        self.log_file = open('/logs/sender.log', 'w')
        print(f"[SENDER] Initialized - Target: {self.dest_ip}:{self.dest_port}")
        
    def generate_payload(self, seq_num, payload_type='data'):
        """
        Generate various payload types for testing
        """
        timestamp = time.time()
        
        if payload_type == 'data':
            # Structured data payload
            header = struct.pack('!IQI', seq_num, int(timestamp * 1e6), self.payload_size)
            data = os.urandom(self.payload_size - len(header))
            payload = header + data
            
        elif payload_type == 'text':
            # Text-based payload
            message = f"Packet {seq_num} sent at {datetime.now().isoformat()}"
            padding = 'X' * (self.payload_size - len(message) - 20)
            payload = (message + padding).encode('utf-8')
            
        elif payload_type == 'pattern':
            # Repeating pattern for analysis
            pattern = bytes([i % 256 for i in range(256)])
            repeats = self.payload_size // len(pattern)
            payload = pattern * repeats + pattern[:self.payload_size % len(pattern)]
            
        return payload
    
    def send_traffic(self, duration=None, num_packets=None, traffic_pattern='constant'):
        """
        Send traffic with different patterns
        - constant: Fixed rate
        - burst: Bursts of packets with idle periods
        - random: Random intervals
        - increasing: Gradually increasing rate
        """
        print(f"[SENDER] Starting transmission - Pattern: {traffic_pattern}")
        
        start_time = time.time()
        packets_sent = 0
        
        while True:
            if duration and (time.time() - start_time) > duration:
                break
            if num_packets and packets_sent >= num_packets:
                break
            
            # Generate payload
            payload = self.generate_payload(self.sequence_number, 'data')
            
            # Send packet
            try:
                self.sock.sendto(payload, (self.dest_ip, self.dest_port))
                
                log_entry = {
                    'timestamp': time.time(),
                    'seq_num': self.sequence_number,
                    'size': len(payload),
                    'destination': f"{self.dest_ip}:{self.dest_port}"
                }
                
                self.log_file.write(json.dumps(log_entry) + '\n')
                self.log_file.flush()
                
                if self.sequence_number % 100 == 0:
                    print(f"[SENDER] Sent packet {self.sequence_number}")
                
                self.sequence_number += 1
                packets_sent += 1
                
            except Exception as e:
                print(f"[SENDER ERROR] {e}")
            
            # Traffic pattern control
            if traffic_pattern == 'constant':
                time.sleep(1.0 / self.packet_rate)
                
            elif traffic_pattern == 'burst':
                if packets_sent % 50 < 10:  # Burst 10 packets
                    time.sleep(0.01)
                else:  # Idle
                    time.sleep(0.5)
                    
            elif traffic_pattern == 'random':
                time.sleep(random.uniform(0.01, 0.2))
                
            elif traffic_pattern == 'increasing':
                rate = self.packet_rate * (1 + packets_sent / 1000)
                time.sleep(1.0 / min(rate, 100))
        
        elapsed = time.time() - start_time
        print(f"[SENDER] Completed: {packets_sent} packets in {elapsed:.2f}s")
        print(f"[SENDER] Average rate: {packets_sent/elapsed:.2f} pps")
    
    def close(self):
        self.sock.close()
        self.log_file.close()


def main():
    sender = WirelessSender()
    
    try:
        # Run for 300 seconds with constant traffic
        sender.send_traffic(duration=300, traffic_pattern='constant')
    except KeyboardInterrupt:
        print("\n[SENDER] Stopped by user")
    finally:
        sender.close()


if __name__ == "__main__":
    main()