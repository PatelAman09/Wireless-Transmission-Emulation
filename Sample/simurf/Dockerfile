# Base Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /simurf

# Copy files
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY .. .

# Entry point
CMD ["python", "run_simurf.py"]
