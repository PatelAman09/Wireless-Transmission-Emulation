"""
Metrics collection and analysis for SimURF.
"""
import time
import json
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
from collections import deque
import statistics


@dataclass
class PacketMetrics:
    """Metrics for a single packet."""
    seq: int
    timestamp_ns: int
    size_bytes: int
    snr_db: Optional[float] = None
    ber: Optional[float] = None
    bit_errors: Optional[int] = None
    latency_ms: Optional[float] = None
    fec_corrections: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MetricsCollector:
    """Collects and aggregates packet metrics."""
    
    def __init__(self, window_size: int = 100):
        """
        Initialize metrics collector.
        
        Args:
            window_size: Number of packets to keep in rolling window
        """
        self.window_size = window_size
        self.packets: deque = deque(maxlen=window_size)
        self.total_packets = 0
        self.total_errors = 0
        self.start_time = time.time()
    
    def add_packet(self, metrics: PacketMetrics):
        """
        Add packet metrics.
        
        Args:
            metrics: Packet metrics to add
        """
        self.packets.append(metrics)
        self.total_packets += 1
        
        if metrics.bit_errors and metrics.bit_errors > 0:
            self.total_errors += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics.
        
        Returns:
            Dictionary with aggregate metrics
        """
        if not self.packets:
            return {
                "total_packets": 0,
                "window_packets": 0,
                "error_rate": 0.0,
                "runtime_s": time.time() - self.start_time
            }
        
        # Extract values
        bers = [p.ber for p in self.packets if p.ber is not None]
        latencies = [p.latency_ms for p in self.packets if p.latency_ms is not None]
        snrs = [p.snr_db for p in self.packets if p.snr_db is not None]
        
        summary = {
            "total_packets": self.total_packets,
            "window_packets": len(self.packets),
            "error_rate": self.total_errors / self.total_packets if self.total_packets > 0 else 0.0,
            "runtime_s": time.time() - self.start_time,
        }
        
        # BER statistics
        if bers:
            summary["ber"] = {
                "mean": statistics.mean(bers),
                "median": statistics.median(bers),
                "min": min(bers),
                "max": max(bers),
            }
        
        # Latency statistics
        if latencies:
            summary["latency_ms"] = {
                "mean": statistics.mean(latencies),
                "median": statistics.median(latencies),
                "min": min(latencies),
                "max": max(latencies),
                "stdev": statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
            }
        
        # SNR statistics
        if snrs:
            summary["snr_db"] = {
                "mean": statistics.mean(snrs),
                "median": statistics.median(snrs),
                "min": min(snrs),
                "max": max(snrs),
            }
        
        return summary
    
    def get_throughput(self) -> float:
        """
        Calculate throughput in packets per second.
        
        Returns:
            Packets per second
        """
        runtime = time.time() - self.start_time
        return self.total_packets / runtime if runtime > 0 else 0.0
    
    def export_csv(self, filename: str):
        """
        Export metrics to CSV file.
        
        Args:
            filename: Output CSV filename
        """
        import csv
        
        if not self.packets:
            return
        
        # Get all field names from first packet
        fieldnames = list(self.packets[0].to_dict().keys())
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for pkt in self.packets:
                writer.writerow(pkt.to_dict())
    
    def export_json(self, filename: str):
        """
        Export summary to JSON file.
        
        Args:
            filename: Output JSON filename
        """
        summary = self.get_summary()
        
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def reset(self):
        """Reset all metrics."""
        self.packets.clear()
        self.total_packets = 0
        self.total_errors = 0
        self.start_time = time.time()


class PerformanceMonitor:
    """Monitor real-time performance metrics."""
    
    def __init__(self, update_interval: float = 1.0):
        """
        Initialize performance monitor.
        
        Args:
            update_interval: Seconds between updates
        """
        self.update_interval = update_interval
        self.last_update = time.time()
        self.packet_count = 0
        self.byte_count = 0
    
    def update(self, packet_size: int) -> Optional[Dict[str, float]]:
        """
        Update counters and return stats if interval elapsed.
        
        Args:
            packet_size: Size of packet in bytes
            
        Returns:
            Performance stats dict if update interval elapsed, else None
        """
        self.packet_count += 1
        self.byte_count += packet_size
        
        now = time.time()
        elapsed = now - self.last_update
        
        if elapsed >= self.update_interval:
            stats = {
                "pps": self.packet_count / elapsed,  # packets per second
                "bps": (self.byte_count * 8) / elapsed,  # bits per second
                "kbps": (self.byte_count * 8) / (elapsed * 1000),
                "mbps": (self.byte_count * 8) / (elapsed * 1_000_000),
            }
            
            # Reset counters
            self.packet_count = 0
            self.byte_count = 0
            self.last_update = now
            
            return stats
        
        return None