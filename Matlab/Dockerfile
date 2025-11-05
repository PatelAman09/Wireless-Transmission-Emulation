# Use an existing MATLAB runtime image or alternative
FROM mathworks/matlab:r2023a-runtime

# Alternatively, you can use Ubuntu and install MATLAB Runtime manually
# FROM ubuntu:20.04

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    net-tools \
    iproute2 \
    tcpdump \
    iputils-ping \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install numpy scipy scapy

# Create working directory structure
WORKDIR /simurf

# Copy project files
COPY matlab_components /simurf/matlab_components/
COPY python_components /simurf/python_components/
COPY scripts /simurf/scripts/
COPY config /simurf/default_configs/

# Make scripts executable
RUN chmod +x /simurf/scripts/*.sh

# Start SimuRF
CMD ["/simurf/scripts/start_simurf.sh"]