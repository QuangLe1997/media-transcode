# 🎬 Video to WebP Converter

## 📋 Mô tả
Tool chuyển đổi video sang WebP với đầy đủ thông số để test và fine-tune chất lượng trước khi áp dụng vào production.

## 🛠️ Yêu cầu
- Python 3.6+
- FFmpeg (cài đặt và có trong PATH)
- Video input bất kỳ (MP4, AVI, MOV, etc.)

## 📁 Files
- `video_to_webp_converter.py`: Converter chính với đầy đủ thông số
- `webp_test_suite.py`: Test suite để so sánh nhiều config
- `WebP_Converter_README.md`: File hướng dẫn này

## 🚀 Cách sử dụng

### 1. Converter đơn lẻ

```bash
# Chuyển đổi cơ bản
python video_to_webp_converter.py input.mp4 output.webp

# Chất lượng cao với resize
python video_to_webp_converter.py input.mp4 output.webp \
  --width 800 --height 600 --quality 90 --method 6

# Test với thông số cụ thể
python video_to_webp_converter.py input.mp4 output.webp \
  --fps 12 --duration 5 --quality 75 --preset photo

# Lossless compression
python video_to_webp_converter.py input.mp4 output.webp \
  --lossless --method 6

# Với filters
python video_to_webp_converter.py input.mp4 output.webp \
  --denoise --sharpen --contrast 1.1 --saturation 1.2
```

### 2. Test Suite (So sánh batch)

```bash
# Chạy tất cả tests
python webp_test_suite.py input.mp4

# Chỉ test presets
python webp_test_suite.py input.mp4 --test presets

# Test chất lượng
python webp_test_suite.py input.mp4 --test quality

# Test kích thước
python webp_test_suite.py input.mp4 --test sizes

# Test FPS
python webp_test_suite.py input.mp4 --test fps
```

## ⚙️ Thông số chính - Giải thích chi tiết

### 📏 KÍCH THƯỚC (Width & Height)

#### `--width` và `--height` là gì?
- **Width**: Chiều RỘNG của video (tính theo pixel)
- **Height**: Chiều CAO của video (tính theo pixel)
- **Pixel**: Điểm ảnh - đơn vị nhỏ nhất tạo nên hình ảnh

#### Ví dụ thực tế:
```bash
# Video gốc: 1920x1080 (Full HD)
# Muốn thu nhỏ còn 1/3:
--width 640 --height 360

# Chỉ set width, height tự động tính theo tỷ lệ:
--width 500  # Height sẽ tự động = 281 (giữ tỷ lệ 16:9)

# Chỉ set height, width tự động:
--height 720  # Width sẽ tự động = 1280 (giữ tỷ lệ)
```

#### Kích thước phổ biến và khi nào dùng:
- **1920×1080** (Full HD): Quá lớn cho WebP, không nên dùng
- **1280×720** (HD): Banner quảng cáo lớn, hero section
- **800×600**: Banner web thông thường
- **640×480**: Preview video trên web
- **360×480**: Preview mobile, thumbnail lớn
- **240×320**: Thumbnail nhỏ, icon động

#### 💡 Càng nhỏ = File càng nhẹ = Load càng nhanh

---

### ⏱️ FPS (Frame Per Second - Số khung hình/giây)

#### FPS là gì?
- Video = nhiều hình ảnh nối tiếp nhau
- FPS = Số hình ảnh hiển thị trong 1 giây
- FPS cao = Mượt hơn nhưng file nặng hơn

#### Ví dụ thực tế:
```bash
# Video gốc 30fps, muốn giảm xuống:
--fps 15  # Giảm 50% số frame = file nhẹ 50%

# Cho animation đơn giản:
--fps 10  # Đủ mượt cho banner

# Cho preview phim:
--fps 24  # Chuẩn cinema, mượt mà
```

#### Chọn FPS như thế nào:
- **5-8 FPS**: Slideshow, ảnh chuyển cảnh (rất nhẹ)
- **10-12 FPS**: Animation đơn giản, banner quảng cáo
- **15 FPS**: Cân bằng tốt cho web (RECOMMENDED)
- **20-24 FPS**: Video mượt, preview chất lượng cao
- **30 FPS**: Quá cao cho WebP, tốn dung lượng

#### 💡 Rule: Giảm FPS từ 30 → 15 = Giảm 50% dung lượng

---

### ⏰ DURATION & START-TIME

#### Duration là gì?
- Độ dài video output (tính bằng giây)
- Video gốc 60s, set duration=5 → Chỉ lấy 5 giây

#### Start-time là gì?  
- Bắt đầu cắt từ giây thứ mấy
- Video 30s, start-time=10 → Bỏ 10s đầu, lấy từ giây 10

#### Ví dụ thực tế:
```bash
# Lấy 5 giây đầu video (cho preview):
--duration 5

# Lấy 3 giây, bắt đầu từ giây thứ 2 (bỏ intro):
--start-time 2 --duration 3

# Lấy highlight giữa video (giây 10-15):
--start-time 10 --duration 5
```

#### Khi nào dùng:
- **Preview phim**: 5-10 giây highlights
- **Banner ads**: 3-8 giây loop
- **Product demo**: 10-15 giây
- **Thumbnail động**: 2-3 giây

---

### 🎨 QUALITY (Chất lượng nén)

#### Quality là gì?
- Mức độ nén hình ảnh (0-100)
- Cao = Đẹp nhưng nặng
- Thấp = Xấu nhưng nhẹ

#### Ví dụ cụ thể:
```bash
# Chất lượng cao cho product showcase:
--quality 85  # File: ~500KB cho 5s video

# Chất lượng trung bình cho banner:
--quality 70  # File: ~300KB cho 5s video  

# Chất lượng thấp cho thumbnail:
--quality 50  # File: ~150KB cho 5s video
```

#### So sánh quality levels:
- **90-100**: Gần như không thấy khác biệt với gốc (File RẤT NẶNG)
- **75-85**: Chất lượng tốt, khó phân biệt (RECOMMENDED)
- **60-75**: Chất lượng khá, thấy compress nhẹ
- **40-60**: Chất lượng trung bình, thấy artifact
- **20-40**: Chất lượng kém, nhiều artifact
- **0-20**: Chỉ dùng khi cần file CỰC NHẸ

#### 💡 Sweet spot: 70-80 cho hầu hết use cases

---

### ⚙️ METHOD (Phương pháp nén)

#### Method là gì?
- Thuật toán nén WebP sử dụng
- Số cao = Nén tốt hơn nhưng chậm hơn

#### Ví dụ thực tế:
```bash
# Cần convert nhanh (hàng loạt file):
--method 1  # 2 giây/file

# Cân bằng speed và quality:
--method 4  # 5 giây/file (DEFAULT)

# Cần quality tốt nhất:
--method 6  # 15 giây/file
```

#### Khi nào dùng method nào:
- **Method 0-1**: Bulk conversion, realtime processing
- **Method 2-3**: Daily operations, user uploads
- **Method 4**: Default, cân bằng tốt
- **Method 5-6**: Final production, marketing materials

#### Thời gian convert (ước tính cho video 5s):
- Method 0: ~1 giây
- Method 2: ~3 giây  
- Method 4: ~6 giây
- Method 6: ~15 giây

---

### 🎯 PRESET (Cài đặt sẵn)

#### Preset là gì?
- Config tối ưu sẵn cho từng loại nội dung
- WebP tự động điều chỉnh các thông số nội bộ

#### Các preset và khi nào dùng:
```bash
# Video người thật, phong cảnh:
--preset photo

# Cartoon, animation:
--preset drawing  

# Logo, text, screenshot:
--preset text

# Icon, graphic đơn giản:
--preset icon
```

#### Ví dụ thực tế:
- **Fashion video** → `--preset photo`
- **Anime/Cartoon** → `--preset drawing`
- **Tutorial screencast** → `--preset text`
- **Logo animation** → `--preset icon`

---

### 🔄 LOSSLESS (Nén không mất dữ liệu)

#### Lossless là gì?
- Giữ 100% chất lượng gốc
- File SIÊU NẶNG (gấp 5-10 lần lossy)

#### Khi nào dùng:
```bash
# Logo animation cần sắc nét tuyệt đối:
--lossless --method 6

# Medical imaging, technical drawings:
--lossless
```

#### ⚠️ Cảnh báo: File có thể nặng 10-20MB cho video ngắn!

### 🎨 Filters
- `--denoise`: Giảm nhiễu
- `--sharpen`: Làm sắc nét
- `--contrast 0.5-2.0`: Tăng/giảm contrast
- `--brightness -1.0-1.0`: Tăng/giảm độ sáng
- `--saturation 0.0-3.0`: Tăng/giảm độ bão hòa

### 🔧 Tối ưu hóa
- `--auto-filter`: Tự động tối ưu
- `--two-pass`: Nén 2 lần (chậm hơn nhưng tốt hơn)
- `--target-size KB`: Kích thước đích (KB)
- `--near-lossless 0-100`: Gần lossless

## 📊 Kết quả Test Suite

Test suite sẽ tạo:
- `webp_tests/`: Folder chứa tất cả file WebP test
- `comparison_report.json`: Báo cáo chi tiết JSON
- Console output với thống kê

Ví dụ output:
```
📊 FINAL COMPARISON REPORT
================================================================================
✅ Total Tests: 42
✅ Successful: 40
❌ Failed: 2

🏆 BEST PERFORMERS:
📁 Smallest File: quality_30 (0.25MB)
⚡ Fastest: method_0 (1.2s)  
🎨 Highest Quality: quality_100 (Q100)
```

## 📊 Bảng tham khảo nhanh các thông số quan trọng

| Thông số | Giá trị | Ảnh hưởng | Gợi ý |
|----------|---------|-----------|-------|
| **width/height** | 240-1920 | Size file & chất lượng | 360x480 (preview), 800x600 (banner) |
| **fps** | 5-30 | Độ mượt & size | 10-15 cho web |
| **quality** | 0-100 | Chất lượng hình ảnh | 70-85 cho production |
| **method** | 0-6 | Tốc độ convert & chất lượng | 2-4 cho cân bằng |
| **duration** | 1-15s | Độ dài video | 3-6s cho preview |

### 🎯 Config theo use case:

| Use Case | Width×Height | FPS | Quality | Method | Duration |
|----------|-------------|-----|---------|---------|----------|
| **Thumbnail nhỏ** | 240×320 | 8 | 60 | 1 | 2-3s |
| **Preview video** | 360×480 | 12 | 75 | 3 | 5-6s |
| **Banner quảng cáo** | 800×600 | 15 | 80 | 4 | 8-10s |
| **High quality** | 1280×720 | 20 | 90 | 6 | 10-15s |
| **Ultra light** | 180×240 | 5 | 40 | 0 | 2s |

## 💡 Gợi ý tối ưu

### Cho Preview/Thumbnail:
```bash
python video_to_webp_converter.py input.mp4 preview.webp \
  --width 360 --height 480 --fps 10 --duration 3 \
  --quality 70 --method 2
```

### Cho Banner/Ad:
```bash
python video_to_webp_converter.py input.mp4 banner.webp \
  --width 800 --height 600 --fps 12 --duration 5 \
  --quality 75 --method 4 --preset photo
```

### Chất lượng cao:
```bash
python video_to_webp_converter.py input.mp4 hq.webp \
  --width 1280 --height 720 --fps 15 --duration 8 \
  --quality 85 --method 6 --denoise
```

### Kích thước nhỏ nhất:
```bash
python video_to_webp_converter.py input.mp4 tiny.webp \
  --width 240 --height 320 --fps 8 --duration 2 \
  --quality 50 --method 1
```

## 🔍 Debug

### Kiểm tra FFmpeg:
```bash
ffmpeg -version
ffmpeg -encoders | grep webp
```

### Thông tin chi tiết:
```bash
python video_to_webp_converter.py input.mp4 output.webp --verbose
```

### Kiểm tra output:
```bash
ffprobe output.webp
file output.webp
ls -la output.webp
```

## 📈 So sánh với các format khác

Test tương đương:
```bash
# WebP
python video_to_webp_converter.py input.mp4 test.webp --quality 75

# GIF (để so sánh)
ffmpeg -i input.mp4 -vf "fps=15,scale=640:480" test.gif

# MP4 (để so sánh) 
ffmpeg -i input.mp4 -vf "fps=15,scale=640:480" -crf 28 test.mp4
```

## 📝 CHEAT SHEET - TRA CỨU NHANH

### 🎯 Muốn file NHẸ NHẤT có thể:
```bash
--width 240 --height 320 --fps 8 --quality 40 --method 0 --duration 3
# Kết quả: ~100-200KB cho video 3 giây
```

### 🎨 Muốn CHẤT LƯỢNG TỐT:
```bash
--width 640 --height 480 --fps 15 --quality 85 --method 6 --duration 5
# Kết quả: ~800KB-1MB cho video 5 giây
```

### ⚡ Muốn CONVERT NHANH:
```bash
--quality 70 --method 1 --fps 12
# Convert trong 1-2 giây
```

### 💰 Muốn CÂN BẰNG tốt (recommended):
```bash
--width 360 --height 480 --fps 12 --quality 75 --method 3 --duration 5
# Kết quả: ~300-500KB, chất lượng tốt
```

### 📱 Cho MOBILE:
```bash
--width 360 --height 640 --fps 10 --quality 70 --method 2 --duration 5
# Tối ưu cho màn hình dọc mobile
```

### 🖥️ Cho DESKTOP:
```bash
--width 800 --height 600 --fps 15 --quality 80 --method 4 --duration 8
# Banner web, hero section
```

## 🎯 Workflow đề xuất

1. **Test cơ bản**: Chạy converter với config mặc định
2. **Test suite**: Chạy test suite để tìm config tối ưu
3. **Fine-tune**: Điều chỉnh thông số dựa trên kết quả
4. **Production**: Áp dụng config tốt nhất vào transcode service

## 🐛 Troubleshooting

### FFmpeg không tìm thấy:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian  
sudo apt install ffmpeg

# Hoặc chỉ định path cụ thể
export PATH="/path/to/ffmpeg:$PATH"
```

### Lỗi WebP encoder:
```bash
ffmpeg -encoders | grep webp
# Nếu không có libwebp, cần compile lại FFmpeg với WebP support
```

### File quá lớn:
- Giảm `--quality`
- Giảm `--fps` 
- Giảm `--width` và `--height`
- Giảm `--duration`
- Dùng `--method 1` hoặc `2`

### Conversion chậm:
- Dùng `--method 0` hoặc `1`
- Bỏ `--two-pass`
- Bỏ filters như `--denoise`, `--sharpen`