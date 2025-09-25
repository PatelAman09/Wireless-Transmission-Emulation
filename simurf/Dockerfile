# Wireless Channel Emulator Docker Image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory structure
RUN mkdir -p utils test

# Copy application files
COPY main.py .
COPY transmitter.py .
COPY channel.py .
COPY receiver.py .
COPY test_sample.py .
COPY usage_example.py .

# Copy utils module
COPY utils/ ./utils/

# Expose ports for packet I/O
EXPOSE 12345 12346

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash simurf
RUN chown -R simurf:simurf /app
USER simurf

# Default command
CMD ["python", "main.py", "--verbose"]