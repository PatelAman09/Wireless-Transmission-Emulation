import socket
import time
import struct
import os
import json
from collections import defaultdict

class WirelessReceiver:
    def __init__(self):
        self.listen_port = int(os.getenv('LISTEN_PORT', 5000))
        self.log_file = open('/logs/receiver.log', 'w')
        self.metrics_file = open('/logs/receiver_metrics.log', 'w')
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', self.listen_port))
        
        # Metrics
        self.total_packets = 0
        self.total_bytes = 0
        self.start_time = time.time()
        self.last_seq = -1
        self.lost_packets = 0
        self.out_of_order = 0
        self.duplicate_packets = 0
        
        self.received_sequences = set()
        self.latencies = []
        
        print(f"[RECEIVER] Listening on port {self.listen_port}")
    
    def parse_packet(self, data):
        """
        Parse packet header if structured format
        """
        try:
            if len(data) >= 16:
                seq_num, timestamp_us, payload_size = struct.unpack('!IQI', data[:16])
                return {
                    'seq_num': seq_num,
                    'timestamp': timestamp_us / 1e6,
                    'payload_size': payload_size,
                    'data': data[16:]
                }
        except:
            pass
        
        return {
            'seq_num': None,
            'timestamp': None,
            'payload_size': len(data),
            'data': data
        }
    
    def calculate_metrics(self):
        """
        Calculate performance metrics
        """
        elapsed = time.time() - self.start_time
        
        metrics = {
            'timestamp': time.time(),
            'total_packets': self.total_packets,
            'total_bytes': self.total_bytes,
            'elapsed_time': elapsed,
            'throughput_mbps': (self.total_bytes * 8) / (elapsed * 1e6) if elapsed > 0 else 0,
            'packet_rate_pps': self.total_packets / elapsed if elapsed > 0 else 0,
            'lost_packets': self.lost_packets,
            'packet_loss_rate': self.lost_packets / (self.total_packets + self.lost_packets) if self.total_packets > 0 else 0,
            'out_of_order': self.out_of_order,
            'duplicates': self.duplicate_packets,
            'avg_latency_ms': sum(self.latencies) / len(self.latencies) * 1000 if self.latencies else 0,
            'max_latency_ms': max(self.latencies) * 1000 if self.latencies else 0,
            'min_latency_ms': min(self.latencies) * 1000 if self.latencies else 0
        }
        
        return metrics
    
    def receive_packets(self):
        """
        Receive and analyze packets
        """
        print("[RECEIVER] Ready to receive packets...")
        
        metrics_interval = 10  # Report metrics every 10 seconds
        last_metrics_time = time.time()
        
        while True:
            try:
                data, addr = self.sock.recvfrom(65535)
                recv_time = time.time()
                
                self.total_packets += 1
                self.total_bytes += len(data)
                
                # Parse packet
                packet_info = self.parse_packet(data)
                
                # Analyze sequence numbers
                if packet_info['seq_num'] is not None:
                    seq = packet_info['seq_num']
                    
                    # Detect packet loss
                    if self.last_seq >= 0:
                        expected_seq = self.last_seq + 1
                        if seq > expected_seq:
                            lost = seq - expected_seq
                            self.lost_packets += lost
                            print(f"[RECEIVER] Packet loss detected: {lost} packets ({expected_seq} to {seq-1})")
                        elif seq < expected_seq:
                            self.out_of_order += 1
                            print(f"[RECEIVER] Out-of-order packet: {seq}")
                    
                    # Detect duplicates
                    if seq in self.received_sequences:
                        self.duplicate_packets += 1
                        print(f"[RECEIVER] Duplicate packet: {seq}")
                    else:
                        self.received_sequences.add(seq)
                    
                    self.last_seq = max(self.last_seq, seq)
                    
                    # Calculate latency
                    if packet_info['timestamp']:
                        latency = recv_time - packet_info['timestamp']
                        self.latencies.append(latency)
                        if len(self.latencies) > 1000:
                            self.latencies = self.latencies[-1000:]
                
                # Log packet
                log_entry = {
                    'timestamp': recv_time,
                    'seq_num': packet_info['seq_num'],
                    'size': len(data),
                    'source': addr[0]
                }
                self.log_file.write(json.dumps(log_entry) + '\n')
                
                # Periodic metrics reporting
                if time.time() - last_metrics_time >= metrics_interval:
                    metrics = self.calculate_metrics()
                    
                    print(f"\n[RECEIVER METRICS]")
                    print(f"  Packets: {metrics['total_packets']}")
                    print(f"  Throughput: {metrics['throughput_mbps']:.2f} Mbps")
                    print(f"  Packet Rate: {metrics['packet_rate_pps']:.2f} pps")
                    print(f"  Packet Loss: {metrics['packet_loss_rate']*100:.2f}%")
                    print(f"  Avg Latency: {metrics['avg_latency_ms']:.2f} ms")
                    print(f"  Out-of-Order: {metrics['out_of_order']}")
                    print(f"  Duplicates: {metrics['duplicates']}\n")
                    
                    self.metrics_file.write(json.dumps(metrics) + '\n')
                    self.metrics_file.flush()
                    self.log_file.flush()
                    
                    last_metrics_time = time.time()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[RECEIVER ERROR] {e}")
        
        # Final metrics
        print("\n[RECEIVER] Final Metrics:")
        final_metrics = self.calculate_metrics()
        for key, value in final_metrics.items():
            print(f"  {key}: {value}")
    
    def close(self):
        self.sock.close()
        self.log_file.close()
        self.metrics_file.close()


def main():
    receiver = WirelessReceiver()
    
    try:
        receiver.receive_packets()
    except KeyboardInterrupt:
        print("\n[RECEIVER] Stopped by user")
    finally:
        receiver.close()


if __name__ == "__main__":
    main()