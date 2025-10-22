import yaml
import time
import numpy as np
import os
import sys

# Add src directory to path
sys.path.append('/app/src')

from transmitter import Transmitter
from receiver import Receiver
from channel import AWGNChannel


def load_config():
    """Load configuration from YAML file"""
    config_path = '/app/config/config.yaml'
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print("Configuration loaded successfully")
        return config
    except FileNotFoundError:
        print(f"Config file not found at {config_path}")
        # Create default config
        default_config = {
            'transmitter': {
                'sample_rate': 1000000,
                'carrier_freq': 100000,
                'symbol_rate': 50000
            },
            'receiver': {
                'sample_rate': 1000000,
                'carrier_freq': 100000,
                'symbol_rate': 50000
            },
            'channel': {
                'snr_db': 20,
                'noise_factor': 0.1
            }
        }
        return default_config


def simulate_transmission(config, test_data):
    """Run complete transmission simulation"""
    print("=" * 50)
    print("SimuRF - Wireless Transmission Emulation")
    print("=" * 50)

    # Initialize components
    transmitter = Transmitter(config)
    receiver = Receiver(config)
    channel = AWGNChannel(config)

    print(f"\n1. Transmitting {len(test_data)} bytes: '{test_data.decode()}'")

    # Transmit
    start_time = time.time()
    transmitted_samples = transmitter.transmit(test_data)
    tx_time = time.time() - start_time

    print(f"\n2. Channel Simulation")
    # Channel simulation
    received_samples = channel.process(transmitted_samples)

    print(f"\n3. Receiving")
    # Receive
    start_time = time.time()
    received_data = receiver.receive(received_samples)
    rx_time = time.time() - start_time

    # Results
    print(f"\n4. Results")
    print(f"Original data: {test_data}")
    print(f"Received data: {received_data}")

    # Calculate performance metrics
    if received_data:
        success = test_data == received_data
        print(f"Transmission successful: {success}")

        if len(test_data) == len(received_data):
            errors = sum(1 for a, b in zip(test_data, received_data) if a != b)
            ber = errors / (len(test_data) * 8)  # Bit error rate
            print(f"Bit Errors: {errors}")
            print(f"Bit Error Rate: {ber:.6f}")

        print(f"Transmission time: {tx_time:.4f}s")
        print(f"Reception time: {rx_time:.4f}s")
        print(f"Total samples processed: {len(transmitted_samples)}")
    else:
        print("ERROR: No data received!")

    return success


def main():
    """Main application entry point"""
    # Load configuration
    config = load_config()

    # Test with different data sizes
    test_messages = [
        b"Hello Aman",
        b"Test message 123789",
        b"Wireless emulation Test1"
    ]

    success_count = 0
    for i, test_data in enumerate(test_messages, 1):
        print(f"\n{'=' * 20} Test {i} {'=' * 20}")
        success = simulate_transmission(config, test_data)
        if success:
            success_count += 1

    print(f"\n{'=' * 50}")
    print(f"Summary: {success_count}/{len(test_messages)} tests passed")
    print("SimuRF Phase 1 completed!")


if __name__ == "__main__":
    main()