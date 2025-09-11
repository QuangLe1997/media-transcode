# Use NVIDIA CUDA base image for GPU support
FROM registry.skylink.vn/nvidia/cuda:12.2.2-cudnn8-devel-ubuntu22.04

# Set environment variables
ENV NVIDIA_DRIVER_CAPABILITIES=video,compute,utility
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Set working directory
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb && \
    dpkg -i cuda-keyring_1.1-1_all.deb && \
    rm cuda-keyring_1.1-1_all.deb

# Install dependencies with explicit GnuTLS packages
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    git \
    curl \
    ffmpeg \
    libunistring-dev \
    nettle-dev \
    pkg-config \
    build-essential \
    libcudnn9-cuda-12 \
    cuda-libraries-12-2 \
    && rm -rf /var/lib/apt/lists/*

# Create Python symlinks
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3



# Copy requirements first for better caching
COPY requirements.txt requirements-face-detection.txt ./

RUN pip install -r requirements.txt && \
    pip install -r requirements-face-detection.txt

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p logs temp /tmp/transcode models_faces && \
    chmod 755 logs temp /tmp/transcode && \
    chmod 777 models_faces


# FFmpeg configuration - using default ffmpeg from apt (no custom build)
ENV FFMPEG_HWACCEL=auto
ENV FFMPEG_GPU_ENABLED=auto
ENV FFMPEG_PATH=/usr/bin/ffmpeg
ENV FFPROBE_PATH=/usr/bin/ffprobe

# Expose port
EXPOSE 8087

# Optimized health check
HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=2 \
    CMD curl -f http://localhost:8087/health || exit 1

# Use exec form for faster startup
CMD ["python", "-O", "main.py"]