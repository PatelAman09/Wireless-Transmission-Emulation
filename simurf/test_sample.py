"""
Simple test script for the Wireless Channel Emulator
Tests the end-to-end functionality without network sockets
"""

import sys
import os
import numpy as np
import logging

# Add the parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transmitter import WirelessTransmitter
from channel import ChannelModel
from receiver import WirelessReceiver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_end_to_end_transmission():
    """Test complete transmission chain"""
    logger.info("Starting end-to-end transmission test...")

    # Test parameters
    test_data = b"Hello, Wireless World! This is a test packet for the channel emulator."
    modulations = ['bpsk', 'qpsk', '16qam']
    channels = ['awgn', 'rayleigh', 'rician']
    snr_values = [0, 5, 10, 15, 20]  # dB

    results = {}

    for modulation in modulations:
        results[modulation] = {}
        logger.info(f"\n=== Testing {modulation.upper()} ===")

        for channel_type in channels:
            results[modulation][channel_type] = {}
            logger.info(f"\n--- {channel_type.title()} Channel ---")

            success_count = 0
            total_tests = len(snr_values)

            for snr_db in snr_values:
                try:
                    # Initialize components
                    tx = WirelessTransmitter(modulation=modulation)
                    channel = ChannelModel(channel_type=channel_type, snr_db=snr_db)
                    rx = WirelessReceiver(modulation=modulation)

                    # Transmit
                    tx_signal = tx.transmit(test_data)

                    # Apply channel
                    rx_signal = channel.apply_channel(tx_signal)

                    # Receive
                    recovered_data = rx.receive(rx_signal)

                    # Check if packet was recovered successfully
                    if recovered_data is not None and recovered_data == test_data:
                        success = True
                        success_count += 1
                        status = "PASS"
                    else:
                        success = False
                        status = "FAIL"

                    results[modulation][channel_type][snr_db] = success

                    logger.info(f"SNR: {snr_db:2d} dB | Status: {status} | "
                                f"TX: {len(tx_signal):6d} samples | "
                                f"RX: {'OK' if recovered_data else 'LOST'}")

                except Exception as e:
                    logger.error(f"Error at SNR {snr_db} dB: {e}")
                    results[modulation][channel_type][snr_db] = False

            success_rate = success_count / total_tests * 100
            logger.info(f"Success rate: {success_rate:.1f}% ({success_count}/{total_tests})")

    return results


def test_individual_components():
    """Test individual components"""
    logger.info("\n=== Testing Individual Components ===")

    # Test data
    test_bits = np.array([1, 0, 1, 1, 0, 0, 1, 0], dtype=np.uint8)
    test_packet = b"Test packet"

    # Test modulation schemes
    from utils.modulation import ModulationSchemes
    mod_schemes = ModulationSchemes()

    logger.info("Testing modulation schemes...")

    # BPSK test
    bpsk_symbols = mod_schemes.bpsk_modulate(test_bits)
    bpsk_bits_recovered = mod_schemes.bpsk_demodulate(bpsk_symbols)
    bpsk_success = np.array_equal(test_bits, bpsk_bits_recovered)
    logger.info(f"BPSK: {'PASS' if bpsk_success else 'FAIL'}")

    # QPSK test
    qpsk_symbols = mod_schemes.qpsk_modulate(test_bits)
    qpsk_bits_recovered = mod_schemes.qpsk_demodulate(qpsk_symbols)
    qpsk_success = np.array_equal(test_bits, qpsk_bits_recovered)
    logger.info(f"QPSK: {'PASS' if qpsk_success else 'FAIL'}")

    # 16-QAM test
    qam_symbols = mod_schemes.qam16_modulate(test_bits)
    qam_bits_recovered = mod_schemes.qam16_demodulate(qam_symbols)
    qam_success = np.array_equal(test_bits, qam_bits_recovered)
    logger.info(f"16-QAM: {'PASS' if qam_success else 'FAIL'}")

    # Test transmitter
    logger.info("\nTesting transmitter...")
    tx = WirelessTransmitter(modulation='qpsk')
    tx_signal = tx.transmit(test_packet)
    tx_success = len(tx_signal) > 0 and tx_signal.dtype == complex
    logger.info(f"Transmitter: {'PASS' if tx_success else 'FAIL'} - Generated {len(tx_signal)} samples")

    # Test channel models
    logger.info("\nTesting channel models...")
    test_signal = np.random.randn(1000) + 1j * np.random.randn(1000)

    # AWGN channel
    awgn_channel = ChannelModel(channel_type='awgn', snr_db=10)
    awgn_output = awgn_channel.apply_channel(test_signal)
    awgn_success = len(awgn_output) == len(test_signal)
    logger.info(f"AWGN Channel: {'PASS' if awgn_success else 'FAIL'}")

    # Rayleigh channel
    rayleigh_channel = ChannelModel(channel_type='rayleigh', snr_db=10)
    rayleigh_output = rayleigh_channel.apply_channel(test_signal)
    rayleigh_success = len(rayleigh_output) == len(test_signal)
    logger.info(f"Rayleigh Channel: {'PASS' if rayleigh_success else 'FAIL'}")

    # Rician channel
    rician_channel = ChannelModel(channel_type='rician', snr_db=10)
    rician_output = rician_channel.apply_channel(test_signal)
    rician_success = len(rician_output) == len(test_signal)
    logger.info(f"Rician Channel: {'PASS' if rician_success else 'FAIL'}")

    # Test receiver
    logger.info("\nTesting receiver...")
    rx = WirelessReceiver(modulation='qpsk')
    # Use a clean signal for receiver test
    clean_signal = tx.transmit(test_packet)
    rx_packet = rx.receive(clean_signal)
    rx_success = rx_packet == test_packet
    logger.info(f"Receiver: {'PASS' if rx_success else 'FAIL'}")

    return {
        'bpsk': bpsk_success,
        'qpsk': qpsk_success,
        '16qam': qam_success,
        'transmitter': tx_success,
        'awgn': awgn_success,
        'rayleigh': rayleigh_success,
        'rician': rician_success,
        'receiver': rx_success
    }


def test_performance_metrics():
    """Test performance under various conditions"""
    logger.info("\n=== Performance Metrics Test ===")

    # Generate test data
    packet_sizes = [64, 256, 1024]  # bytes
    snr_range = np.arange(-5, 21, 5)  # -5 to 20 dB

    performance_data = {}

    for packet_size in packet_sizes:
        logger.info(f"\nTesting packet size: {packet_size} bytes")

        # Generate random test data
        test_data = np.random.bytes(packet_size)

        performance_data[packet_size] = {
            'snr_db': [],
            'success_rate': [],
            'throughput_bps': []
        }

        for snr_db in snr_range:
            success_count = 0
            total_time = 0
            num_trials = 10

            for trial in range(num_trials):
                try:
                    import time
                    start_time = time.time()

                    # Initialize system
                    tx = WirelessTransmitter(modulation='qpsk')
                    channel = ChannelModel(channel_type='awgn', snr_db=snr_db)
                    rx = WirelessReceiver(modulation='qpsk')

                    # Process packet
                    tx_signal = tx.transmit(test_data)
                    rx_signal = channel.apply_channel(tx_signal)
                    recovered_data = rx.receive(rx_signal)

                    end_time = time.time()
                    total_time += (end_time - start_time)

                    if recovered_data == test_data:
                        success_count += 1

                except Exception as e:
                    logger.debug(f"Trial {trial} failed: {e}")

            success_rate = success_count / num_trials
            avg_time = total_time / num_trials
            throughput = (packet_size * 8 * success_rate) / avg_time if avg_time > 0 else 0

            performance_data[packet_size]['snr_db'].append(snr_db)
            performance_data[packet_size]['success_rate'].append(success_rate)
            performance_data[packet_size]['throughput_bps'].append(throughput)

            logger.info(f"SNR: {snr_db:2d} dB | Success: {success_rate:.2f} | "
                        f"Throughput: {throughput / 1000:.1f} kbps")

    return performance_data


def run_socket_test():
    """Test socket-based communication (requires emulator to be running)"""
    logger.info("\n=== Socket Communication Test ===")

    import socket
    import threading
    import time

    def send_test_packets():
        """Send test packets to the emulator"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            test_messages = [
                b"Hello World!",
                b"This is a test message",
                b"Short",
                b"A" * 100,  # Longer message
                bytes(range(256))  # Binary data
            ]

            for i, msg in enumerate(test_messages):
                sock.sendto(msg, ('localhost', 12345))
                logger.info(f"Sent message {i + 1}: {len(msg)} bytes")
                time.sleep(0.1)

            sock.close()

        except Exception as e:
            logger.error(f"Error sending packets: {e}")

    def receive_test_packets():
        """Receive processed packets from the emulator"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('localhost', 12346))
            sock.settimeout(5.0)  # 5 second timeout

            received_count = 0
            start_time = time.time()

            while received_count < 5 and (time.time() - start_time) < 10:
                try:
                    data, addr = sock.recvfrom(4096)
                    received_count += 1
                    logger.info(f"Received packet {received_count}: {len(data)} bytes from {addr}")
                except socket.timeout:
                    break

            sock.close()
            return received_count

        except Exception as e:
            logger.error(f"Error receiving packets: {e}")
            return 0

    logger.info("Note: This test requires the emulator to be running separately")
    logger.info("Run: python main.py --verbose")
    logger.info("Then run this test in another terminal")

    # Start receiver in background
    receiver_thread = threading.Thread(target=receive_test_packets)
    receiver_thread.daemon = True
    receiver_thread.start()

    # Wait a moment, then send packets
    time.sleep(1)
    send_test_packets()

    # Wait for receiver to finish
    receiver_thread.join(timeout=15)


def main():
    """Run all tests"""
    print("Wireless Channel Emulator - Test Suite")
    print("=" * 50)

    try:
        # Test individual components
        component_results = test_individual_components()

        # Test end-to-end transmission
        e2e_results = test_end_to_end_transmission()

        # Test performance metrics
        performance_results = test_performance_metrics()

        # Print summary
        logger.info("\n" + "=" * 50)
        logger.info("TEST SUMMARY")
        logger.info("=" * 50)

        # Component test summary
        logger.info("\nComponent Tests:")
        for component, result in component_results.items():
            status = "PASS" if result else "FAIL"
            logger.info(f"  {component:12s}: {status}")

        # E2E test summary
        logger.info("\nEnd-to-End Tests:")
        for mod in e2e_results:
            for channel in e2e_results[mod]:
                success_count = sum(e2e_results[mod][channel].values())
                total_count = len(e2e_results[mod][channel])
                success_rate = success_count / total_count * 100
                logger.info(f"  {mod:6s} + {channel:8s}: {success_rate:5.1f}% "
                            f"({success_count}/{total_count})")

        # Performance summary
        logger.info("\nPerformance Tests:")
        for packet_size in performance_results:
            max_throughput = max(performance_results[packet_size]['throughput_bps'])
            logger.info(f"  {packet_size:4d} bytes: Max throughput {max_throughput / 1000:.1f} kbps")

        logger.info("\nAll tests completed!")

        # Optionally run socket test
        user_input = input("\nRun socket communication test? (y/n): ")
        if user_input.lower() == 'y':
            run_socket_test()

    except KeyboardInterrupt:
        logger.info("\nTests interrupted by user")
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())