FROM python:3.10-slim

# Cài đặt các gói cần thiết và FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libmagic1 \
    wget \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt NVIDIA GPU drivers (bỏ comment nếu cần)
# RUN wget -q -O - https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub | apt-key add - && \
#     echo "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64 /" > /etc/apt/sources.list.d/cuda.list && \
#     apt-get update && apt-get install -y --no-install-recommends \
#     cuda-toolkit-11-8 \
#     && rm -rf /var/lib/apt/lists/*

# Tạo thư mục ứng dụng
WORKDIR /app

# Cài đặt dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . /app/

# Tạo thư mục uploads và tmp
RUN mkdir -p /app/uploads /tmp/transcode-jobs

# Mở port
EXPOSE 5000

# Biến môi trường
ENV PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    UPLOAD_FOLDER=/app/uploads \
    TEMP_STORAGE_PATH=/tmp/transcode-jobs

# Entrypoint script
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]