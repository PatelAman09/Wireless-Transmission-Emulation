import json
import time
import numpy as np
from flask import Flask, render_template, jsonify
from collections import deque
import threading
import os

app = Flask(__name__)

class MetricsAnalyzer:
    def __init__(self, log_dir='/logs'):
        self.log_dir = log_dir
        self.sender_metrics = deque(maxlen=1000)
        self.receiver_metrics = deque(maxlen=1000)
        self.simulator_metrics = deque(maxlen=1000)
        
        self.running = True
        self.update_thread = threading.Thread(target=self.update_metrics)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def read_log_file(self, filename):
        """Read and parse JSON log file"""
        filepath = os.path.join(self.log_dir, filename)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
                return [json.loads(line.strip()) for line in lines if line.strip()]
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            return []
    
    def update_metrics(self):
        """Continuously update metrics from log files"""
        while self.running:
            try:
                # Read simulator metrics
                sim_data = self.read_log_file('simulator_metrics.log')
                if sim_data:
                    self.simulator_metrics.extend(sim_data[-100:])
                
                # Read receiver metrics
                recv_data = self.read_log_file('receiver_metrics.log')
                if recv_data:
                    self.receiver_metrics.extend(recv_data[-100:])
                
                time.sleep(2)  # Update every 2 seconds
            except Exception as e:
                print(f"Error updating metrics: {e}")
    
    def get_latest_metrics(self):
        """Get latest aggregated metrics"""
        if not self.simulator_metrics or not self.receiver_metrics:
            return None
        
        # Latest simulator metrics
        latest_sim = list(self.simulator_metrics)[-10:]
        avg_ber = np.mean([m['ber'] for m in latest_sim]) if latest_sim else 0
        avg_snr = np.mean([m['snr_db'] for m in latest_sim]) if latest_sim else 0
        avg_evm = np.mean([m['evm'] for m in latest_sim]) if latest_sim else 0
        
        # Latest receiver metrics
        latest_recv = list(self.receiver_metrics)[-1] if self.receiver_metrics else {}
        
        return {
            'timestamp': time.time(),
            'channel_metrics': {
                'avg_ber': float(avg_ber),
                'avg_snr_db': float(avg_snr),
                'avg_evm': float(avg_evm)
            },
            'receiver_metrics': {
                'throughput_mbps': latest_recv.get('throughput_mbps', 0),
                'packet_loss_rate': latest_recv.get('packet_loss_rate', 0),
                'avg_latency_ms': latest_recv.get('avg_latency_ms', 0),
                'total_packets': latest_recv.get('total_packets', 0)
            }
        }
    
    def get_time_series(self, metric_name, source='simulator', window=100):
        """Get time series data for plotting"""
        if source == 'simulator':
            data = list(self.simulator_metrics)[-window:]
        elif source == 'receiver':
            data = list(self.receiver_metrics)[-window:]
        else:
            return []
        
        if not data:
            return []
        
        return [
            {
                'timestamp': d.get('timestamp', 0),
                'value': d.get(metric_name, 0)
            }
            for d in data
        ]
    
    def calculate_statistics(self):
        """Calculate comprehensive statistics"""
        sim_data = list(self.simulator_metrics)
        recv_data = list(self.receiver_metrics)
        
        if not sim_data or not recv_data:
            return {}
        
        # BER statistics
        ber_values = [m['ber'] for m in sim_data]
        
        # SNR statistics
        snr_values = [m['snr_db'] for m in sim_data]
        
        # EVM statistics
        evm_values = [m['evm'] for m in sim_data]
        
        # Latest receiver stats
        latest_recv = recv_data[-1] if recv_data else {}
        
        return {
            'ber': {
                'mean': float(np.mean(ber_values)),
                'min': float(np.min(ber_values)),
                'max': float(np.max(ber_values)),
                'std': float(np.std(ber_values))
            },
            'snr': {
                'mean': float(np.mean(snr_values)),
                'min': float(np.min(snr_values)),
                'max': float(np.max(snr_values)),
                'std': float(np.std(snr_values))
            },
            'evm': {
                'mean': float(np.mean(evm_values)),
                'min': float(np.min(evm_values)),
                'max': float(np.max(evm_values)),
                'std': float(np.std(evm_values))
            },
            'throughput': {
                'current': latest_recv.get('throughput_mbps', 0),
                'total_packets': latest_recv.get('total_packets', 0),
                'packet_loss_rate': latest_recv.get('packet_loss_rate', 0)
            }
        }


# Global analyzer instance
analyzer = MetricsAnalyzer()


@app.route('/')
def index():
    """Main dashboard page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SimuRF - Wireless Channel Simulator</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background: #f5f5f5;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .metric-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            .metric-card h3 {
                margin: 0 0 10px 0;
                font-size: 14px;
                opacity: 0.9;
            }
            .metric-card .value {
                font-size: 28px;
                font-weight: bold;
            }
            .metric-card .unit {
                font-size: 14px;
                opacity: 0.8;
            }
            .chart-container {
                margin: 20px 0;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
            }
            .status {
                display: inline-block;
                padding: 5px 10px;
                border-radius: 4px;
                background: #4CAF50;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ SimuRF - Wireless Channel Simulator Dashboard</h1>
            <p><span class="status" id="status">● LIVE</span> Real-time monitoring</p>
            
            <div class="metrics-grid" id="metrics"></div>
            
            <div class="chart-container">
                <h2>Bit Error Rate (BER)</h2>
                <div id="ber-chart"></div>
            </div>
            
            <div class="chart-container">
                <h2>Signal-to-Noise Ratio (SNR)</h2>
                <div id="snr-chart"></div>
            </div>
            
            <div class="chart-container">
                <h2>Throughput</h2>
                <div id="throughput-chart"></div>
            </div>
        </div>
        
        <script>
            function updateDashboard() {
                fetch('/api/metrics')
                    .then(response => response.json())
                    .then(data => {
                        updateMetricCards(data);
                    });
                
                updateCharts();
            }
            
            function updateMetricCards(data) {
                if (!data) return;
                
                const metrics = document.getElementById('metrics');
                metrics.innerHTML = `
                    <div class="metric-card">
                        <h3>Average BER</h3>
                        <div class="value">${data.channel_metrics.avg_ber.toExponential(2)}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Average SNR</h3>
                        <div class="value">${data.channel_metrics.avg_snr_db.toFixed(2)}</div>
                        <div class="unit">dB</div>
                    </div>
                    <div class="metric-card">
                        <h3>Average EVM</h3>
                        <div class="value">${(data.channel_metrics.avg_evm * 100).toFixed(2)}</div>
                        <div class="unit">%</div>
                    </div>
                    <div class="metric-card">
                        <h3>Throughput</h3>
                        <div class="value">${data.receiver_metrics.throughput_mbps.toFixed(2)}</div>
                        <div class="unit">Mbps</div>
                    </div>
                    <div class="metric-card">
                        <h3>Packet Loss</h3>
                        <div class="value">${(data.receiver_metrics.packet_loss_rate * 100).toFixed(2)}</div>
                        <div class="unit">%</div>
                    </div>
                    <div class="metric-card">
                        <h3>Latency</h3>
                        <div class="value">${data.receiver_metrics.avg_latency_ms.toFixed(2)}</div>
                        <div class="unit">ms</div>
                    </div>
                `;
            }
            
            function updateCharts() {
                // BER Chart
                fetch('/api/timeseries/ber')
                    .then(response => response.json())
                    .then(data => {
                        const trace = {
                            x: data.map(d => new Date(d.timestamp * 1000)),
                            y: data.map(d => d.value),
                            type: 'scatter',
                            mode: 'lines',
                            line: {color: '#FF6B6B'}
                        };
                        
                        Plotly.newPlot('ber-chart', [trace], {
                            yaxis: {type: 'log'},
                            margin: {t: 10}
                        });
                    });
                
                // SNR Chart
                fetch('/api/timeseries/snr_db')
                    .then(response => response.json())
                    .then(data => {
                        const trace = {
                            x: data.map(d => new Date(d.timestamp * 1000)),
                            y: data.map(d => d.value),
                            type: 'scatter',
                            mode: 'lines',
                            line: {color: '#4ECDC4'}
                        };
                        
                        Plotly.newPlot('snr-chart', [trace], {
                            yaxis: {title: 'SNR (dB)'},
                            margin: {t: 10}
                        });
                    });
                
                // Throughput Chart
                fetch('/api/timeseries/throughput')
                    .then(response => response.json())
                    .then(data => {
                        const trace = {
                            x: data.map(d => new Date(d.timestamp * 1000)),
                            y: data.map(d => d.value),
                            type: 'scatter',
                            mode: 'lines',
                            fill: 'tozeroy',
                            line: {color: '#95E1D3'}
                        };
                        
                        Plotly.newPlot('throughput-chart', [trace], {
                            yaxis: {title: 'Throughput (Mbps)'},
                            margin: {t: 10}
                        });
                    });
            }
            
            // Update every 2 seconds
            setInterval(updateDashboard, 2000);
            updateDashboard();
        </script>
    </body>
    </html>
    """


@app.route('/api/metrics')
def get_metrics():
    """Get latest metrics"""
    metrics = analyzer.get_latest_metrics()
    return jsonify(metrics)


@app.route('/api/timeseries/<metric>')
def get_timeseries(metric):
    """Get time series data"""
    if metric == 'throughput':
        data = analyzer.get_time_series('throughput_mbps', 'receiver', 100)
    else:
        data = analyzer.get_time_series(metric, 'simulator', 100)
    
    return jsonify(data)


@app.route('/api/statistics')
def get_statistics():
    """Get comprehensive statistics"""
    stats = analyzer.calculate_statistics()
    return jsonify(stats)


if __name__ == '__main__':
    print("[ANALYZER] Starting dashboard on http://0.0.0.0:8080")
    app.run(host='0.0.0.0', port=8080, debug=False)