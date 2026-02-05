"""
SimURF Analyzer Application
Collects and analyzes metrics from RF simulator.
"""
import sys
import socket
import json
import logging
import argparse
from typing import Dict, Any
from collections import deque
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [Analyzer] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SimURFAnalyzer:
    """Real-time metrics analyzer."""
    
    def __init__(
        self,
        listen_ip: str = "0.0.0.0",
        listen_port: int = 7000,
        window_size: int = 100,
        output_file: str = "metrics.json"
    ):
        """
        Initialize analyzer.
        
        Args:
            listen_ip: IP to bind to
            listen_port: Port to listen on
            window_size: Number of metrics to keep in memory
            output_file: JSON file to save metrics
        """
        self.listen_ip = listen_ip
        self.listen_port = listen_port
        self.window_size = window_size
        self.output_file = output_file
        
        # Metrics storage
        self.metrics_history: deque = deque(maxlen=window_size)
        self.packet_count = 0
        self.start_time = time.time()
        
        # Setup socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((listen_ip, listen_port))
        
        logger.info("=" * 70)
        logger.info(f"SimURF Analyzer Started")
        logger.info(f"Listening: {listen_ip}:{listen_port}")
        logger.info(f"Window size: {window_size} packets")
        logger.info(f"Output: {output_file}")
        logger.info("=" * 70)
    
    def process_metrics(self, metrics: Dict[str, Any]):
        """
        Process received metrics.
        
        Args:
            metrics: Metrics dictionary from simulator
        """
        self.packet_count += 1
        self.metrics_history.append(metrics)
        
        logger.info(f"\n{'─' * 70}")
        logger.info(f"Metrics #{self.packet_count}")
        logger.info(f"  SNR: {metrics.get('snr_db', 'N/A')} dB")
        logger.info(f"  Doppler: {metrics.get('doppler', 'N/A')} Hz")
        logger.info(f"  Channel: {metrics.get('channel_model', 'N/A')}")
        
        if 'ber' in metrics:
            logger.info(f"  BER: {metrics['ber']:.6f}")
            logger.info(f"  Bit errors: {metrics.get('bit_errors', 0)}")
        
        if 'byte_errors' in metrics:
            logger.info(f"  Byte errors: {metrics['byte_errors']}")
        
        # Calculate running statistics
        if len(self.metrics_history) >= 10:
            self._print_statistics()
    
    def _print_statistics(self):
        """Print running statistics."""
        bers = [m.get('ber', 0) for m in self.metrics_history if 'ber' in m]
        
        if bers:
            avg_ber = sum(bers) / len(bers)
            max_ber = max(bers)
            min_ber = min(bers)
            
            logger.info(f"\n  Running stats (last {len(self.metrics_history)} packets):")
            logger.info(f"    BER: avg={avg_ber:.6f}, min={min_ber:.6f}, max={max_ber:.6f}")
            
            # Calculate packet error rate
            errors = [m for m in self.metrics_history if m.get('byte_errors', 0) > 0]
            per = len(errors) / len(self.metrics_history)
            logger.info(f"    PER: {per:.4f} ({len(errors)}/{len(self.metrics_history)})")
    
    def run(self):
        """Main receive loop."""
        buffer_size = 65535
        
        try:
            while True:
                data, addr = self.sock.recvfrom(buffer_size)
                
                try:
                    metrics = json.loads(data.decode())
                    self.process_metrics(metrics)
                except json.JSONDecodeError as e:
                    logger.error(f"✗ Invalid JSON: {e}")
                except Exception as e:
                    logger.error(f"✗ Processing error: {e}")
                    
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            self._save_metrics()
            self._print_summary()
        except Exception as e:
            logger.error(f"✗ Fatal error: {e}", exc_info=True)
            raise
        finally:
            self.close()
    
    def _save_metrics(self):
        """Save metrics to file."""
        try:
            with open(self.output_file, 'w') as f:
                json.dump({
                    'packet_count': self.packet_count,
                    'runtime_s': time.time() - self.start_time,
                    'metrics': list(self.metrics_history)
                }, f, indent=2)
            logger.info(f"Metrics saved to: {self.output_file}")
        except Exception as e:
            logger.error(f"✗ Could not save metrics: {e}")
    
    def _print_summary(self):
        """Print final summary."""
        runtime = time.time() - self.start_time
        
        logger.info("=" * 70)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total packets:  {self.packet_count}")
        logger.info(f"Runtime:        {runtime:.2f} s")
        logger.info(f"Throughput:     {self.packet_count / runtime:.2f} pps")
        
        if self.metrics_history:
            # Calculate overall statistics
            bers = [m.get('ber', 0) for m in self.metrics_history if 'ber' in m]
            
            if bers:
                logger.info(f"\nOverall BER statistics:")
                logger.info(f"  Average: {sum(bers) / len(bers):.6f}")
                logger.info(f"  Minimum: {min(bers):.6f}")
                logger.info(f"  Maximum: {max(bers):.6f}")
            
            # Packet error rate
            errors = [m for m in self.metrics_history if m.get('byte_errors', 0) > 0]
            per = len(errors) / len(self.metrics_history)
            logger.info(f"\nPacket Error Rate: {per:.4f}")
            logger.info(f"  Packets with errors: {len(errors)}/{len(self.metrics_history)}")
        
        logger.info("=" * 70)
    
    def close(self):
        """Clean up resources."""
        self.sock.close()
        logger.info("Analyzer closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SimURF Metrics Analyzer")
    parser.add_argument(
        "--listen-ip",
        default="0.0.0.0",
        help="IP address to bind to"
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=7000,
        help="Port to listen on"
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=100,
        help="Number of metrics to keep in memory"
    )
    parser.add_argument(
        "--output",
        default="metrics.json",
        help="Output JSON file"
    )
    
    args = parser.parse_args()
    
    # Create and run analyzer
    analyzer = SimURFAnalyzer(
        listen_ip=args.listen_ip,
        listen_port=args.listen_port,
        window_size=args.window_size,
        output_file=args.output
    )
    
    try:
        analyzer.run()
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())