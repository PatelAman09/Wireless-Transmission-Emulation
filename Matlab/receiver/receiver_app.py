"""
SimURF Receiver Application
Receives packets from MATLAB RF simulator and processes them.
"""
import sys
import socket
import time
import logging
import argparse
from typing import Optional

from shared.packet_format import unpack
from shared.crypto_utils import decrypt
from shared.fec_utils import fec_decode_with_stats
from shared.config_utils import SimURFConfig, ConfigurationError
from shared.metrics import MetricsCollector, PacketMetrics, PerformanceMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [Receiver] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SimURFReceiver:
    """Wireless packet receiver."""
    
    def __init__(
        self,
        listen_ip: str = "0.0.0.0",
        listen_port: int = 5000,
        use_fec: bool = True,
        fec_repetition: int = 3,
        metrics_file: Optional[str] = None
    ):
        """
        Initialize receiver.
        
        Args:
            listen_ip: IP to bind to
            listen_port: Port to listen on
            use_fec: Expect FEC-encoded packets
            fec_repetition: FEC repetition factor
            metrics_file: Optional file to save metrics CSV
        """
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.use_fec = use_fec
        self.fec_repetition = fec_repetition
        self.metrics_file = metrics_file
        
        # Statistics
        self.packet_count = 0
        self.success_count = 0
        self.crc_errors = 0
        self.decode_errors = 0
        
        # Metrics tracking
        self.metrics_collector = MetricsCollector(window_size=1000)
        self.perf_monitor = PerformanceMonitor(update_interval=5.0)
        
        # Setup socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.sock.bind((listen_ip, listen_port))
            logger.info("=" * 70)
            logger.info(f"SimURF Receiver Started")
            logger.info(f"Listening: {listen_ip}:{listen_port}")
            logger.info(f"FEC: {'Enabled' if use_fec else 'Disabled'} "
                       f"(repetition={fec_repetition if use_fec else 'N/A'})")
            if metrics_file:
                logger.info(f"Metrics output: {metrics_file}")
            logger.info("Waiting for packets...")
            logger.info("=" * 70)
        except Exception as e:
            logger.error(f"✗ Could not bind socket: {e}")
            raise
    
    def process_packet(self, data: bytes, addr: tuple) -> bool:
        """
        Process received packet.
        
        Args:
            data: Raw packet bytes
            addr: Source address tuple
            
        Returns:
            True if successfully decoded, False otherwise
        """
        self.packet_count += 1
        receive_time = time.time_ns()
        
        logger.info(f"\n{'─' * 70}")
        logger.info(f"Packet #{self.packet_count} from {addr}")
        logger.info(f"Raw size: {len(data)} bytes")
        
        try:
            # Step 1: Unpack and validate CRC
            pkt = unpack(data)
            logger.info(f"✓ CRC valid, SEQ={pkt['seq']}")
            logger.info(f"  Route: {pkt['src_ip']} → {pkt['dst_ip']}")
            logger.info(f"  Payload: {len(pkt['payload'])} bytes")
            
            payload = pkt["payload"]
            fec_corrections = 0
            
            # Step 2: Optional FEC decoding
            if self.use_fec:
                logger.info(f"→ Decoding FEC...")
                payload, fec_corrections = fec_decode_with_stats(
                    payload, 
                    repeat=self.fec_repetition
                )
                logger.info(f"✓ FEC decoded: {len(payload)} bytes "
                          f"({fec_corrections} corrections)")
            
            # Step 3: Decrypt
            logger.info(f"→ Decrypting...")
            plaintext = decrypt(payload)
            logger.info(f"✓ Decrypted: {len(plaintext)} bytes")
            
            # Step 4: Decode message
            message = plaintext.decode(errors='replace')
            logger.info(f"✓ MESSAGE: '{message}'")
            
            # Calculate latency
            latency_ns = receive_time - pkt['timestamp_ns']
            latency_ms = latency_ns / 1_000_000
            
            # Record metrics
            metrics = PacketMetrics(
                seq=pkt['seq'],
                timestamp_ns=pkt['timestamp_ns'],
                size_bytes=len(data),
                latency_ms=latency_ms,
                fec_corrections=fec_corrections if self.use_fec else None
            )
            self.metrics_collector.add_packet(metrics)
            
            # Performance monitoring
            stats = self.perf_monitor.update(len(data))
            if stats:
                logger.info(f"Performance: {stats['pps']:.1f} pps, "
                          f"{stats['kbps']:.1f} kbps")
            
            self.success_count += 1
            logger.info(f"Stats: {self.success_count} OK | "
                       f"{self.crc_errors} CRC | {self.decode_errors} Decode")
            
            return True
            
        except ValueError as e:
            # CRC or packet corruption
            self.crc_errors += 1
            logger.error(f"✗ CORRUPTED (CRC/format): {e}")
            return False
            
        except Exception as e:
            # Decoding or other errors
            self.decode_errors += 1
            logger.error(f"✗ DECODE ERROR: {e}")
            return False
    
    def run(self):
        """Main receive loop."""
        buffer_size = 65535
        
        try:
            while True:
                data, addr = self.sock.recvfrom(buffer_size)
                self.process_packet(data, addr)
                
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 70)
            logger.info("Shutting down...")
            self._print_summary()
            
        except Exception as e:
            logger.error(f"✗ Fatal error: {e}", exc_info=True)
            raise
        finally:
            self.close()
    
    def _print_summary(self):
        """Print final statistics."""
        logger.info("=" * 70)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 70)
        logger.info(f"Total packets:    {self.packet_count}")
        logger.info(f"Successful:       {self.success_count}")
        logger.info(f"CRC errors:       {self.crc_errors}")
        logger.info(f"Decode errors:    {self.decode_errors}")
        
        if self.packet_count > 0:
            success_rate = (self.success_count / self.packet_count) * 100
            logger.info(f"Success rate:     {success_rate:.2f}%")
        
        # Throughput
        throughput = self.metrics_collector.get_throughput()
        logger.info(f"Throughput:       {throughput:.2f} pps")
        
        # Summary metrics
        summary = self.metrics_collector.get_summary()
        if 'latency_ms' in summary:
            lat = summary['latency_ms']
            logger.info(f"Latency (mean):   {lat['mean']:.2f} ms")
            logger.info(f"Latency (median): {lat['median']:.2f} ms")
        
        logger.info("=" * 70)
        
        # Export metrics
        if self.metrics_file:
            self.metrics_collector.export_csv(self.metrics_file)
            logger.info(f"Metrics saved to: {self.metrics_file}")
    
    def close(self):
        """Clean up resources."""
        self.sock.close()
        logger.info("Receiver closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SimURF Wireless Receiver")
    parser.add_argument(
        "--listen-ip",
        default="0.0.0.0",
        help="IP address to bind to"
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=5000,
        help="Port to listen on"
    )
    parser.add_argument(
        "--no-fec",
        action="store_true",
        help="Disable FEC decoding"
    )
    parser.add_argument(
        "--fec-repetition",
        type=int,
        default=3,
        help="FEC repetition factor"
    )
    parser.add_argument(
        "--metrics-file",
        help="Output CSV file for metrics"
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
    
    # Create and run receiver
    receiver = SimURFReceiver(
        listen_ip=args.listen_ip,
        listen_port=args.listen_port,
        use_fec=use_fec,
        fec_repetition=args.fec_repetition,
        metrics_file=args.metrics_file
    )
    
    try:
        receiver.run()
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())