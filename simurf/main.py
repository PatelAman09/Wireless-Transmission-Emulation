"""
Wireless Channel Emulator - Main Entry Point
Simulates wireless transmission of IP packets through various channel models
"""

import argparse
import socket
import threading
import time
import logging
from typing import Optional

from transmitter import WirelessTransmitter
from channel import ChannelModel
from receiver import WirelessReceiver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WirelessChannelEmulator:
    def __init__(self,
                 input_port: int = 12345,
                 output_port: int = 12346,
                 channel_type: str = 'awgn',
                 snr_db: float = 10.0,
                 modulation: str = 'qpsk'):
        """
        Initialize the wireless channel emulator

        Args:
            input_port: Port to receive input IP packets
            output_port: Port to send output IP packets
            channel_type: Type of channel model ('awgn', 'rayleigh', 'rician')
            snr_db: Signal-to-noise ratio in dB
            modulation: Modulation scheme ('qpsk', 'bpsk', '16qam')
        """
        self.input_port = input_port
        self.output_port = output_port

        # Initialize signal processing blocks
        self.transmitter = WirelessTransmitter(modulation=modulation)
        self.channel = ChannelModel(channel_type=channel_type, snr_db=snr_db)
        self.receiver = WirelessReceiver(modulation=modulation)

        # Socket setup
        self.input_socket = None
        self.output_socket = None
        self.running = False

        logger.info(f"Initialized emulator: {channel_type} channel, {snr_db} dB SNR, {modulation} modulation")

    def setup_sockets(self):
        """Setup UDP sockets for packet I/O"""
        try:
            # Input socket (receive packets to transmit)
            self.input_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.input_socket.bind(('0.0.0.0', self.input_port))
            self.input_socket.settimeout(1.0)  # Non-blocking with timeout

            # Output socket (send received packets)
            self.output_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            logger.info(f"Sockets setup: Input port {self.input_port}, Output port {self.output_port}")

        except Exception as e:
            logger.error(f"Failed to setup sockets: {e}")
            raise

    def process_packet(self, packet_data: bytes, source_addr: tuple) -> Optional[bytes]:
        """
        Process a single packet through the wireless channel

        Args:
            packet_data: Raw packet bytes
            source_addr: Source address tuple (ip, port)

        Returns:
            Processed packet bytes or None if packet is lost
        """
        try:
            # Step 1: Transmitter - Convert packet to complex baseband signal
            logger.debug(f"Processing packet of {len(packet_data)} bytes from {source_addr}")
            tx_signal = self.transmitter.transmit(packet_data)

            # Step 2: Channel - Apply channel effects
            rx_signal = self.channel.apply_channel(tx_signal)

            # Step 3: Receiver - Recover packet from received signal
            recovered_packet = self.receiver.receive(rx_signal)

            if recovered_packet is not None:
                logger.debug(f"Successfully recovered packet of {len(recovered_packet)} bytes")
                return recovered_packet
            else:
                logger.warning("Packet lost during transmission")
                return None

        except Exception as e:
            logger.error(f"Error processing packet: {e}")
            return None

    def packet_handler(self):
        """Main packet processing loop"""
        logger.info("Starting packet handler...")

        while self.running:
            try:
                # Receive packet
                data, addr = self.input_socket.recvfrom(4096)

                # Process through wireless channel
                processed_data = self.process_packet(data, addr)

                # Send processed packet if recovered
                if processed_data is not None:
                    # Send back to source (in real scenario, this would be the destination)
                    self.output_socket.sendto(processed_data, (addr[0], self.output_port))
                    logger.debug(f"Sent processed packet to {addr[0]}:{self.output_port}")

            except socket.timeout:
                # Continue loop on timeout
                continue
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    logger.error(f"Error in packet handler: {e}")

    def start(self):
        """Start the emulator"""
        logger.info("Starting Wireless Channel Emulator...")

        self.setup_sockets()
        self.running = True

        # Start packet handling in a separate thread
        handler_thread = threading.Thread(target=self.packet_handler, daemon=True)
        handler_thread.start()

        logger.info(f"Emulator running. Send packets to port {self.input_port}")
        logger.info(f"Processed packets will be sent to port {self.output_port}")

        try:
            # Keep main thread alive
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()

    def stop(self):
        """Stop the emulator"""
        logger.info("Stopping Wireless Channel Emulator...")
        self.running = False

        if self.input_socket:
            self.input_socket.close()
        if self.output_socket:
            self.output_socket.close()

        logger.info("Emulator stopped")

    def get_stats(self):
        """Get emulator statistics"""
        return {
            'transmitter_stats': self.transmitter.get_stats(),
            'channel_stats': self.channel.get_stats(),
            'receiver_stats': self.receiver.get_stats()
        }


def main():
    parser = argparse.ArgumentParser(description='Wireless Channel Emulator')
    parser.add_argument('--input-port', type=int, default=12345,
                        help='Input port for receiving packets (default: 12345)')
    parser.add_argument('--output-port', type=int, default=12346,
                        help='Output port for sending processed packets (default: 12346)')
    parser.add_argument('--channel', choices=['awgn', 'rayleigh', 'rician'],
                        default='awgn', help='Channel model (default: awgn)')
    parser.add_argument('--snr', type=float, default=10.0,
                        help='Signal-to-noise ratio in dB (default: 10.0)')
    parser.add_argument('--modulation', choices=['bpsk', 'qpsk', '16qam'],
                        default='qpsk', help='Modulation scheme (default: qpsk)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create and start emulator
    emulator = WirelessChannelEmulator(
        input_port=args.input_port,
        output_port=args.output_port,
        channel_type=args.channel,
        snr_db=args.snr,
        modulation=args.modulation
    )

    try:
        emulator.start()
    except Exception as e:
        logger.error(f"Failed to start emulator: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
