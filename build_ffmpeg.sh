#!/bin/bash
set -e

# Script to build FFmpeg with CUDA support
# This script is designed for Ubuntu/Debian systems

# Output colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Print colored messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root (auto-continue in Docker)
if [ "$EUID" -ne 0 ]; then
    if [ -z "$DOCKER_BUILD" ]; then
        log_warn "This script is not running as root, which may cause permission issues."
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Exiting. Please run with sudo."
            exit 1
        fi
    else
        log_warn "Not running as root but DOCKER_BUILD detected - continuing..."
    fi
fi

# Set working directory
WORKDIR="$HOME/ffmpeg_build"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# Check if CUDA is installed
if [ ! -d "/usr/local/cuda" ] && [ ! -d "/usr/local/cuda-*" ]; then
    log_error "CUDA does not appear to be installed at /usr/local/cuda"
    log_info "Please install CUDA before running this script."
    log_info "Visit https://developer.nvidia.com/cuda-downloads for installation instructions."
    exit 1
fi

# Find CUDA version
CUDA_PATH=$(ls -d /usr/local/cuda-* 2>/dev/null | sort -V | tail -n 1)
if [ -z "$CUDA_PATH" ]; then
    CUDA_PATH="/usr/local/cuda"
fi
log_info "Found CUDA at $CUDA_PATH"

# Set environment variables
export PATH="$CUDA_PATH/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_PATH/lib64:$LD_LIBRARY_PATH"

# Detect number of CPU cores for faster compilation
CPUS=$(nproc)
log_info "Using $CPUS CPU cores for compilation"

# Install dependencies
log_info "Installing dependencies..."
apt-get update
apt-get install -y \
    autoconf \
    automake \
    build-essential \
    cmake \
    git-core \
    libass-dev \
    libfreetype6-dev \
    libgnutls28-dev \
    libmp3lame-dev \
    libsdl2-dev \
    libtool \
    libva-dev \
    libvdpau-dev \
    libvorbis-dev \
    libxcb1-dev \
    libxcb-shm0-dev \
    libxcb-xfixes0-dev \
    meson \
    ninja-build \
    pkg-config \
    texinfo \
    wget \
    yasm \
    zlib1g-dev \
    nasm

# Verify GnuTLS installation
if ! pkg-config --exists gnutls; then
    log_warn "GnuTLS not found by pkg-config. Installing additional dependencies..."
    apt-get install -y --reinstall libgnutls28-dev
    
    # If still not found, disable GnuTLS
    if ! pkg-config --exists gnutls; then
        log_warn "GnuTLS still not found. Will build FFmpeg without GnuTLS support."
        GNUTLS_FLAG=""
    else
        GNUTLS_FLAG="--enable-gnutls"
    fi
else
    GNUTLS_FLAG="--enable-gnutls"
fi

# Install NVIDIA drivers and CUDA headers if not already installed
log_info "Checking for NVIDIA drivers and CUDA development packages..."
if ! dpkg -l | grep -q "^ii.*nvidia-driver"; then
    log_warn "NVIDIA drivers not found. Please ensure appropriate drivers are installed."
    log_info "You may need to run: apt-get install nvidia-driver-<version>"
fi

if ! dpkg -l | grep -q "^ii.*cuda-toolkit"; then
    log_warn "CUDA toolkit not found in installed packages."
    log_info "This may be OK if you installed CUDA manually."
fi

# Build ffnvcodec (NVIDIA headers required for NVENC/NVDEC)
log_info "Building ffnvcodec (NVIDIA codec headers)..."
cd "$WORKDIR"
git clone https://git.videolan.org/git/ffmpeg/nv-codec-headers.git -b n12.1.14.0
cd nv-codec-headers
make
make install
log_info "ffnvcodec headers installed"

# Build NASM (newer version required for x264)
log_info "Building NASM..."
cd "$WORKDIR"
wget https://www.nasm.us/pub/nasm/releasebuilds/2.15.05/nasm-2.15.05.tar.bz2
tar xjf nasm-2.15.05.tar.bz2
cd nasm-2.15.05
./autogen.sh
./configure --prefix="$WORKDIR/ffmpeg_build" --bindir="$WORKDIR/bin"
make -j$CPUS
make install

# Build x264
log_info "Building x264..."
cd "$WORKDIR"
git clone --depth 1 https://code.videolan.org/videolan/x264.git
cd x264
PATH="$WORKDIR/bin:$PATH" ./configure --prefix="$WORKDIR/ffmpeg_build" --bindir="$WORKDIR/bin" --enable-static --enable-pic
PATH="$WORKDIR/bin:$PATH" make -j$CPUS
make install

# Build x265
log_info "Building x265..."
cd "$WORKDIR"
git clone https://bitbucket.org/multicoreware/x265_git
cd "$WORKDIR/x265_git/build/linux"
cmake -G "Unix Makefiles" -DCMAKE_INSTALL_PREFIX="$WORKDIR/ffmpeg_build" -DENABLE_SHARED=off ../../source
make -j$CPUS
make install

# Build libvpx
log_info "Building libvpx..."
cd "$WORKDIR"
git clone --depth 1 https://chromium.googlesource.com/webm/libvpx.git
cd libvpx
PATH="$WORKDIR/bin:$PATH" ./configure --prefix="$WORKDIR/ffmpeg_build" --disable-examples --disable-unit-tests --enable-vp9-highbitdepth --as=yasm
PATH="$WORKDIR/bin:$PATH" make -j$CPUS
make install

# Build libfdk-aac
log_info "Building libfdk-aac..."
cd "$WORKDIR"
git clone --depth 1 https://github.com/mstorsjo/fdk-aac
cd fdk-aac
autoreconf -fiv
./configure --prefix="$WORKDIR/ffmpeg_build" --disable-shared
make -j$CPUS
make install

# Build FFmpeg with CUDA support
log_info "Building FFmpeg with CUDA support..."
cd "$WORKDIR"
git clone https://git.ffmpeg.org/ffmpeg.git -b n7.1.1
cd ffmpeg
PATH="$WORKDIR/bin:$PATH" PKG_CONFIG_PATH="$WORKDIR/ffmpeg_build/lib/pkgconfig" ./configure \
    --prefix="$WORKDIR/ffmpeg_build" \
    --pkg-config-flags="--static" \
    --extra-cflags="-I$WORKDIR/ffmpeg_build/include -I$CUDA_PATH/include" \
    --extra-ldflags="-L$WORKDIR/ffmpeg_build/lib -L$CUDA_PATH/lib64" \
    --extra-libs="-lpthread -lm" \
    --bindir="$WORKDIR/bin" \
    --enable-gpl \
    $GNUTLS_FLAG \
    --enable-libass \
    --enable-libfdk-aac \
    --enable-libfreetype \
    --enable-libmp3lame \
    --enable-libvorbis \
    --enable-libvpx \
    --enable-libx264 \
    --enable-libx265 \
    --enable-nonfree \
    --enable-cuda-nvcc \
    --enable-libnpp \
    --enable-cuvid \
    --enable-nvenc \
    --enable-cuda \
    --enable-nvdec

PATH="$WORKDIR/bin:$PATH" make -j$CPUS
make install

# Create symlinks
log_info "Creating symbolic links to binaries..."
ln -sf "$WORKDIR/bin/ffmpeg" /usr/local/bin/
ln -sf "$WORKDIR/bin/ffprobe" /usr/local/bin/

# Verify installation
log_info "Verifying FFmpeg installation..."
if ffmpeg -version | grep -q "enable-cuda"; then
    log_info "FFmpeg with CUDA support has been successfully built!"
    log_info "FFmpeg is installed at: $WORKDIR/bin/ffmpeg"
    log_info "Installation location: $WORKDIR/ffmpeg_build"
    
    # Show CUDA-specific capabilities
    echo -e "\n${GREEN}=== FFmpeg CUDA Capabilities ===${NC}"
    ffmpeg -hide_banner -hwaccels | grep -i "cuda\|cuvid\|nvenc\|nvdec"
    
    echo -e "\n${GREEN}=== Full FFmpeg Version Information ===${NC}"
    ffmpeg -version
else
    log_error "FFmpeg installation appears to be missing CUDA support!"
    log_info "Check the build logs for errors."
fi

log_info "Build process complete."
