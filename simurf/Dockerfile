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

# Copy application code
COPY . .

# Create utils directory structure
RUN mkdir -p utils test

# Expose ports for packet I/O
EXPOSE 12345 12346

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash simurf
RUN chown -R simurf:simurf /app
USER simurf

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('localhost', 12345)); s.close()" || exit 1

# Default command
CMD ["python", "main.py", "--verbose"]

# Alternative commands can be run as:
# docker run simurf python main.py --channel rayleigh --snr 15 --modulation qpsk
# docker run simurf python -m pytest test/ -v