# WebP Conversion Engine Design

## WebP Configuration Schema
Based on GIF config structure, WebP will have similar parameters optimized for WebP format:

```python
class WebPConfig(BaseModel):
    """Configuration for WebP generation"""
    fps: int = Field(default=10, ge=1, le=30, description="Frames per second for animated WebP")
    width: Optional[int] = Field(default=None, ge=32, le=1920, description="Width in pixels (auto if None)")
    height: Optional[int] = Field(default=None, ge=32, le=1080, description="Height in pixels (auto if None)")
    duration: Optional[float] = Field(default=None, gt=0, description="Duration in seconds (full video if None)")
    start_time: float = Field(default=0, ge=0, description="Start time in seconds")
    quality: int = Field(default=80, ge=0, le=100, description="WebP quality (0=lossy, 100=lossless)")
    lossless: bool = Field(default=False, description="Use lossless WebP compression")
    animated: bool = Field(default=True, description="Create animated WebP (false for single frame)")
    method: int = Field(default=4, ge=0, le=6, description="WebP compression method (0=fast, 6=slowest)")
    loop: int = Field(default=0, description="Loop count (0 = infinite)")
```

## WebP vs GIF Comparison

| Parameter | GIF | WebP | Notes |
|-----------|-----|------|-------|
| fps | ✓ | ✓ | Same implementation |
| dimensions | ✓ | ✓ | Same width/height logic |
| duration/start_time | ✓ | ✓ | Same video segment extraction |
| quality | ✓ (colors/dither) | ✓ (quality/lossless) | WebP has better quality control |
| optimization | ✓ (optimize) | ✓ (method) | WebP has compression methods |
| loop | ✓ | ✓ | Same looping behavior |

## Implementation Strategy

1. Add `OutputType.WEBP` to schemas
2. Create `WebPConfig` class similar to `GifConfig`
3. Add `webp_config` to `TranscodeProfile`
4. Implement `_process_webp()` method in `transcode_worker.py`
5. Add WebP template configurations

## Processing Methods

**Method 1: FFmpeg-based (Recommended)**
- Use FFmpeg's native WebP encoder
- Better performance and quality
- Supports both static and animated WebP
- Hardware acceleration possible

**Method 2: Library-based (Fallback)**  
- Use PIL/Pillow for WebP processing
- Similar to current GIF implementation
- Good compatibility but slower

## WebP Advantages over GIF
- Better compression (25-50% smaller files)
- Better quality at same file size
- Supports both lossy and lossless compression
- True color support (not limited to 256 colors)
- Alpha transparency support