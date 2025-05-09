#!/bin/bash

# Kiểm tra quyền
if [ "$EUID" -ne 0 ]; then
    echo "Khuyến nghị: Chạy script với quyền sudo để tránh các vấn đề với Docker"
    echo "Ví dụ: sudo ./run-docker.sh"
    echo "Tiếp tục không dùng sudo? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        exit 1
    fi
fi

# Kiểm tra Docker và Docker Compose đã được cài đặt chưa
if ! command -v docker &> /dev/null; then
    echo "Docker chưa được cài đặt. Vui lòng cài đặt Docker trước."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "Docker Compose chưa được cài đặt hoặc không phải là Compose V2. Vui lòng cài đặt Docker Compose V2."
    exit 1
fi

# Kiểm tra GPU nếu cần
USE_GPU=false
if [ "$1" == "--gpu" ] || [ "$1" == "-g" ]; then
    USE_GPU=true
    # Kiểm tra NVIDIA Docker
    if ! command -v nvidia-smi &> /dev/null; then
        echo "Cảnh báo: 'nvidia-smi' không tìm thấy, GPU có thể không khả dụng."
        echo "Tiếp tục? (y/n)"
        read -r response
        if [ "$response" != "y" ]; then
            exit 1
        fi
    fi

    if ! grep -q "nvidia" <<< "$(docker info)"; then
        echo "Cảnh báo: NVIDIA Docker runtime dường như không được cài đặt."
        echo "Xem: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
        echo "Tiếp tục? (y/n)"
        read -r response
        if [ "$response" != "y" ]; then
            exit 1
        fi
    fi
fi

# Tạo thư mục uploads nếu chưa tồn tại
mkdir -p uploads

# Chuẩn bị biến môi trường
if [ ! -f .env ]; then
    echo "Không tìm thấy file .env. Bạn có muốn tạo file này không? (y/n)"
    read -r response
    if [ "$response" == "y" ]; then
        cat > .env << EOL
# Flask settings
SECRET_KEY=change-this-in-production
FLASK_ENV=production

# AWS S3 settings (if using S3)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET=your-bucket-name

# GPU settings
GPU_ENABLED=$([ "$USE_GPU" == true ] && echo "true" || echo "false")
GPU_TYPE=nvidia
EOL
        echo "Đã tạo file .env. Vui lòng chỉnh sửa nó với thông tin của bạn."
        echo "Tiếp tục? (y/n)"
        read -r response
        if [ "$response" != "y" ]; then
            exit 1
        fi
    fi
fi

# Khởi động dịch vụ
if [ "$USE_GPU" == true ]; then
    echo "Khởi động Media Transcode Service với GPU support..."
    docker compose -f docker-compose.gpu.yml up -d
else
    echo "Khởi động Media Transcode Service..."
    docker compose up -d
fi

# Kiểm tra trạng thái
sleep 5
echo "Kiểm tra trạng thái dịch vụ..."
docker compose ps

echo ""
echo "Media Transcode Service đã được khởi động!"
echo "Web UI: http://localhost:5000"
echo "Flower (giám sát Celery): http://localhost:5555"
echo ""
echo "Để dừng dịch vụ, chạy: docker compose down"