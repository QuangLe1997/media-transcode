# Project Cleanup Analysis

## 🗑️ Files Recommended for Deletion

### 1. **Empty Docker Files** (0 bytes)
```bash
rm Dockerfile.consumer Dockerfile.gpu Dockerfile.gpu-simple
```
- `Dockerfile.consumer` - empty file
- `Dockerfile.gpu` - empty file  
- `Dockerfile.gpu-simple` - empty file

Keep: `Dockerfile`, `Dockerfile.optimized`, `Dockerfile.simple` (have content)

### 2. **Test Files** (Development/Testing only)
```bash
rm test_*.py webp_*.py
```
- `test_face_detection_api.py` - API testing
- `test_face_detection_filtering.py` - Face detection tests
- `test_full_flow.py` - Full workflow tests
- `test_json_format.py` - JSON validation tests
- `test_s3_logging.py` - S3 logging tests
- `test_webp_conversion.py` - WebP conversion tests ⚠️ **Keep for reference**
- `test_webp_simple.py` - Simple WebP tests
- `webp_direct_test.py` - Direct WebP tests
- `webp_quick_test.py` - Quick WebP tests
- `webp_config_design.md` - Design docs ⚠️ **Keep for reference**

### 3. **Utility/Cleanup Scripts** (Operational tools)
```bash
# Keep these for maintenance but can archive
```
- `quick_clean.py` - Quick cleanup utility
- `quick_clean_markers.py` - S3 markers cleanup
- `clean_delete_markers.py` - Delete markers cleanup
- `s3_bulk_clean.py` - Bulk S3 cleanup
- `s3_deep_clean.py` - Deep S3 cleanup
- `s3_deep_folder_clean.py` - Folder cleanup
- `s3_turbo_delete.py` - Fast S3 deletion
- `s3_ultra_delete.py` - Ultra fast deletion
- `s3_config_examples.py` - S3 config examples

### 4. **Debug/Check Scripts** (Diagnostic tools)
```bash
# Keep for debugging but can archive
```
- `check_db_schema.py` - Database schema validation
- `check_folder_status.py` - Folder status checker
- `check_server_logs.py` - Log analyzer
- `check_face_worker_logs.sh` - Face worker logs
- `explain_face_metrics.py` - Face metrics explanation

### 5. **Temporary/Generated Files**
```bash
rm .DS_Store celery.log transcode_tasks.db
```
- `.DS_Store` - macOS system file
- `celery.log` - Log file (77KB)
- `transcode_tasks.db` - SQLite database (24KB)

### 6. **Migration Scripts** (One-time use)
```bash
# Archive after successful migration
```
- `add_face_detection_migration.py` - Face detection migration
- `add_pubsub_topic_migration.py` - PubSub migration
- `create_config_templates_table.py` - Config table creation
- `run_migration.py` - General migration runner

### 7. **Development Sample Data**
```bash
rm -rf sample_media_test/ uploads/
```
- `sample_media_test/` - Test media files
- `uploads/` - Upload directory with development files
- `instance/` - Flask instance folder
- `logs/` - Log directory

### 8. **Unused Configuration Files**
- `thumb_cfg.json` - Thumbnail config (290 bytes)
- `request.txt` - Request examples

## ✅ Files to Keep (Core System)

### Core Application
- `app.py` - Main Flask application
- `main.py` - Alternative entry point
- `config.py` - Configuration management
- `logging_config.py` - Logging setup
- `mobile_profile_system.py` - Profile system
- `run.py` - Application runner
- `run_consumer.py` - Consumer runner

### API & Services
- `api/` - REST API endpoints
- `services/` - Core business logic
- `database/` - Database models
- `tasks/` - Celery tasks
- `consumer/` - Background workers

### Frontend & Templates
- `frontend/` - React frontend
- `templates/` - Jinja2 templates
- `static/` - CSS/JS assets

### Configuration & Deployment
- `docker-compose.yml` - Docker orchestration
- `deploy.sh` - Deployment script
- `requirements*.txt` - Python dependencies
- `.env.example` - Environment template
- `CLAUDE.md` - Project documentation

### Documentation
- `README.md` - Main documentation
- `*_GUIDE.md` - Setup guides
- `*_README.md` - Component docs

## 🔧 Cleanup Commands

### Safe Cleanup (Recommended)
```bash
# Remove empty Docker files
rm Dockerfile.consumer Dockerfile.gpu Dockerfile.gpu-simple

# Remove temporary files
rm .DS_Store celery.log transcode_tasks.db thumb_cfg.json request.txt

# Archive test files (don't delete yet)
mkdir archive/
mv test_*.py webp_*.py archive/
mv quick_clean*.py clean_delete_markers.py archive/
mv s3_*clean*.py s3_*delete*.py archive/
mv check_*.py explain_*.py archive/
mv add_*_migration.py create_config_templates_table.py archive/
```

### Aggressive Cleanup (After confirming not needed)
```bash
# Remove development data
rm -rf sample_media_test/ uploads/ instance/ logs/

# Remove archived files
rm -rf archive/
```

## 📊 Space Savings
- **Empty files**: ~5 files
- **Test files**: ~10 files (~100KB)
- **Utility scripts**: ~15 files (~300KB)  
- **Temp data**: ~3 files (~100KB)
- **Sample data**: ~folders with media files

**Total estimated savings**: 500KB+ code files, potentially GB in media data

## ⚠️ Important Notes
1. **Test files** - Keep `test_webp_conversion.py` as reference for WebP implementation
2. **Migration scripts** - Archive but don't delete until migrations confirmed working
3. **Cleanup scripts** - Useful for maintenance, consider archiving vs deleting
4. **Sample data** - Remove after confirming production deployment works
5. **Logs/DB** - Can be regenerated, safe to remove in development