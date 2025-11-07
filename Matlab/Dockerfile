FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    net-tools \
    iproute2 \
    tcpdump \
    iputils-ping \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies including MATLAB Engine API
RUN pip3 install numpy scipy scapy matlabengine

# Create working directory
WORKDIR /simurf

# Copy project files
COPY . .

# Create directories
RUN mkdir -p /simurf/input /simurf/output /simurf/logs /simurf/matlab_components

# Set Python to not buffer output
ENV PYTHONUNBUFFERED=1

# Start with MATLAB-enhanced version
CMD ["python3", "python_components/network_manager_matlab.py"]