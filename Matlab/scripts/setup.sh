#!/bin/bash
# SimURF Quick Start Script

set -e

echo "========================================="
echo "SimURF Wireless Communication Simulator"
echo "========================================="
echo ""

# Check if MATLAB is available
if ! python -c "import matlab.engine" 2>/dev/null; then
    echo "⚠️  WARNING: MATLAB Python engine not found"
    echo "   Please install it before running the simulator:"
    echo "   cd /path/to/matlab/extern/engines/python"
    echo "   python setup.py install"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Build Docker images
echo "📦 Building Docker images..."
docker-compose build

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the system:"
echo "  1. Start MATLAB simulator:  python simulator/simurf_matlab_bridge.py"
echo "  2. In another terminal:     docker-compose up"
echo ""
echo "To run specific scenarios:"
echo "  docker-compose run sender python sender/sender_app.py --scenario <name>"
echo ""
echo "Available scenarios: demo, short, medium, long, stress, baseline, low_snr, high_doppler"
echo ""
