FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    net-tools \
    iproute2 \
    tcpdump \
    iputils-ping \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install numpy scipy scapy

# Create working directory
WORKDIR /simurf

# Copy ALL files from current directory
COPY . .

# Verify files were copied
RUN echo "🔍 Checking files in container..." && \
    ls -la && \
    echo "📁 python_components contents:" && \
    ls -la python_components/ || echo "python_components not found!" && \
    echo "📁 config contents:" && \
    ls -la config/ || echo "config not found!"

# Create directories
RUN mkdir -p /simurf/input /simurf/output /simurf/logs

# Set Python to not buffer output
ENV PYTHONUNBUFFERED=1

# Start the application
CMD ["python3", "python_components/network_manager.py"]