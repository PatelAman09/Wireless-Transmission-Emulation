"""
Usage example for the Wireless Channel Emulator
Demonstrates how to use the emulator for packet transmission simulation
"""

import socket
import threading
import time
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PacketSender:
    """Sends test packets to the emulator"""

    def __init__(self, emulator_port=12345):
        self.emulator_port = emulator_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_packet(self, data: bytes, delay: float = 0.1):
        """Send a single packet"""
        try:
            self.socket.sendto(data, ('localhost', self.emulator_port))
            logger.info(f"Sent packet: {len(data)} bytes")
            time.sleep(delay)
        except Exception as e:
            logger.error(f"Failed to send packet: {e}")

    def send_bulk_data(self, data: bytes, chunk_size: int = 1024):
        """Send large data in chunks"""
        num_chunks = (len(data) + chunk_size - 1) // chunk_size

        for i in range(num_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(data))
            chunk = data[start:end]

            # Add sequence number to chunk
            seq_header = f"SEQ:{i:04d}|".encode()
            packet = seq_header + chunk

            self.send_packet(packet)
            logger.info(f"Sent chunk {i + 1}/{num_chunks}")

    def close(self):
        """Close the socket"""
        self.socket.close()


class PacketReceiver:
    """Receives processed packets from the emulator"""

    def __init__(self, receive_port=12346):
        self.receive_port = receive_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.received_packets = []
        self.running = False

    def start_receiving(self, timeout: float = 30.0):
        """Start receiving packets"""
        try:
            self.socket.bind(('localhost', self.receive_port))
            self.socket.settimeout(1.0)
            self.running = True

            logger.info(f"Started receiving on port {self.receive_port}")
            start_time = time.time()

            while self.running and (time.time() - start_time) < timeout:
                try:
                    data, addr = self.socket.recvfrom(4096)
                    self.received_packets.append((time.time(), data, addr))
                    logger.info(f"Received packet: {len(data)} bytes from {addr}")

                except socket.timeout:
                    continue  # Keep looping

        except Exception as e:
            logger.error(f"Receiver error: {e}")
        finally:
            self.socket.close()

    def stop_receiving(self):
        """Stop receiving packets"""
        self.running = False

    def get_received_data(self):
        """Get all received packets"""
        return self.received_packets


def example_basic_usage():
    """Basic usage example"""
    logger.info("=== Basic Usage Example ===")
    logger.info("Make sure the emulator is running: python main.py")

    # Wait for user confirmation
    input("Press Enter when the emulator is running...")

    sender = PacketSender()
    receiver = PacketReceiver()

    # Start receiver in background thread
    receiver_thread = threading.Thread(target=receiver.start_receiving, args=(10,))
    receiver_thread.daemon = True
    receiver_thread.start()

    # Wait a moment for receiver to start
    time.sleep(1)

    # Send test packets
    test_messages = [
        b"Hello, Wireless World!",
        b"This is packet number 2",
        b"Testing different sizes: " + b"X" * 100,
        b"Final test packet"
    ]

    logger.info("Sending test packets...")
    for i, msg in enumerate(test_messages):
        sender.send_packet(msg)
        time.sleep(0.5)

    # Wait for all packets to be processed
    time.sleep(2)

    # Stop receiver
    receiver.stop_receiving()
    receiver_thread.join(timeout=5)

    # Check results
    received = receiver.get_received_data()
    logger.info(f"\nResults:")
    logger.info(f"Sent: {len(test_messages)} packets")
    logger.info(f"Received: {len(received)} packets")

    for i, (timestamp, data, addr) in enumerate(received):
        logger.info(f"  Packet {i + 1}: {len(data)} bytes at {timestamp:.3f}")

    sender.close()


def example_file_transfer():
    """File transfer simulation example"""
    logger.info("\n=== File Transfer Example ===")

    # Create a test file content
    file_content = b"This is a test file for wireless transmission.\n" * 100
    file_content += b"The file contains multiple lines and should be transmitted\n"
    file_content += b"through the wireless channel emulator in chunks.\n"
    file_content += b"END OF FILE\n"

    logger.info(f"Simulating transfer of {len(file_content)} byte file")

    sender = PacketSender()
    receiver = PacketReceiver()

    # Start receiver
    receiver_thread = threading.Thread(target=receiver.start_receiving, args=(15,))
    receiver_thread.daemon = True
    receiver_thread.start()

    time.sleep(1)

    # Send file in chunks
    logger.info("Starting file transfer...")
    sender.send_bulk_data(file_content, chunk_size=256)

    # Wait for transfer to complete
    time.sleep(3)

    # Stop receiver
    receiver.stop_receiving()
    receiver_thread.join(timeout=5)

    # Reconstruct received file
    received = receiver.get_received_data()
    received_data = b""

    # Sort by sequence number and reconstruct
    seq_packets = []
    for timestamp, data, addr in received:
        if data.startswith(b"SEQ:"):
            try:
                seq_str = data[4:8].decode()
                seq_num = int(seq_str)
                payload = data[9:]  # Skip "SEQ:XXXX|"
                seq_packets.append((seq_num, payload))
            except:
                logger.warning("Failed to parse sequence number")

    # Sort and reconstruct
    seq_packets.sort(key=lambda x: x[0])
    for seq_num, payload in seq_packets:
        received_data += payload

    # Compare
    success = received_data == file_content
    logger.info(f"\nFile Transfer Results:")
    logger.info(f"Original size: {len(file_content)} bytes")
    logger.info(f"Received size: {len(received_data)} bytes")
    logger.info(f"Integrity check: {'PASS' if success else 'FAIL'}")

    if not success:
        logger.info(
            f"First difference at byte: {next((i for i in range(min(len(file_content), len(received_data))) if file_content[i:i + 1] != received_data[i:i + 1]), -1)}")

    sender.close()


def example_performance_test():
    """Performance testing example"""
    logger.info("\n=== Performance Test Example ===")
    logger.info("This test sends packets at different rates to measure throughput")

    sender = PacketSender()
    receiver = PacketReceiver()

    # Start receiver
    receiver_thread = threading.Thread(target=receiver.start_receiving, args=(20,))
    receiver_thread.daemon = True
    receiver_thread.start()

    time.sleep(1)

    # Test different packet sizes and rates
    test_configs = [
        {"size": 64, "count": 50, "delay": 0.01},  # High rate, small packets
        {"size": 256, "count": 30, "delay": 0.05},  # Medium rate, medium packets
        {"size": 1024, "count": 20, "delay": 0.1},  # Low rate, large packets
    ]

    for config in test_configs:
        logger.info(
            f"\nTesting {config['size']} byte packets, {config['count']} packets, {1 / config['delay']:.1f} pps")

        start_time = time.time()

        for i in range(config["count"]):
            # Create test packet with sequence info
            payload = f"PKT:{i:04d}|".encode() + b"X" * (config["size"] - 9)
            sender.send_packet(payload, config["delay"])

        end_time = time.time()
        duration = end_time - start_time

        logger.info(f"Sent {config['count']} packets in {duration:.2f} seconds")
        logger.info(f"Average rate: {config['count'] / duration:.1f} pps")

    # Wait for all packets to be received
    time.sleep(5)

    # Stop receiver and analyze results
    receiver.stop_receiving()
    receiver_thread.join(timeout=5)

    received = receiver.get_received_data()
    total_bytes = sum(len(data) for _, data, _ in received)

    logger.info(f"\nPerformance Results:")
    logger.info(f"Total packets received: {len(received)}")
    logger.info(f"Total bytes received: {total_bytes}")
    logger.info(f"Average packet size: {total_bytes / len(received):.1f} bytes" if received else 0)

    sender.close()


def main():
    """Main function to run examples"""
    print("Wireless Channel Emulator - Usage Examples")
    print("=" * 50)
    print()
    print("Available examples:")
    print("1. Basic usage (simple packet transmission)")
    print("2. File transfer simulation")
    print("3. Performance testing")
    print("4. Run all examples")
    print()

    try:
        choice = input("Choose an example (1-4): ").strip()

        if choice == '1':
            example_basic_usage()
        elif choice == '2':
            example_file_transfer()
        elif choice == '3':
            example_performance_test()
        elif choice == '4':
            example_basic_usage()
            example_file_transfer()
            example_performance_test()
        else:
            print("Invalid choice")
            return 1

        logger.info("\nExample completed!")

    except KeyboardInterrupt:
        logger.info("\nExample interrupted by user")
    except Exception as e:
        logger.error(f"Example failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
