FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Create directory for data exchange
RUN mkdir -p /data

# Expose network ports
EXPOSE 5000/udp
EXPOSE 5001/tcp

# Run the simulation server
CMD ["python", "./src/simulation_server.py"]