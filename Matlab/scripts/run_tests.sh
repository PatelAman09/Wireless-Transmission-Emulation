#!/bin/bash
# Run all SimURF tests

set -e

echo "======================================"
echo "SimURF Test Suite"
echo "======================================"
echo ""

# Unit tests
echo "🧪 Running unit tests..."
python tests/test_simurf.py

if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed!"
    exit 1
fi

echo "✅ Unit tests passed!"
echo ""

# Check if MATLAB simulator is running
echo "🔍 Checking if MATLAB simulator is running..."
if ! nc -zv localhost 5000 2>/dev/null; then
    echo "⚠️  MATLAB simulator not detected on port 5000"
    echo "   Please start it first: python simulator/simurf_matlab_bridge.py"
    echo ""
    read -p "Skip integration tests? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "✅ All tests completed (integration tests skipped)"
        exit 0
    else
        exit 1
    fi
fi

# Integration tests
echo "🔗 Running integration tests..."
echo ""

# Test scenarios
scenarios=("demo" "short" "baseline")

for scenario in "${scenarios[@]}"; do
    echo "Testing scenario: $scenario"
    
    # Run sender in background
    timeout 30 docker-compose run --rm sender \
        python sender/sender_app.py --scenario $scenario &
    
    SENDER_PID=$!
    
    # Wait for completion
    wait $SENDER_PID
    
    if [ $? -ne 0 ]; then
        echo "❌ Scenario '$scenario' failed!"
        exit 1
    fi
    
    echo "✅ Scenario '$scenario' passed"
    echo ""
    
    # Small delay between scenarios
    sleep 2
done

echo ""
echo "======================================"
echo "✅ All tests passed!"
echo "======================================"
