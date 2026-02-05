"""
SimURF Sender Application
Transmits packets through MATLAB RF simulator to receiver.
"""
import sys
import time
import socket
import argparse
import logging
from typing import List, Dict, Any

from shared.packet_format import pack
from shared.crypto_utils import encrypt
from shared.fec_utils import fec_encode
from shared.config_utils import SimURFConfig, ConfigurationError
from shared.metrics import PerformanceMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [Sender] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SimURFSender:
    """Wireless packet sender."""
    
    def __init__(
        self,
        simulator_host: str = "host.docker.internal",
        simulator_port: int = 5000,
        src_ip: str = "10.0.0.2",
        dst_ip: str = "10.0.0.1",
        use_fec: bool = True,
        fec_repetition: int = 3
    ):
        """
        Initialize sender.
        
        Args:
            simulator_host: MATLAB simulator hostname
            simulator_port: Simulator port
            src_ip: Source IP for packet headers
            dst_ip: Destination IP for packet headers
            use_fec: Enable forward error correction
            fec_repetition: FEC repetition factor
        """
        self.simulator_host = simulator_host
        self.simulator_port = simulator_port
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.use_fec = use_fec
        self.fec_repetition = fec_repetition
        
        self.seq = 0
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.perf_monitor = PerformanceMonitor(update_interval=5.0)
        
        logger.info("=" * 70)
        logger.info(f"SimURF Sender Initialized")
        logger.info(f"Target: {simulator_host}:{simulator_port}")
        logger.info(f"FEC: {'Enabled' if use_fec else 'Disabled'} "
                   f"(repetition={fec_repetition if use_fec else 'N/A'})")
        logger.info(f"Route: {src_ip} → {dst_ip}")
        logger.info("=" * 70)
    
    def send_message(self, message: str, delay_after: float = 0.0) -> bool:
        """
        Send a single message.
        
        Args:
            message: Text message to send
            delay_after: Delay in seconds after sending
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp_ns = time.time_ns()
            
            logger.info(f"\n{'─' * 70}")
            logger.info(f"Packet #{self.seq}")
            logger.info(f"Message: '{message}' ({len(message)} chars)")
            
            # Step 1: Encrypt
            ciphertext = encrypt(message.encode())
            logger.info(f"→ Encrypted: {len(ciphertext)} bytes")
            
            # Step 2: Optional FEC
            if self.use_fec:
                payload = fec_encode(ciphertext, repeat=self.fec_repetition)
                logger.info(f"→ FEC encoded: {len(payload)} bytes ({self.fec_repetition}x)")
            else:
                payload = ciphertext
                logger.info(f"→ No FEC")
            
            # Step 3: Pack packet
            packet_bytes = pack(
                seq=self.seq,
                src_ip=self.src_ip,
                dst_ip=self.dst_ip,
                timestamp_ns=timestamp_ns,
                payload=payload
            )
            logger.info(f"→ Packed: {len(packet_bytes)} bytes total")
            
            # Step 4: Send to simulator
            self.sock.sendto(packet_bytes, (self.simulator_host, self.simulator_port))
            logger.info(f"✓ Sent to {self.simulator_host}:{self.simulator_port}")
            
            # Update performance metrics
            stats = self.perf_monitor.update(len(packet_bytes))
            if stats:
                logger.info(f"Performance: {stats['pps']:.1f} pps, "
                          f"{stats['kbps']:.1f} kbps")
            
            self.seq += 1
            
            if delay_after > 0:
                time.sleep(delay_after)
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Send failed: {e}")
            return False
    
    def send_batch(self, messages: List[str], delay: float = 0.5):
        """
        Send a batch of messages.
        
        Args:
            messages: List of messages to send
            delay: Delay between messages in seconds
        """
        logger.info(f"\n{'═' * 70}")
        logger.info(f"Starting batch: {len(messages)} messages")
        logger.info(f"{'═' * 70}")
        
        success = 0
        for msg in messages:
            if self.send_message(msg, delay):
                success += 1
        
        logger.info(f"\n{'═' * 70}")
        logger.info(f"Batch complete: {success}/{len(messages)} sent successfully")
        logger.info(f"{'═' * 70}")
    
    def close(self):
        """Clean up resources."""
        self.sock.close()
        logger.info("Sender closed")


def load_scenario(scenario_name: str) -> Dict[str, Any]:
    """Load test scenario configuration."""
    try:
        config_mgr = SimURFConfig()
        return config_mgr.load_test_scenario(scenario_name)
    except ConfigurationError:
        # Return default scenarios
        return get_default_scenarios().get(scenario_name, {})


def get_default_scenarios() -> Dict[str, Dict[str, Any]]:
    """Get built-in test scenarios."""
    return {
        "demo": {
            "messages": [
                "Hello SimURF",
                "Wireless transmission test",
                "BPSK modulation demo",
                "Rayleigh fading channel"
            ],
            "delay": 0.5
        },
        
        "short": {
            "messages": ["A", "B", "C", "D", "E"] * 2,
            "delay": 0.3
        },
        
        "medium": {
            "messages": [
                "This is a medium-length message for testing",
                "Multiple sentences can be sent together",
                "Testing various message lengths"
            ] * 3,
            "delay": 0.5
        },
        
        "long": {
            "messages": [
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 5,
                "Testing longer messages with more content to verify system stability.",
                "Another long message with different content pattern. " * 3
            ] * 2,
            "delay": 1.0
        },
        
        "stress": {
            "messages": ["X" * i for i in range(10, 200, 20)] * 2,
            "delay": 0.1
        }
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SimURF Wireless Sender")
    parser.add_argument(
        "--scenario",
        default="demo",
        help="Test scenario to run (demo, short, medium, long, stress)"
    )
    parser.add_argument(
        "--simulator-host",
        default="host.docker.internal",
        help="Simulator hostname"
    )
    parser.add_argument(
        "--simulator-port",
        type=int,
        default=5000,
        help="Simulator port"
    )
    parser.add_argument(
        "--no-fec",
        action="store_true",
        help="Disable FEC"
    )
    parser.add_argument(
        "--fec-repetition",
        type=int,
        default=3,
        help="FEC repetition factor"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config_mgr = SimURFConfig()
        channel_cfg = config_mgr.load_matlab_channel_config()
        use_fec = channel_cfg.get("use_fec", True) and not args.no_fec
    except ConfigurationError as e:
        logger.warning(f"Could not load config: {e}, using defaults")
        use_fec = not args.no_fec
    
    # Create sender
    sender = SimURFSender(
        simulator_host=args.simulator_host,
        simulator_port=args.simulator_port,
        use_fec=use_fec,
        fec_repetition=args.fec_repetition
    )
    
    try:
        # Load scenario
        scenario = load_scenario(args.scenario)
        if not scenario:
            logger.error(f"Unknown scenario: {args.scenario}")
            logger.info(f"Available scenarios: {', '.join(get_default_scenarios().keys())}")
            return 1
        
        # Send messages
        messages = scenario.get("messages", [])
        delay = scenario.get("delay", 0.5)
        
        sender.send_batch(messages, delay)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    finally:
        sender.close()


if __name__ == "__main__":
    sys.exit(main())