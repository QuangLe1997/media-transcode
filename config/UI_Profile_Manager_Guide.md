# 🎨 UI Profile Manager - User Guide

## 🎯 **Tổng quan**

Profile Manager UI đã được tích hợp vào hệ thống transcode để quản lý **35 profiles** cho 3 tính năng chính:

- **AI Face Swap** (19 profiles)
- **Popup Home** (8 profiles) 
- **Banner Promoted** (8 profiles)

## 🚀 **Cách sử dụng**

### **1. Từ màn hình Upload**

#### **Trong tab Profiles Configuration:**
1. Click nút **🔧 Profile Manager** 
2. Modal ProfileManager sẽ hiện ra
3. Chọn feature và device tier
4. Preview profiles detail
5. Click **🚀 Use These Profiles** để load vào form upload

#### **Ví dụ sử dụng:**
```
1. Chọn "AI Face Swap - Video"
2. Chọn device tier "Both"
3. Xem 8 profiles được load
4. Click "Use These Profiles"
5. Profiles JSON tự động điền vào editor
6. Upload video để transcode
```

### **2. Page riêng Profile Manager**

#### **Truy cập:** `/profiles` hoặc click **🔧 Profile Manager** trên navigation

#### **Tính năng:**
- **Browse tất cả features** và profiles
- **Preview profiles detail** với JSON viewer
- **Copy to clipboard** generated profiles
- **Feature guide** với mô tả chi tiết
- **Direct link** to Upload page

## 🎛️ **Giao diện chi tiết**

### **Left Panel - Feature Selection**
```
📋 Select Feature & Device Tier
├── Feature Type: [Dropdown với 6 features]
│   ├── 🎭 AI Face Swap - Video
│   ├── 🎭 AI Face Swap - Image
│   ├── 🏠 Home Popup - Video
│   ├── 🏠 Home Popup - Image
│   ├── 📢 Banner Promoted - Video
│   └── 🎨 Banner Promoted - Image
│
├── Device Tier: [3 buttons]
│   ├── 🔄 Both Tiers (tất cả profiles)
│   ├── 📱 High-End (flagship devices)
│   └── 📞 Low-End (budget devices)
│
└── 📄 Available Profiles
    ├── [List profiles với hover effect]
    └── 🚀 Use These Profiles button
```

### **Right Panel - Profile Detail**
```
🔍 Profile Detail
├── Profile Name & Tags
├── JSON Viewer (read-only)
│   ├── Syntax highlighting
│   ├── Collapsible sections
│   └── Copy functionality
└── Configuration breakdown
```

## 📱 **Use Cases thực tế**

### **1. Admin upload AI Face Swap template**
```
Feature: ai_face_swap_video
Device: both
Profiles: 8 (preview, detail, AI processing)
Output: Video với 8 versions khác nhau
```

### **2. Admin upload Home Popup content**
```
Feature: popup_home_image  
Device: high
Profiles: 2 (WebP + JPEG cho high-end)
Output: Image cho popup 80% screen height
```

### **3. Admin upload Banner Promoted**
```
Feature: banner_promoted_video
Device: low  
Profiles: 2 (optimized cho budget devices)
Output: Video banner 1/3 screen height
```

## 🎨 **UI/UX Features**

### **✅ Visual Indicators:**
- **Color-coded device tiers** (green for selected)
- **Feature icons** cho dễ nhận biết
- **Loading spinners** during API calls
- **Success/Error messages** với màu sắc phù hợp

### **✅ Interactive Elements:**
- **Hover effects** trên profile list
- **Click to preview** profile detail
- **Copy to clipboard** functionality
- **Modal overlay** cho profile manager

### **✅ Responsive Design:**
- **Grid layout** adapts to screen size
- **Mobile-friendly** modal design
- **Scroll handling** cho long profile lists

## 🔧 **Integration với API**

### **API Endpoints được sử dụng:**
```javascript
GET /profiles              // List all features
GET /profiles/{feature}    // Get feature profiles  
GET /profiles/single/{id}  // Get single profile detail
```

### **Error Handling:**
- **Network errors**: Hiển thị user-friendly message
- **API errors**: Show specific error details
- **Validation**: Prevent invalid selections

## 🎯 **Benefits**

✅ **User Experience:**
- **No more manual JSON editing** cho profiles
- **Visual profile selection** thay vì copy-paste
- **Consistent profiles** across all uploads
- **Feature-specific optimization**

✅ **Developer Experience:** 
- **Centralized profile management**
- **Easy to add new profiles**
- **Consistent UI patterns**
- **Maintainable code structure**

✅ **Business Value:**
- **Faster content upload** workflow
- **Reduced user errors** 
- **Standardized output quality**
- **Scalable profile system**

## 🚀 **Workflow mới**

### **Trước (Old way):**
```
1. Manually write 35 profiles JSON
2. Copy-paste từ examples
3. Risk of syntax errors  
4. Time-consuming setup
```

### **Bây giờ (New way):**
```
1. Click "Profile Manager" 
2. Select feature (e.g., "AI Face Swap - Video")
3. Choose device tier
4. Click "Use These Profiles"  
5. Upload media → Done! 🎉
```

Hệ thống Profile Manager UI giúp việc transcode media trở nên **đơn giản, nhanh chóng và chính xác** hơn rất nhiều! 🎯