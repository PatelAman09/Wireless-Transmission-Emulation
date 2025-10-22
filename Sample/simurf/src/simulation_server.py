import yaml
import signal
import sys
import time
from datetime import datetime

sys.path.append('/app/src')

from transmitter import Transmitter
from receiver import Receiver
from channel import AWGNChannel
from network_interface import NetworkInterface


class SimulationServer:
    """
    Main simulation server that processes incoming packets
    through the wireless channel simulation.
    """

    def __init__(self, config_path='/app/config/config.yaml'):
        self.config = self.load_config(config_path)

        # Initialize RF components
        self.transmitter = Transmitter(self.config)
        self.receiver = Receiver(self.config)
        self.channel = AWGNChannel(self.config)

        # Initialize network interface
        self.network = NetworkInterface(self.config, self.process_packet)

        # Simulation statistics
        self.sim_stats = {
            'total_simulations': 0,
            'successful_transmissions': 0,
            'failed_transmissions': 0,
            'total_bits_transmitted': 0,
            'total_bit_errors': 0
        }

        # Setup graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

    def load_config(self, config_path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            print(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            print(f"Config file not found at {config_path}, using defaults")
            return self.get_default_config()

    def get_default_config(self):
        """Return default configuration"""
        return {
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
                'snr_db': 25,  # Increased for better reliability
                'noise_factor': 0.05
            },
            'network': {
                'host': '0.0.0.0',
                'udp_port': 5000,
                'tcp_port': 5001
            }
        }

    def process_packet(self, packet):
        """
        Process a received packet through the RF simulation chain.
        This is the callback function for the network interface.
        """
        self.sim_stats['total_simulations'] += 1

        start_time = time.time()

        print(f"\n{'=' * 60}")
        print(f"Processing Packet #{self.sim_stats['total_simulations']}")
        print(f"Protocol: {packet['protocol']}")
        print(f"Source: {packet['source']}")
        print(f"Timestamp: {packet['timestamp']}")
        print(f"Size: {packet['size']} bytes")
        print(f"{'=' * 60}")

        try:
            # Extract payload data
            payload = packet['data']
            original_data_length = len(payload)

            # Step 1: Transmit (now returns signal AND symbol count)
            print("\n[TRANSMITTER] Encoding and modulating...")
            tx_signal, original_symbol_count = self.transmitter.transmit(payload)

            # Step 2: Channel simulation
            print("\n[CHANNEL] Adding noise and impairments...")
            rx_signal = self.channel.process(tx_signal)

            # Step 3: Receive (pass expected data length for synchronization)
            print("\n[RECEIVER] Demodulating and decoding...")
            decoded_data = self.receiver.receive(rx_signal, original_data_length)

            # Calculate metrics
            processing_time = time.time() - start_time
            success = (payload == decoded_data)

            if success:
                self.sim_stats['successful_transmissions'] += 1
            else:
                self.sim_stats['failed_transmissions'] += 1

            # Calculate BER if data was received
            bit_errors = 0
            ber = 0.0

            if decoded_data:
                # Compare common portion of data
                min_len = min(len(payload), len(decoded_data))
                for i in range(min_len):
                    orig_byte = payload[i]
                    recv_byte = decoded_data[i]
                    # Count bit differences
                    xor = orig_byte ^ recv_byte
                    bit_errors += bin(xor).count('1')

                total_bits = min_len * 8
                if total_bits > 0:
                    ber = bit_errors / total_bits

                self.sim_stats['total_bits_transmitted'] += total_bits
                self.sim_stats['total_bit_errors'] += bit_errors

            # Prepare result
            result = {
                'success': success,
                'original_size': len(payload),
                'received_size': len(decoded_data) if decoded_data else 0,
                'bit_errors': bit_errors,
                'bit_error_rate': ber,
                'processing_time_ms': processing_time * 1000,
                'snr_db': self.config['channel']['snr_db'],
                'original_data': payload.hex() if len(payload) <= 100 else payload[:100].hex() + '...',
                'received_data': decoded_data.hex() if decoded_data and len(decoded_data) <= 100 else (
                    decoded_data[:100].hex() + '...' if decoded_data else ''),
                'match': payload == decoded_data,
                'timestamp': datetime.now().isoformat(),
                'symbols_generated': original_symbol_count,
                'samples_generated': len(tx_signal)
            }

            # Print results
            print(f"\n{'=' * 60}")
            print("SIMULATION RESULTS")
            print(f"{'=' * 60}")
            print(f"Success: {result['success']}")
            print(f"Original Size: {result['original_size']} bytes")
            print(f"Received Size: {result['received_size']} bytes")
            print(f"Symbols Generated: {result['symbols_generated']}")
            print(f"Samples Generated: {result['samples_generated']}")
            print(f"Bit Errors: {bit_errors}")
            print(f"Bit Error Rate: {ber:.6f}")
            print(f"Processing Time: {processing_time * 1000:.2f} ms")
            print(f"Data Match: {result['match']}")

            if not result['match']:
                print(f"\nData Comparison:")
                print(f"Original: {payload[:50]}...")
                print(f"Received: {decoded_data[:50] if decoded_data else 'NO DATA'}...")

                if decoded_data and len(payload) != len(decoded_data):
                    print(f"Length mismatch: {len(payload)} vs {len(decoded_data)} bytes")

            print(f"{'=' * 60}\n")

            return result

        except Exception as e:
            print(f"ERROR during simulation: {e}")
            import traceback
            traceback.print_exc()

            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def run(self):
        """Start the simulation server"""
        print("\n" + "=" * 70)
        print("SimuRF - Wireless Network Simulation Server")
        print("=" * 70)
        print(f"Sample Rate: {self.config['transmitter']['sample_rate']} Hz")
        print(f"Carrier Frequency: {self.config['transmitter']['carrier_freq']} Hz")
        print(f"Symbol Rate: {self.config['transmitter']['symbol_rate']} symbols/s")
        print(f"Modulation: QPSK (Quadrature Phase Shift Keying)")
        print(f"Channel SNR: {self.config['channel']['snr_db']} dB")
        print(f"Network Ports: UDP:{self.config['network']['udp_port']}, TCP:{self.config['network']['tcp_port']}")
        print("=" * 70 + "\n")

        # Start network interface
        self.network.start()

        print("Server is running. Press Ctrl+C to stop.\n")

        # Main loop - print statistics periodically
        try:
            while True:
                time.sleep(30)  # Print stats every 30 seconds
                self.print_statistics()
        except KeyboardInterrupt:
            pass

    def print_statistics(self):
        """Print current statistics"""
        net_stats = self.network.get_statistics()

        print("\n" + "=" * 70)
        print("STATISTICS")
        print("=" * 70)
        print(f"Uptime: {net_stats['uptime_seconds']:.1f} seconds")
        print(f"\nNetwork:")
        print(f"  Packets Received: {net_stats['packets_received']}")
        print(f"  Packets Processed: {net_stats['packets_processed']}")
        print(f"  Packets Dropped: {net_stats['packets_dropped']}")
        print(f"  Bytes Received: {net_stats['bytes_received']}")
        print(f"  Packet Rate: {net_stats['packets_per_second']:.2f} pkt/s")
        print(f"  Queue Size: {net_stats['queue_size']}")

        print(f"\nSimulation:")
        print(f"  Total Simulations: {self.sim_stats['total_simulations']}")
        print(f"  Successful: {self.sim_stats['successful_transmissions']}")
        print(f"  Failed: {self.sim_stats['failed_transmissions']}")

        if self.sim_stats['total_simulations'] > 0:
            success_rate = (self.sim_stats['successful_transmissions'] /
                            self.sim_stats['total_simulations'] * 100)
            print(f"  Success Rate: {success_rate:.1f}%")

        if self.sim_stats['total_bits_transmitted'] > 0:
            overall_ber = (self.sim_stats['total_bit_errors'] /
                           self.sim_stats['total_bits_transmitted'])
            print(f"  Overall BER: {overall_ber:.6f}")
            print(f"  Total Bits: {self.sim_stats['total_bits_transmitted']}")
            print(f"  Total Errors: {self.sim_stats['total_bit_errors']}")

        print("=" * 70 + "\n")

    def shutdown(self, signum, frame):
        """Graceful shutdown"""
        print("\n\nShutting down server...")
        self.network.stop()
        self.print_statistics()
        print("Server stopped.")
        sys.exit(0)


def main():
    """Main entry point"""
    server = SimulationServer()
    server.run()


if __name__ == "__main__":
    main()