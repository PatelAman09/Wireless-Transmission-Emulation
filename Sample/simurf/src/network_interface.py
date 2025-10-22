import socket
import threading
import queue
import json
import struct
import time
from datetime import datetime


class NetworkInterface:
    """
    Network interface for receiving packets from external sources.
    Supports both UDP and TCP connections.
    """

    def __init__(self, config, packet_callback):
        self.config = config
        self.packet_callback = packet_callback

        # Network configuration
        self.udp_port = config.get('network', {}).get('udp_port', 5000)
        self.tcp_port = config.get('network', {}).get('tcp_port', 5001)
        self.host = config.get('network', {}).get('host', '0.0.0.0')

        # Packet queue for async processing
        self.packet_queue = queue.Queue(maxsize=100)

        # Threading control
        self.running = False
        self.threads = []

        # Statistics
        self.stats = {
            'packets_received': 0,
            'packets_processed': 0,
            'packets_dropped': 0,
            'bytes_received': 0,
            'start_time': None
        }

    def start(self):
        """Start all network listeners"""
        self.running = True
        self.stats['start_time'] = time.time()

        # Start UDP listener
        udp_thread = threading.Thread(target=self._udp_listener, daemon=True)
        udp_thread.start()
        self.threads.append(udp_thread)

        # Start TCP listener
        tcp_thread = threading.Thread(target=self._tcp_listener, daemon=True)
        tcp_thread.start()
        self.threads.append(tcp_thread)

        # Start packet processor
        processor_thread = threading.Thread(target=self._packet_processor, daemon=True)
        processor_thread.start()
        self.threads.append(processor_thread)

        print(f"Network Interface started:")
        print(f"  UDP listening on {self.host}:{self.udp_port}")
        print(f"  TCP listening on {self.host}:{self.tcp_port}")

    def stop(self):
        """Stop all network listeners"""
        self.running = False
        for thread in self.threads:
            thread.join(timeout=2)
        print("Network Interface stopped")

    def _udp_listener(self):
        """UDP socket listener for connectionless packet reception"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.udp_port))
        sock.settimeout(1.0)  # Non-blocking with timeout

        print(f"UDP listener ready on port {self.udp_port}")

        while self.running:
            try:
                data, addr = sock.recvfrom(65536)  # Max UDP packet size

                self.stats['packets_received'] += 1
                self.stats['bytes_received'] += len(data)

                packet = {
                    'protocol': 'UDP',
                    'source': addr,
                    'data': data,
                    'timestamp': datetime.now().isoformat(),
                    'size': len(data)
                }

                try:
                    self.packet_queue.put_nowait(packet)
                    print(f"UDP: Received {len(data)} bytes from {addr}")
                except queue.Full:
                    self.stats['packets_dropped'] += 1
                    print(f"UDP: Queue full, dropped packet from {addr}")

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"UDP listener error: {e}")

        sock.close()

    def _tcp_listener(self):
        """TCP socket listener for connection-oriented communication"""
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.host, self.tcp_port))
        server_sock.listen(5)
        server_sock.settimeout(1.0)

        print(f"TCP listener ready on port {self.tcp_port}")

        while self.running:
            try:
                client_sock, addr = server_sock.accept()
                # Handle each client in a separate thread
                client_thread = threading.Thread(
                    target=self._handle_tcp_client,
                    args=(client_sock, addr),
                    daemon=True
                )
                client_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"TCP listener error: {e}")

        server_sock.close()

    def _handle_tcp_client(self, sock, addr):
        """Handle individual TCP client connection"""
        print(f"TCP: Client connected from {addr}")

        try:
            while self.running:
                # Read packet length header (4 bytes)
                length_data = self._recv_exact(sock, 4)
                if not length_data:
                    break

                packet_length = struct.unpack('!I', length_data)[0]

                # Read packet data
                data = self._recv_exact(sock, packet_length)
                if not data:
                    break

                self.stats['packets_received'] += 1
                self.stats['bytes_received'] += len(data)

                packet = {
                    'protocol': 'TCP',
                    'source': addr,
                    'data': data,
                    'timestamp': datetime.now().isoformat(),
                    'size': len(data),
                    'socket': sock  # Keep socket for response
                }

                try:
                    self.packet_queue.put_nowait(packet)
                    print(f"TCP: Received {len(data)} bytes from {addr}")
                except queue.Full:
                    self.stats['packets_dropped'] += 1
                    print(f"TCP: Queue full, dropped packet from {addr}")

        except Exception as e:
            print(f"TCP client error from {addr}: {e}")
        finally:
            sock.close()
            print(f"TCP: Client disconnected from {addr}")

    def _recv_exact(self, sock, n):
        """Receive exactly n bytes from socket"""
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def _packet_processor(self):
        """Process packets from queue and pass to simulation"""
        print("Packet processor started")

        while self.running:
            try:
                packet = self.packet_queue.get(timeout=1)

                # Process packet through simulation
                result = self.packet_callback(packet)

                self.stats['packets_processed'] += 1

                # Send response back if TCP
                if packet['protocol'] == 'TCP' and 'socket' in packet:
                    self._send_tcp_response(packet['socket'], result)

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Packet processor error: {e}")

    def _send_tcp_response(self, sock, result):
        """Send response back to TCP client"""
        try:
            response_data = json.dumps(result).encode('utf-8')
            # Send length header + data
            sock.sendall(struct.pack('!I', len(response_data)))
            sock.sendall(response_data)
        except Exception as e:
            print(f"Error sending TCP response: {e}")

    def get_statistics(self):
        """Get network interface statistics"""
        uptime = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0

        return {
            **self.stats,
            'uptime_seconds': uptime,
            'packets_per_second': self.stats['packets_received'] / uptime if uptime > 0 else 0,
            'queue_size': self.packet_queue.qsize()
        }
