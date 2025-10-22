"""
Test client to send packets to the SimuRF simulation server.
Demonstrates both UDP and TCP communication.
"""

import socket
import struct
import json
import time
import argparse


class SimuRFClient:
    """Client for sending data to SimuRF simulation server"""

    def __init__(self, host='localhost', udp_port=5000, tcp_port=5001):
        self.host = host
        self.udp_port = udp_port
        self.tcp_port = tcp_port

    def send_udp(self, data):
        """Send data via UDP (no response expected)"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            if isinstance(data, str):
                data = data.encode('utf-8')

            print(f"Sending {len(data)} bytes via UDP to {self.host}:{self.udp_port}")
            sock.sendto(data, (self.host, self.udp_port))
            print("UDP packet sent successfully")

        except Exception as e:
            print(f"UDP send error: {e}")
        finally:
            sock.close()

    def send_tcp(self, data):
        """Send data via TCP and receive response"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            if isinstance(data, str):
                data = data.encode('utf-8')

            print(f"Connecting to {self.host}:{self.tcp_port}")
            sock.connect((self.host, self.tcp_port))
            print(f"Connected. Sending {len(data)} bytes...")

            # Send length header + data
            sock.sendall(struct.pack('!I', len(data)))
            sock.sendall(data)
            print("Data sent. Waiting for response...")

            # Receive response length
            length_data = self._recv_exact(sock, 4)
            if not length_data:
                print("No response received")
                return None

            response_length = struct.unpack('!I', length_data)[0]

            # Receive response data
            response_data = self._recv_exact(sock, response_length)
            if not response_data:
                print("Incomplete response received")
                return None

            # Parse JSON response
            result = json.loads(response_data.decode('utf-8'))

            print("\n" + "=" * 60)
            print("RESPONSE FROM SERVER")
            print("=" * 60)
            print(json.dumps(result, indent=2))
            print("=" * 60 + "\n")

            return result

        except Exception as e:
            print(f"TCP error: {e}")
            return None
        finally:
            sock.close()

    def _recv_exact(self, sock, n):
        """Receive exactly n bytes"""
        data = b''
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data


def run_interactive_mode(client):
    """Interactive mode for manual testing"""
    print("\n" + "=" * 60)
    print("SimuRF Test Client - Interactive Mode")
    print("=" * 60)
    print("Commands:")
    print("  udp <message>  - Send message via UDP")
    print("  tcp <message>  - Send message via TCP")
    print("  quit           - Exit")
    print("=" * 60 + "\n")

    while True:
        try:
            cmd = input("simurf> ").strip()

            if not cmd:
                continue

            if cmd.lower() == 'quit':
                break

            parts = cmd.split(maxsplit=1)
            if len(parts) < 2:
                print("Invalid command. Use: udp/tcp <message>")
                continue

            protocol, message = parts

            if protocol.lower() == 'udp':
                client.send_udp(message)
            elif protocol.lower() == 'tcp':
                client.send_tcp(message)
            else:
                print(f"Unknown protocol: {protocol}")

        except KeyboardInterrupt:
            print("\n")
            break
        except Exception as e:
            print(f"Error: {e}")


def run_batch_tests(client):
    """Run a series of automated tests"""
    test_messages = [
        "Hello SimuRF",
        "Testing wireless simulation",
        "QPSK modulation test message 12345",
        "A" * 100,  # Long message
        "Short",
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit",
    ]

    print("\n" + "=" * 60)
    print("Running Batch Tests")
    print("=" * 60 + "\n")

    results = []

    for i, msg in enumerate(test_messages, 1):
        print(f"\nTest {i}/{len(test_messages)}: '{msg[:50]}{'...' if len(msg) > 50 else ''}'")
        print("-" * 60)

        # Test TCP (with response)
        result = client.send_tcp(msg)
        results.append(result)

        time.sleep(1)  # Small delay between tests

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    successful = sum(1 for r in results if r and r.get('success'))
    total = len(results)

    print(f"Total Tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")

    if results:
        avg_ber = sum(r.get('bit_error_rate', 0) for r in results if r) / len(results)
        print(f"Average BER: {avg_ber:.6f}")

    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='SimuRF Test Client')
    parser.add_argument('--host', default='localhost', help='Server hostname/IP')
    parser.add_argument('--udp-port', type=int, default=5000, help='UDP port')
    parser.add_argument('--tcp-port', type=int, default=5001, help='TCP port')
    parser.add_argument('--mode', choices=['interactive', 'batch'], default='interactive',
                        help='Operation mode')
    parser.add_argument('--protocol', choices=['udp', 'tcp'], default='tcp',
                        help='Protocol for single message')
    parser.add_argument('--message', help='Single message to send')

    args = parser.parse_args()

    client = SimuRFClient(args.host, args.udp_port, args.tcp_port)

    if args.message:
        # Send single message
        if args.protocol == 'udp':
            client.send_udp(args.message)
        else:
            client.send_tcp(args.message)
    elif args.mode == 'batch':
        run_batch_tests(client)
    else:
        run_interactive_mode(client)


if __name__ == "__main__":
    main()
