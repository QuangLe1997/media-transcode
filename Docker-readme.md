# Media Transcode Service - Docker Setup

Hướng dẫn chạy dịch vụ Media Transcode bằng Docker.

## Yêu cầu

- Docker
- Docker Compose (v2)
- NVIDIA Container Toolkit (nếu sử dụng GPU)

## Cấu trúc

Dịch vụ gồm các container sau:

1. **web**: Flask web application
2. **worker**: Celery worker cho xử lý video và hình ảnh
3. **flower**: Giao diện giám sát Celery
4. **redis**: Message broker cho Celery

## Hướng dẫn cài đặt

### 1. Chuẩn bị môi trường

#### Cài đặt Docker và Docker Compose

- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt update
  sudo apt install docker.io docker-compose-plugin
  sudo systemctl enable --now docker
  ```

- **Windows/Mac**: Cài đặt Docker Desktop từ [trang web Docker](https://www.docker.com/products/docker-desktop/)

#### NVIDIA Container Toolkit (chỉ cần nếu sử dụng GPU)

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### 2. Chạy dịch vụ

#### Sử dụng script tự động

Linux/Mac:
```bash
# Không sử dụng GPU
./run-docker.sh

# Với GPU support
./run-docker.sh --gpu
```

Windows:
```cmd
:: Không sử dụng GPU
run-docker.bat

:: Với GPU support
run-docker.bat --gpu
```

#### Thủ công

```bash
# Không sử dụng GPU
docker compose up -d

# Với GPU support
docker compose -f docker-compose.gpu.yml up -d
```

### 3. Truy cập dịch vụ

- **Flask Web App**: http://localhost:5000
- **Flower** (Celery monitoring): http://localhost:5555

## Cấu hình

### File .env

Tạo file `.env` trong thư mục gốc với nội dung sau:

```
# Flask settings
SECRET_KEY=change-this-in-production
FLASK_ENV=production

# AWS S3 settings (nếu sử dụng S3)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1
S3_BUCKET=your-bucket-name

# GPU settings
GPU_ENABLED=true  # hoặc false
GPU_TYPE=nvidia
```

### Dữ liệu ứng dụng

- Upload files: Lưu trong thư mục `./uploads`, được mount vào container
- Database: SQLite file lưu trong volume `instance`
- Redis data: Lưu trong volume `redis_data`

## Quản lý dịch vụ

### Xem logs

```bash
# Xem logs của tất cả services
docker compose logs

# Xem logs của service cụ thể
docker compose logs web
docker compose logs worker
```

### Restart dịch vụ

```bash
docker compose restart
```

### Dừng dịch vụ

```bash
docker compose down
```

### Xóa dữ liệu (cẩn thận)

```bash
docker compose down -v
```

## Xử lý sự cố

### Kiểm tra trạng thái container

```bash
docker compose ps
```

### Kiểm tra kết nối Redis

```bash
docker exec -it media-transcode-redis redis-cli ping
```

### Kiểm tra Celery worker

```bash
docker exec -it media-transcode-worker celery -A tasks.celery_config.celery_app inspect active
```

### Kiểm tra GPU (nếu sử dụng)

```bash
docker exec -it media-transcode-worker nvidia-smi
```