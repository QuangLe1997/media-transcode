# Unified Media Conversion Suite

🎬 **Complete media conversion suite** with multiple tools and advanced parameter control:
- **WebP Converter**: Convert video/image to WebP
- **Media Transcode**: Convert image to JPG, video to MP4

## 📁 Structure

```
app_local/
├── unified_media_server.py        # Main Flask server (all services)
├── media_to_webp_converter.py     # WebP conversion engine
├── media_transcode_converter.py   # JPG/MP4 conversion engine
├── webp_converter_ui.html         # WebP converter interface
├── media_transcode_ui.html        # Universal transcode interface
├── webp_viewer.html               # WebP file viewer
├── quick_webp_test.py             # Command line test script
├── start_unified_server.py        # Unified server launcher
├── README.md                      # This documentation
├── temp_uploads/                  # Temporary upload storage
├── videos/                        # WebP conversion folders
│   ├── input/                     # Input videos for WebP
│   └── output/                    # WebP output files
└── transcode_output/              # JPG/MP4 output files
```

## 🚀 Quick Start

### Option 1: Using Unified Launcher
```bash
cd app_local
python start_unified_server.py
```

### Option 2: Direct Server Start
```bash
cd app_local
python unified_media_server.py
```

### Access Points:
- **WebP Converter**: http://localhost:5001/webp
- **Media Transcode**: http://localhost:5001/transcode  
- **WebP Viewer**: http://localhost:5001/viewer
- **Default (WebP)**: http://localhost:5001

## ⚙️ Features

### 🎨 WebP Converter Features
#### 🎯 Basic Settings
- **Width/Height**: Resize control (maintains aspect ratio)
- **Quality**: 0-100 compression level
- **FPS**: Frame rate control
- **Speed**: 0.5x to 2.0x playback speed
- **Duration**: Output length in seconds
- **Start Time**: Skip beginning of video

#### 🔧 Advanced Settings
- **Method**: Compression method (0-6, higher = better quality)
- **Preset**: Optimization for content type (default, photo, drawing, etc.)
- **Lossless**: Perfect quality, larger file size
- **Target KB**: Automatic quality adjustment to reach file size
- **Near Lossless**: High quality with some compression
- **Alpha Quality/Method**: Transparency channel settings

### 🎬 Media Transcode Features
#### 🖼️ Image to JPG
- **JPEG Quality**: 0-100 quality control
- **Optimize**: Huffman table optimization
- **Progressive**: Progressive JPEG encoding
- **Color Adjustments**: Contrast, brightness, saturation, gamma
- **Filters**: Denoising, sharpening

#### 🎬 Video to MP4
- **Codec**: H.264 or H.265 (HEVC)
- **CRF**: Constant Rate Factor (0-51, lower = better)
- **Preset**: Speed vs quality (ultrafast to veryslow)
- **Bitrate Control**: Fixed bitrate, max bitrate, buffer size
- **Profile/Level**: H.264 profile and level settings
- **Audio**: AAC, MP3, or no audio with bitrate control
- **Advanced**: Two-pass encoding, hardware acceleration

#### 🎨 Common Processing
- **Color Adjustments**: Contrast, brightness, saturation, gamma
- **Filters**: Denoising, sharpening
- **Resize**: Width/height with aspect ratio preservation

## 📤 Output Features

- **Smart Filenames**: Include key parameters for easy identification
  - Format: `{id}_{name}_w{width}_q{quality}_{fps}fps_{speed}x_{duration}s.webp`
  - Example: `a1b2_video1_w360_q85_15fps_1.5x_6s.webp`

- **Result Display**: 
  - Actual dimensions and file size
  - Conversion time vs output duration
  - Configuration review and copy
  - Delete functionality

- **Advanced Info**: Expandable section showing all used parameters

## 🎮 Usage Examples

### High Quality Animation
```
Width: 540px
Quality: 90
FPS: 15
Method: 6 (Best)
Preset: drawing
```

### Small Social Media Clip
```
Width: 360px
Quality: 75
FPS: 12
Speed: 1.2x
Duration: 3s
Target: 500KB
```

### Logo/Icon Animation
```
Lossless: True
Preset: icon
FPS: 10
Duration: 2s
```

## 🔧 Dependencies

- Python 3.7+
- FFmpeg with libwebp support
- webpinfo (from libwebp-tools)
- Flask, Flask-CORS

## 📝 API Endpoints

- `GET /` - Web UI
- `POST /api/convert` - Convert video to WebP
- `GET /api/output/<filename>` - Serve WebP files
- `GET /api/files` - List output files
- `GET /api/presets` - Get preset configurations
- `GET /api/health` - Health check

## 💡 Tips

1. **Aspect Ratio**: Only set width OR height to maintain proportions
2. **File Size**: Use Target KB for upload size limits
3. **Quality vs Size**: Quality 85 is usually optimal
4. **Speed vs Duration**: Speed affects playback, Duration affects output length
5. **Presets**: Choose based on content type for better optimization