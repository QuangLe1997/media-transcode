# 📋 Config Templates Manager - User Guide

## 🎯 **Overview**

The Config Templates Manager is a comprehensive UI for managing configuration templates in the transcode system. It provides full CRUD (Create, Read, Update, Delete) operations for profile templates stored in the database.

## 🌐 **Access**

- **URL**: `http://192.168.0.234:3000/config-templates`
- **Navigation**: Click **📋 Config Templates** in the main navigation bar

## ✨ **Features**

### 🔍 **Template Discovery**
- **Search functionality**: Search by template name or ID
- **Template grid view**: Visual cards showing template information
- **Real-time statistics**: Total template count and search results
- **Refresh capability**: Reload templates from database

### ➕ **Create New Templates**
- **JSON Editor**: Monaco editor with syntax highlighting
- **Template validation**: Real-time JSON validation
- **Format helper**: Auto-format JSON button
- **Template naming**: Descriptive name assignment

### 👁️ **View Templates**
- **Read-only view**: Browse template configuration safely
- **Full JSON display**: Complete profile configuration
- **Template metadata**: ID, creation date, profile count
- **Profile type summary**: Output types at a glance

### ✏️ **Edit Templates**
- **Live editing**: Monaco editor for JSON configuration
- **Name changes**: Update template names
- **Validation**: Real-time error checking
- **Format assistance**: JSON formatting helper

### 🗑️ **Delete Templates**
- **Confirmation dialog**: Prevents accidental deletion
- **Warning messages**: Clear deletion consequences
- **Safe removal**: Complete cleanup from database

### 📋 **Template Operations**
- **Copy to clipboard**: Quick JSON copying for reuse
- **Template statistics**: Profile count and types
- **Creation timestamps**: When templates were added
- **Update tracking**: Last modification dates

## 🎛️ **Interface Guide**

### **Main Dashboard**
```
📋 Config Templates Manager
├── Search bar (🔍 Search templates...)
├── Refresh button (🔄 Refresh)
├── Create button (➕ New Template)
└── Template statistics (📊 Total: X templates)
```

### **Template Cards**
```
Template Card
├── Template Name (clickable header)
├── Template ID (monospace identifier)
├── Profile Count (📁 X profiles)  
├── Output Types (Types: video, image, etc.)
├── Creation Date (MM/DD/YYYY)
└── Action Buttons:
    ├── 👁️ View (read-only preview)
    ├── ✏️ Edit (modify configuration)
    ├── 📋 Copy (copy JSON to clipboard)
    └── 🗑️ Delete (remove template)
```

### **Modal Dialogs**

#### **Create Template Modal**
- Template name input field
- Monaco JSON editor (300px height)
- Format JSON button
- Create/Cancel buttons

#### **Edit Template Modal**  
- Pre-filled template name
- Pre-loaded JSON configuration
- Monaco JSON editor
- Save Changes/Cancel buttons

#### **View Template Modal**
- Template metadata display
- Read-only Monaco editor (400px height)
- Copy JSON/Close buttons

#### **Delete Confirmation Modal**
- Template name confirmation
- Warning about permanent deletion
- Delete/Cancel buttons

## 🔧 **JSON Configuration Format**

Templates use the standard transcode profile format:

```json
[
  {
    "id_profile": "profile_identifier",
    "output_type": "video|image|gif|webp", 
    "input_type": "video|image",
    "video_config": {
      "codec": "libx264",
      "max_width": 1280,
      "max_height": 720,
      "crf": 23,
      "preset": "medium"
    }
  }
]
```

### **Validation Rules**
- **JSON Format**: Must be valid JSON array
- **Profile Structure**: Each profile needs `id_profile` and `output_type`
- **Configuration**: Type-specific config objects (video_config, image_config, etc.)
- **Constraints**: Follow schema validation rules (e.g., max height 1080 for WebP/GIF)

## 🚀 **Workflow Examples**

### **Creating a Template**
1. Click **➕ New Template**
2. Enter descriptive template name
3. Replace example JSON with your configuration
4. Use **🎨 Format JSON** if needed
5. Click **✅ Create Template**

### **Editing a Template**
1. Find template in grid view
2. Click **✏️ Edit** button
3. Modify name or JSON configuration
4. Validate changes with format helper
5. Click **💾 Save Changes**

### **Using Templates**
1. Click **👁️ View** to preview configuration
2. Click **📋 Copy** to copy JSON to clipboard
3. Navigate to **📤 Upload Page**
4. Paste into profiles configuration
5. Upload your media files

### **Managing Templates**
1. Use **🔍 Search** to find specific templates
2. **🔄 Refresh** to reload from database  
3. **🗑️ Delete** unused templates
4. Monitor template statistics

## 🎯 **Integration**

### **Database Backend**
- **Storage**: PostgreSQL with ConfigTemplateCRUD
- **API Endpoints**: `/config-templates` REST API
- **Real-time**: Direct database operations
- **Persistence**: All changes saved immediately

### **Upload Integration**
- **Template Loading**: Direct import to Upload page
- **Profile Manager**: Works alongside existing tools
- **Consistency**: Same data across all interfaces

## 📊 **Benefits**

### **For Users**
✅ **Visual Management**: Easy template browsing and editing  
✅ **No JSON Errors**: Built-in validation and formatting  
✅ **Quick Access**: Search and filter capabilities  
✅ **Safe Operations**: Confirmation dialogs prevent mistakes  

### **For Developers**
✅ **Database Driven**: No hardcoded configurations  
✅ **REST API**: Standard CRUD operations  
✅ **Consistent UI**: Matches system design patterns  
✅ **Extensible**: Easy to add new features  

### **For Operations**
✅ **Centralized Management**: Single source of truth  
✅ **Audit Trail**: Creation and modification timestamps  
✅ **Backup Ready**: Database-stored configurations  
✅ **Scalable**: Handles unlimited templates  

## 🔗 **Related Pages**

- **📤 Upload**: Use templates for media transcoding
- **🔧 Profile Manager**: Alternative profile selection interface  
- **📊 Results**: View transcoding results from template usage

---

The Config Templates Manager provides a complete solution for managing transcode configurations with a user-friendly interface, robust validation, and seamless integration with the existing transcode system! 🎉