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

# Create non-root user
RUN useradd --create-home --shell /bin/bash simurf

# Copy application code and set permissions
COPY --chown=simurf:simurf main.py transmitter.py channel.py receiver.py test_sample.py usage_example.py ./
COPY --chown=simurf:simurf utils/ ./utils/

# Switch to non-root user
USER simurf

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 12345 12346

# Health check (ensure your app listens on 12345)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(1); s.connect(('localhost', 12345)); s.close()" || exit 1

# Default command
CMD ["python", "main.py", "--verbose"]
