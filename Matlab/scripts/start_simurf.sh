
# Create directories
mkdir -p /simurf/input /simurf/output /simurf/logs

# Set up dummy network interfaces for testing
echo "Setting up network interfaces..."
ip link add name simurf-in type dummy 2>/dev/null || true
ip link add name simurf-out type dummy 2>/dev/null || true
ip link set simurf-in up 2>/dev/null || true
ip link set simurf-out up 2>/dev/null || true

# Start Python RF emulator and network manager
echo "Starting SimuRF Wireless Transmission Emulator..."
cd /simurf/python_components

# Start the main application
python3 network_manager.py

echo "SimuRF container is running..."