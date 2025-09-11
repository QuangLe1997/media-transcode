# GPU Hardware Acceleration Setup

This guide helps you deploy the transcode service with NVIDIA GPU hardware acceleration for faster H.264/H.265 encoding.

## Prerequisites

### Server Requirements
- NVIDIA GPU with NVENC support (GTX 10xx series or newer)
- Ubuntu 18.04+ or similar Linux distribution
- Docker and Docker Compose
- NVIDIA drivers installed

### Check GPU Support
```bash
# Check if NVIDIA GPU is detected
nvidia-smi

# Check NVIDIA driver version (should be 470+ for best compatibility)
cat /proc/driver/nvidia/version
```

## Quick Setup

### 1. Upload Files to Server
Upload these files to your server (`192.168.0.234:6789`):
- `Dockerfile.gpu`
- `docker-compose.gpu.yml`
- `check-gpu.sh`
- `deploy-gpu.sh`
- All existing project files

### 2. Check GPU Compatibility
```bash
ssh skl@192.168.0.234 -p 6789
cd /path/to/transcode-project
./check-gpu.sh
```

### 3. Deploy with GPU Support
```bash
./deploy-gpu.sh
```

## Manual Setup Steps

### 1. Install NVIDIA Docker Support
```bash
# Add NVIDIA Docker repository
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install nvidia-docker2
sudo apt-get update
sudo apt-get install -y nvidia-docker2

# Restart Docker
sudo systemctl restart docker
```

### 2. Test GPU Access
```bash
# Test GPU access in Docker
docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi
```

### 3. Build and Deploy
```bash
# Build GPU-enabled images
docker-compose -f docker-compose.gpu.yml build

# Start services
docker-compose -f docker-compose.gpu.yml up -d

# Check logs
docker-compose -f docker-compose.gpu.yml logs -f
```

## GPU Codec Profiles

The system includes optimized profiles for GPU acceleration:

### H.264 NVENC Profiles
- `high_main_video` - Uses `h264_nvenc` codec
- `high_main_video_gpu_h256` - Uses `h265_nvenc` codec
- `high_thumbs_video_l` - Uses `h264_nvenc` for thumbnails

### Example Profile Configuration
```json
{
  "id_profile": "gpu_720p_h264",
  "output_type": "video",
  "video_config": {
    "codec": "h264_nvenc",
    "max_width": 720,
    "max_height": 1280,
    "crf": 20,
    "max_bitrate": "4000k",
    "preset": "medium",
    "profile": "high",
    "level": "4.1",
    "max_fps": 30,
    "audio_codec": "aac",
    "audio_bitrate": "128k"
  },
  "input_type": "video"
}
```

## Performance Comparison

| Codec | Relative Speed | Quality | Use Case |
|-------|---------------|---------|----------|
| libx264 (CPU) | 1x | High | CPU-only servers |
| h264_nvenc (GPU) | 3-5x | Good | GPU servers, fast encoding |
| libx265 (CPU) | 0.3x | Highest | High quality, slow |
| h265_nvenc (GPU) | 2-3x | Good | GPU servers, smaller files |

### Example Encoding Times (1080p video)
- **CPU H.264**: 30-60 seconds
- **GPU H.264**: 10-20 seconds
- **CPU H.265**: 100-200 seconds  
- **GPU H.265**: 30-60 seconds

## GPU Optimization Features

### FFmpeg Arguments Generated
For GPU codecs, the system automatically generates optimized arguments:

```bash
# CPU H.264
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -preset medium output.mp4

# GPU H.264 (optimized)
ffmpeg -i input.mp4 -c:v h264_nvenc -cq 23 -preset medium -rc vbr -rc-lookahead 20 output.mp4
```

### Key GPU Optimizations
- Uses `-cq` instead of `-crf` for NVENC
- Adds `-rc vbr` for variable bitrate
- Adds `-rc-lookahead 20` for better quality
- Maps CPU presets to NVENC presets
- Proper bufsize calculation for rate control

## Monitoring GPU Usage

### Check GPU Utilization
```bash
# Real-time GPU monitoring
watch -n 1 nvidia-smi

# GPU memory usage
nvidia-smi --query-gpu=memory.used,memory.total --format=csv

# GPU utilization in container
docker-compose -f docker-compose.gpu.yml exec consumer nvidia-smi
```

### Container Resource Limits
The GPU docker-compose includes optimized resource limits:
- **Consumer**: 2GB RAM, 4 CPU cores, 1 GPU
- **API**: 1GB RAM, 2 CPU cores, GPU access
- **Shared temp storage**: `/tmp/transcode`

## Troubleshooting

### Common Issues

1. **GPU not detected in container**
   ```bash
   # Check Docker GPU runtime
   docker info | grep nvidia
   
   # Test GPU access
   docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi
   ```

2. **NVENC encoder not available**
   ```bash
   # Check FFmpeg encoders in container
   docker-compose -f docker-compose.gpu.yml exec consumer ffmpeg -encoders | grep nvenc
   ```

3. **Out of GPU memory**
   ```bash
   # Check GPU memory usage
   nvidia-smi
   
   # Reduce concurrent transcoding or lower resolution
   ```

### Log Analysis
```bash
# Check container logs
docker-compose -f docker-compose.gpu.yml logs consumer

# Monitor real-time processing
docker-compose -f docker-compose.gpu.yml logs -f consumer | grep "NVENC\|GPU\|h264_nvenc"
```

## Configuration Files

### Key Files for GPU Setup
- `Dockerfile.gpu` - GPU-enabled container image
- `docker-compose.gpu.yml` - GPU service configuration
- `mobile_profile_system.py` - GPU codec logic
- `faceswap_profiles_config.json` - GPU profile definitions

### Environment Variables
Add to your `.env` file:
```bash
# Enable GPU features
FFMPEG_HWACCEL=cuda
FFMPEG_GPU_ENABLED=1
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility,video
```

## Production Deployment

### Auto-restart Configuration
```bash
# Enable auto-restart for GPU services
docker-compose -f docker-compose.gpu.yml up -d --restart unless-stopped
```

### Health Monitoring
The GPU setup includes enhanced health checks:
- Longer startup time (30s) for GPU initialization
- GPU memory monitoring
- NVENC availability verification

### Scaling Considerations
- **Single GPU**: Handle 4-8 concurrent 720p transcodes
- **Multiple GPUs**: Use Docker Swarm or Kubernetes for scaling
- **GPU sharing**: Multiple containers can share one GPU efficiently

## Support

For issues with GPU setup:
1. Run `./check-gpu.sh` and share output
2. Check container logs: `docker-compose -f docker-compose.gpu.yml logs`
3. Verify GPU drivers: `nvidia-smi`
4. Test FFmpeg NVENC: `ffmpeg -encoders | grep nvenc`