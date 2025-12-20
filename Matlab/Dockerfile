FROM ubuntu:22.04

RUN apt update && apt install -y \
    python3 python3-pip \
    iproute2 net-tools \
    && rm -rf /var/lib/apt/lists/*

# MATLAB must be installed or mounted
# Install MATLAB engine for Python here

WORKDIR /simurf
COPY . /simurf

CMD ["python3", "python_components/main.py"]
