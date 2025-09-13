# 🚀 Transcode Service - New Profile Template API

## 📋 **Tổng quan**

Service đã được nâng cấp với **ProfileTemplateService** để quản lý tất cả 35 profiles cho 3 tính năng:

- **AI Face Swap** (19 profiles): Template thumbnails, detail view, AI processing
- **Popup Home** (8 profiles): Full-screen popup 80% height
- **Banner Promoted** (8 profiles): Banner 1/3 height

## 🔧 **API Endpoints mới**

### **1. List All Profiles**
```bash
GET /profiles
```

**Response:**
```json
{
  "profiles": {
    "ai_face_swap_video": ["preview_webp_high", "preview_webp_low", ...],
    "ai_face_swap_image": ["thumb_webp_high", "thumb_webp_low", ...],
    "popup_home_video": ["popup_webp_high", "popup_webp_low", ...],
    "popup_home_image": ["popup_image_webp_high", ...],
    "banner_promoted_video": ["banner_webp_high", ...],
    "banner_promoted_image": ["banner_image_webp_high", ...]
  },
  "total_profiles": 35,
  "features": ["ai_face_swap_video", "ai_face_swap_image", ...]
}
```

### **2. Get Feature Profiles**
```bash
GET /profiles/{feature}?device_tier={tier}
```

**Parameters:**
- `feature`: ai_face_swap_video, ai_face_swap_image, popup_home_video, popup_home_image, banner_promoted_video, banner_promoted_image
- `device_tier`: both, high, low

**Example:**
```bash
GET /profiles/ai_face_swap_video?device_tier=high
```

### **3. Get Single Profile**
```bash
GET /profiles/single/{profile_id}
```

### **4. 🌟 Easy Feature Transcode (New!)**
```bash
POST /transcode/feature/{feature}
```

**Simplified API** - Chỉ cần chọn feature, service tự động load đúng profiles!

## 🎯 **Sử dụng thực tế**

### **AI Face Swap Template Upload**

```bash
# Video template
curl -X POST '/transcode/feature/ai_face_swap_video' \
  -F 'media_url=https://example.com/face-template.mp4' \
  -F 'device_tier=both' \
  -F 'enable_face_detection=true' \
  -F 'callback_url=https://your-api.com/webhook'

# Image template  
curl -X POST '/transcode/feature/ai_face_swap_image' \
  -F 'media_url=https://example.com/face-template.jpg' \
  -F 'device_tier=both' \
  -F 'enable_face_detection=true'
```

### **Home Popup Content**

```bash
# Video popup (80% screen height)
curl -X POST '/transcode/feature/popup_home_video' \
  -F 'media_url=https://example.com/popup-video.mp4' \
  -F 'device_tier=high'

# Image popup
curl -X POST '/transcode/feature/popup_home_image' \
  -F 'media_url=https://example.com/popup-image.jpg'
```

### **Banner Promoted Content**

```bash
# Video banner (1/3 screen height)
curl -X POST '/transcode/feature/banner_promoted_video' \
  -F 'media_url=https://example.com/banner-video.mp4' \
  -F 'device_tier=low'

# Image banner
curl -X POST '/transcode/feature/banner_promoted_image' \
  -F 'media_url=https://example.com/banner-image.jpg'
```

## 📱 **Response Example**

```json
{
  "task_id": "abc123-def456-ghi789",
  "status": "processing", 
  "feature": "ai_face_swap_video",
  "device_tier": "both",
  "source_url": "https://example.com/video.mp4",
  "input_type": "url",
  "profiles_count": 8,
  "published_profiles": 8,
  "failed_profiles": [],
  "face_detection_enabled": true,
  "face_detection_published": true,
  "media_detection": {
    "detected_type": "video",
    "original_profiles": 8,
    "filtered_profiles": 8,
    "skipped_profiles": []
  }
}
```

## 🎨 **JavaScript Integration**

```javascript
class TranscodeClient {
  async uploadTemplate(feature, mediaUrl, options = {}) {
    const formData = new FormData();
    formData.append('media_url', mediaUrl);
    formData.append('device_tier', options.deviceTier || 'both');
    
    if (feature.includes('ai_face_swap')) {
      formData.append('enable_face_detection', 'true');
    }
    
    const response = await fetch(`/transcode/feature/${feature}`, {
      method: 'POST',
      body: formData
    });
    
    return response.json();
  }
  
  // Usage examples
  async uploadAITemplate(videoUrl) {
    return this.uploadTemplate('ai_face_swap_video', videoUrl);
  }
  
  async uploadPopup(imageUrl, deviceTier = 'high') {
    return this.uploadTemplate('popup_home_image', imageUrl, { deviceTier });
  }
  
  async uploadBanner(videoUrl, deviceTier = 'low') {
    return this.uploadTemplate('banner_promoted_video', videoUrl, { deviceTier });
  }
}

// Usage
const client = new TranscodeClient();
const task = await client.uploadAITemplate('https://example.com/template.mp4');
console.log('Task ID:', task.task_id);
```

## 🔄 **Migration từ API cũ**

### **Trước (API cũ):**
```bash
curl -X POST '/transcode' \
  -F 'profiles=[{...}, {...}, {...}]' \  # Phải define 35 profiles!
  -F 's3_output_config={...}'
```

### **Bây giờ (API mới):**
```bash  
curl -X POST '/transcode/feature/ai_face_swap_video' \
  -F 'media_url=video.mp4'  # Chỉ cần chọn feature!
```

## ✅ **Lợi ích**

✅ **Đơn giản hóa**: Chỉ cần chọn feature, không cần define 35 profiles
✅ **Consistency**: Tất cả profiles đã được test và tối ưu
✅ **Auto S3 Config**: Mỗi feature có S3 config riêng
✅ **Face Detection**: Tự động enable cho AI face swap
✅ **Device Detection**: Tự động filter theo high/low tier
✅ **Media Detection**: Tự động skip profiles không tương thích

## 🎯 **Use Cases**

| Feature | Use Case | Profiles Generated |
|---------|----------|-------------------|
| `ai_face_swap_video` | Admin upload video template | 8 profiles |
| `ai_face_swap_image` | Admin upload image template | 11 profiles |
| `popup_home_video` | Home screen popup video | 4 profiles |
| `popup_home_image` | Home screen popup image | 4 profiles |
| `banner_promoted_video` | Promoted banner video | 4 profiles |
| `banner_promoted_image` | Promoted banner image | 4 profiles |

**Total: 35 profiles được quản lý tự động!** 🎉