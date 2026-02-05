#!/usr/bin/env python3
"""
SimURF Metrics Visualization
Generate plots from collected metrics data.
"""
import json
import argparse
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def load_metrics(filename):
    """Load metrics from JSON file."""
    with open(filename) as f:
        return json.load(f)


def plot_ber(metrics_list, output_dir):
    """Plot Bit Error Rate over time."""
    bers = []
    packet_nums = []
    
    for i, m in enumerate(metrics_list):
        if 'ber' in m:
            bers.append(m['ber'])
            packet_nums.append(i)
    
    if not bers:
        print("No BER data available")
        return
    
    plt.figure(figsize=(12, 6))
    plt.semilogy(packet_nums, bers, marker='o', linestyle='-', alpha=0.7)
    plt.xlabel('Packet Number', fontsize=12)
    plt.ylabel('Bit Error Rate (BER)', fontsize=12)
    plt.title('Bit Error Rate Over Time', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_file = Path(output_dir) / 'ber_plot.png'
    plt.savefig(output_file, dpi=300)
    print(f"Saved BER plot to {output_file}")
    plt.close()


def plot_snr(metrics_list, output_dir):
    """Plot SNR over time."""
    snrs = []
    packet_nums = []
    
    for i, m in enumerate(metrics_list):
        if 'snr_db' in m:
            snrs.append(m['snr_db'])
            packet_nums.append(i)
    
    if not snrs:
        print("No SNR data available")
        return
    
    plt.figure(figsize=(12, 6))
    plt.plot(packet_nums, snrs, marker='o', linestyle='-', alpha=0.7, color='green')
    plt.xlabel('Packet Number', fontsize=12)
    plt.ylabel('SNR (dB)', fontsize=12)
    plt.title('Signal-to-Noise Ratio Over Time', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_file = Path(output_dir) / 'snr_plot.png'
    plt.savefig(output_file, dpi=300)
    print(f"Saved SNR plot to {output_file}")
    plt.close()


def plot_error_distribution(metrics_list, output_dir):
    """Plot distribution of bit errors."""
    bit_errors = []
    
    for m in metrics_list:
        if 'bit_errors' in m:
            bit_errors.append(m['bit_errors'])
    
    if not bit_errors:
        print("No bit error data available")
        return
    
    plt.figure(figsize=(10, 6))
    plt.hist(bit_errors, bins=30, edgecolor='black', alpha=0.7)
    plt.xlabel('Bit Errors per Packet', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.title('Distribution of Bit Errors', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    
    output_file = Path(output_dir) / 'error_distribution.png'
    plt.savefig(output_file, dpi=300)
    print(f"Saved error distribution to {output_file}")
    plt.close()


def plot_summary_stats(data, output_dir):
    """Plot summary statistics."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    metrics_list = data.get('metrics', [])
    
    # Extract data
    bers = [m.get('ber', 0) for m in metrics_list if 'ber' in m]
    snrs = [m.get('snr_db', 0) for m in metrics_list if 'snr_db' in m]
    bit_errors = [m.get('bit_errors', 0) for m in metrics_list if 'bit_errors' in m]
    
    # BER over time
    if bers:
        axes[0, 0].semilogy(range(len(bers)), bers, 'b-', alpha=0.7)
        axes[0, 0].set_xlabel('Packet Number')
        axes[0, 0].set_ylabel('BER')
        axes[0, 0].set_title('BER Over Time')
        axes[0, 0].grid(True, alpha=0.3)
    
    # SNR over time
    if snrs:
        axes[0, 1].plot(range(len(snrs)), snrs, 'g-', alpha=0.7)
        axes[0, 1].set_xlabel('Packet Number')
        axes[0, 1].set_ylabel('SNR (dB)')
        axes[0, 1].set_title('SNR Over Time')
        axes[0, 1].grid(True, alpha=0.3)
    
    # BER histogram
    if bers:
        axes[1, 0].hist(bers, bins=20, edgecolor='black', alpha=0.7)
        axes[1, 0].set_xlabel('BER')
        axes[1, 0].set_ylabel('Frequency')
        axes[1, 0].set_title('BER Distribution')
        axes[1, 0].grid(True, alpha=0.3, axis='y')
    
    # Statistics text
    mean_ber = np.mean(bers) if bers else 0
    median_ber = np.median(bers) if bers else 0
    max_ber = max(bers) if bers else 0
    total_bit_errors = sum(bit_errors) if bit_errors else 0
    pkts_with_errors = sum(1 for e in bit_errors if e > 0) if bit_errors else 0
    
    stats_text = f"""
    Total Packets: {data.get('packet_count', 0)}
    Runtime: {data.get('runtime_s', 0):.2f} s
    
    BER Statistics:
    - Mean: {mean_ber:.6f}
    - Median: {median_ber:.6f}
    - Max: {max_ber:.6f}
    
    Error Statistics:
    - Total bit errors: {total_bit_errors}
    - Packets with errors: {pkts_with_errors}
    """
    
    axes[1, 1].text(0.1, 0.5, stats_text, fontsize=10, family='monospace',
                   verticalalignment='center', transform=axes[1, 1].transAxes)
    axes[1, 1].axis('off')
    
    plt.tight_layout()
    
    output_file = Path(output_dir) / 'summary_dashboard.png'
    plt.savefig(output_file, dpi=300)
    print(f"Saved summary dashboard to {output_file}")
    plt.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Visualize SimURF metrics data"
    )
    parser.add_argument(
        'metrics_file',
        help='Path to metrics JSON file'
    )
    parser.add_argument(
        '--output-dir',
        default='./plots',
        help='Output directory for plots'
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load metrics
    print(f"Loading metrics from {args.metrics_file}...")
    data = load_metrics(args.metrics_file)
    
    metrics_list = data.get('metrics', [])
    print(f"Found {len(metrics_list)} packet metrics")
    
    # Generate plots
    print("\nGenerating plots...")
    plot_ber(metrics_list, output_dir)
    plot_snr(metrics_list, output_dir)
    plot_error_distribution(metrics_list, output_dir)
    plot_summary_stats(data, output_dir)
    
    print(f"\n✅ All plots saved to {output_dir}")


if __name__ == '__main__':
    main()