"""
Mobile-optimized profile system for video/image transcoding
Hệ thống profiles tối ưu cho mobile devices với bandwidth khác nhau
"""

import logging
import subprocess
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    """Loại thiết bị mobile"""

    LOW_END = "low_end"  # Máy yếu, mạng chậm
    MID_RANGE = "mid_range"  # Máy trung bình, mạng ổn
    HIGH_END = "high_end"  # Máy mạnh, mạng nhanh
    PREMIUM = "premium"  # Máy cao cấp, mạng rất nhanh


class MediaType(str, Enum):
    """Loại media đầu vào"""

    VIDEO = "video"
    IMAGE = "image"


class ProfileType(str, Enum):
    """Loại profile output"""

    MAIN_VIDEO = "main_video"  # Video chính (giữ nguyên độ dài)
    PREVIEW_VIDEO = "preview_video"  # Video preview (ngắn, không âm thanh)
    THUMBNAIL_IMAGE = "thumbnail_image"  # Ảnh thumbnail
    OPTIMIZED_IMAGE = "optimized_image"  # Ảnh đã tối ưu


# =============================================================================
# CORE PROFILE CONFIG ATTRIBUTES
# =============================================================================


class VideoConfig(BaseModel):
    """Cấu hình video transcoding"""

    # Video codec
    codec: str = Field(description="Video codec")

    # Resolution (giữ aspect ratio)
    max_width: Optional[int] = Field(default=None, description="Chiều rộng tối đa")
    max_height: Optional[int] = Field(default=None, description="Chiều cao tối đa")

    # Quality control
    crf: Optional[int] = Field(default=None, description="Constant Rate Factor")
    bitrate: Optional[str] = Field(default=None, description="Target bitrate")
    max_bitrate: Optional[str] = Field(default=None, description="Max bitrate")

    # Encoding speed
    preset: str = Field(default="medium", description="Encoding preset")

    # Mobile compatibility
    profile: str = Field(default="main", description="H.264/H.265 profile")
    level: Optional[str] = Field(default=None, description="H.264/H.265 level")

    # Frame rate
    fps: Optional[int] = Field(default=None, description="Target frame rate")
    max_fps: Optional[int] = Field(default=None, description="Maximum frame rate")

    # Audio (for main videos)
    audio_codec: Optional[str] = Field(default=None, description="Audio codec")
    audio_bitrate: Optional[str] = Field(default=None, description="Audio bitrate")

    # Preview-specific options
    duration: Optional[int] = Field(default=None, description="Duration in seconds (for previews)")
    start_time: Optional[int] = Field(default=0, description="Start time in seconds")
    remove_audio: bool = Field(default=False, description="Remove audio track")
    speed: Optional[float] = Field(
        default=None, description="Playback speed (2.0 = 2x faster, 0.5 = 2x slower)"
    )


class ImageConfig(BaseModel):
    """Cấu hình image processing"""

    # Resolution
    max_width: Optional[int] = Field(default=None, description="Chiều rộng tối đa")
    max_height: Optional[int] = Field(default=None, description="Chiều cao tối đa")

    # Quality
    quality: int = Field(default=80, ge=1, le=100, description="Image quality")

    # Format
    format: str = Field(default="jpeg", description="Output format")

    # Processing
    thumbnail_mode: bool = Field(default=False, description="Use thumbnail selection")
    extract_time: Optional[float] = Field(
        default=None, description="Time to extract frame (for video input)"
    )


class ProfileConfig(BaseModel):
    """Complete profile configuration"""

    id: str = Field(description="Profile identifier")
    name: str = Field(description="Human-readable name")
    device_type: DeviceType = Field(description="Target device type")
    profile_type: ProfileType = Field(description="Type of output")

    # Config dựa trên loại output
    video_config: Optional[VideoConfig] = Field(default=None)
    image_config: Optional[ImageConfig] = Field(default=None)

    # Metadata
    description: str = Field(default="", description="Profile description")
    priority: int = Field(default=100, description="Processing priority")


# =============================================================================
# PREDEFINED MOBILE PROFILES
# =============================================================================

# Video profiles cho mobile devices
MOBILE_VIDEO_PROFILES = {
    # Main videos (giữ nguyên độ dài)
    "main_low_240p": ProfileConfig(
        id="main_low_240p",
        name="240p Low-end Mobile",
        device_type=DeviceType.LOW_END,
        profile_type=ProfileType.MAIN_VIDEO,
        video_config=VideoConfig(
            codec="libx264",
            max_height=240,
            crf=30,
            max_bitrate="300k",
            preset="fast",
            profile="baseline",
            level="3.0",
            max_fps=24,
            audio_codec="aac",
            audio_bitrate="64k",
        ),
        description="Cho máy yếu, mạng 2G/3G chậm",
    ),
    "main_mid_360p": ProfileConfig(
        id="main_mid_360p",
        name="360p Mid-range Mobile",
        device_type=DeviceType.MID_RANGE,
        profile_type=ProfileType.MAIN_VIDEO,
        video_config=VideoConfig(
            codec="libx264",
            max_height=360,
            crf=26,
            max_bitrate="600k",
            preset="medium",
            profile="main",
            level="3.1",
            max_fps=30,
            audio_codec="aac",
            audio_bitrate="96k",
        ),
        description="Cho máy trung bình, mạng 3G/4G",
    ),
    "main_high_720p": ProfileConfig(
        id="main_high_720p",
        name="720p High-end Mobile",
        device_type=DeviceType.HIGH_END,
        profile_type=ProfileType.MAIN_VIDEO,
        video_config=VideoConfig(
            codec="libx264",
            max_height=720,
            crf=23,
            max_bitrate="1500k",
            preset="medium",
            profile="high",
            level="4.0",
            max_fps=30,
            audio_codec="aac",
            audio_bitrate="128k",
        ),
        description="Cho máy mạnh, mạng 4G/5G",
    ),
    "main_premium_1080p": ProfileConfig(
        id="main_premium_1080p",
        name="1080p Premium Mobile",
        device_type=DeviceType.PREMIUM,
        profile_type=ProfileType.MAIN_VIDEO,
        video_config=VideoConfig(
            codec="libx264",
            max_height=1080,
            crf=20,
            max_bitrate="3000k",
            preset="slow",
            profile="high",
            level="4.1",
            max_fps=60,
            audio_codec="aac",
            audio_bitrate="192k",
        ),
        description="Cho máy cao cấp, mạng 5G",
    ),
    # GPU-accelerated profiles
    "main_gpu_720p_h264": ProfileConfig(
        id="main_gpu_720p_h264",
        name="720p GPU H.264",
        device_type=DeviceType.HIGH_END,
        profile_type=ProfileType.MAIN_VIDEO,
        video_config=VideoConfig(
            codec="h264_nvenc",
            max_height=720,
            crf=23,
            max_bitrate="1500k",
            preset="medium",
            profile="high",
            level="4.0",
            max_fps=30,
            audio_codec="aac",
            audio_bitrate="128k",
        ),
        description="GPU-accelerated H.264 cho máy có NVIDIA GPU",
    ),
    "main_gpu_1080p_h264": ProfileConfig(
        id="main_gpu_1080p_h264",
        name="1080p GPU H.264",
        device_type=DeviceType.PREMIUM,
        profile_type=ProfileType.MAIN_VIDEO,
        video_config=VideoConfig(
            codec="h264_nvenc",
            max_height=1080,
            crf=20,
            max_bitrate="3000k",
            preset="medium",
            profile="high",
            level="4.1",
            max_fps=60,
            audio_codec="aac",
            audio_bitrate="192k",
        ),
        description="GPU-accelerated H.264 1080p cho server có GPU",
    ),
    "main_gpu_720p_h265": ProfileConfig(
        id="main_gpu_720p_h265",
        name="720p GPU H.265",
        device_type=DeviceType.HIGH_END,
        profile_type=ProfileType.MAIN_VIDEO,
        video_config=VideoConfig(
            codec="h265_nvenc",
            max_height=720,
            crf=25,
            max_bitrate="1000k",
            preset="medium",
            profile="main",
            level="4.0",
            max_fps=30,
            audio_codec="aac",
            audio_bitrate="128k",
        ),
        description="GPU-accelerated H.265 cho bandwidth thấp",
    ),
    "main_gpu_1080p_h265": ProfileConfig(
        id="main_gpu_1080p_h265",
        name="1080p GPU H.265",
        device_type=DeviceType.PREMIUM,
        profile_type=ProfileType.MAIN_VIDEO,
        video_config=VideoConfig(
            codec="h265_nvenc",
            max_height=1080,
            crf=22,
            max_bitrate="2000k",
            preset="medium",
            profile="main",
            level="4.1",
            max_fps=60,
            audio_codec="aac",
            audio_bitrate="192k",
        ),
        description="GPU-accelerated H.265 1080p cho chất lượng cao",
    ),
}

# Preview video profiles (ngắn, không âm thanh)
PREVIEW_VIDEO_PROFILES = {
    "preview_low_240p": ProfileConfig(
        id="preview_low_240p",
        name="240p Preview Low-end",
        device_type=DeviceType.LOW_END,
        profile_type=ProfileType.PREVIEW_VIDEO,
        video_config=VideoConfig(
            codec="libx264",
            max_height=240,
            crf=32,
            preset="ultrafast",
            profile="baseline",
            max_fps=15,
            duration=3,  # 3 giây
            remove_audio=True,
        ),
        description="Preview 3s cho máy yếu",
    ),
    "preview_mid_360p": ProfileConfig(
        id="preview_mid_360p",
        name="360p Preview Mid-range",
        device_type=DeviceType.MID_RANGE,
        profile_type=ProfileType.PREVIEW_VIDEO,
        video_config=VideoConfig(
            codec="libx264",
            max_height=360,
            crf=28,
            preset="fast",
            profile="main",
            max_fps=20,
            duration=5,  # 5 giây
            remove_audio=True,
        ),
        description="Preview 5s cho máy trung bình",
    ),
    "preview_high_720p": ProfileConfig(
        id="preview_high_720p",
        name="720p Preview High-end",
        device_type=DeviceType.HIGH_END,
        profile_type=ProfileType.PREVIEW_VIDEO,
        video_config=VideoConfig(
            codec="libx264",
            max_height=720,
            crf=25,
            preset="medium",
            profile="high",
            max_fps=30,
            duration=8,  # 8 giây
            remove_audio=True,
        ),
        description="Preview 8s cho máy mạnh",
    ),
    # GPU-accelerated preview profiles
    "preview_gpu_480p": ProfileConfig(
        id="preview_gpu_480p",
        name="480p GPU Preview",
        device_type=DeviceType.HIGH_END,
        profile_type=ProfileType.PREVIEW_VIDEO,
        video_config=VideoConfig(
            codec="h264_nvenc",
            max_height=480,
            crf=26,
            preset="fast",
            profile="main",
            max_fps=24,
            duration=5,  # 5 giây
            remove_audio=True,
        ),
        description="GPU-accelerated preview cho server có GPU",
    ),
    "preview_gpu_720p": ProfileConfig(
        id="preview_gpu_720p",
        name="720p GPU Preview",
        device_type=DeviceType.PREMIUM,
        profile_type=ProfileType.PREVIEW_VIDEO,
        video_config=VideoConfig(
            codec="h264_nvenc",
            max_height=720,
            crf=24,
            preset="fast",
            profile="high",
            max_fps=30,
            duration=8,  # 8 giây
            remove_audio=True,
        ),
        description="GPU-accelerated 720p preview cho performance cao",
    ),
}

# Thumbnail image profiles
THUMBNAIL_IMAGE_PROFILES = {
    "thumb_small": ProfileConfig(
        id="thumb_small",
        name="Small Thumbnail",
        device_type=DeviceType.LOW_END,
        profile_type=ProfileType.THUMBNAIL_IMAGE,
        image_config=ImageConfig(
            max_width=160, max_height=120, quality=70, format="jpeg", thumbnail_mode=True
        ),
        description="Thumbnail nhỏ cho list view",
    ),
    "thumb_medium": ProfileConfig(
        id="thumb_medium",
        name="Medium Thumbnail",
        device_type=DeviceType.MID_RANGE,
        profile_type=ProfileType.THUMBNAIL_IMAGE,
        image_config=ImageConfig(
            max_width=320, max_height=240, quality=75, format="jpeg", thumbnail_mode=True
        ),
        description="Thumbnail trung bình",
    ),
    "thumb_large": ProfileConfig(
        id="thumb_large",
        name="Large Thumbnail",
        device_type=DeviceType.HIGH_END,
        profile_type=ProfileType.THUMBNAIL_IMAGE,
        image_config=ImageConfig(
            max_width=640, max_height=480, quality=80, format="jpeg", thumbnail_mode=True
        ),
        description="Thumbnail lớn cho detail view",
    ),
    "thumb_webp": ProfileConfig(
        id="thumb_webp",
        name="WebP Thumbnail",
        device_type=DeviceType.PREMIUM,
        profile_type=ProfileType.THUMBNAIL_IMAGE,
        image_config=ImageConfig(
            max_width=640, max_height=480, quality=85, format="webp", thumbnail_mode=True
        ),
        description="Thumbnail WebP cho browser hiện đại",
    ),
}

# Image optimization profiles (cho input image)
IMAGE_OPTIMIZATION_PROFILES = {
    "img_mobile_small": ProfileConfig(
        id="img_mobile_small",
        name="Mobile Small Image",
        device_type=DeviceType.LOW_END,
        profile_type=ProfileType.OPTIMIZED_IMAGE,
        image_config=ImageConfig(max_width=480, max_height=360, quality=75, format="jpeg"),
    ),
    "img_mobile_medium": ProfileConfig(
        id="img_mobile_medium",
        name="Mobile Medium Image",
        device_type=DeviceType.MID_RANGE,
        profile_type=ProfileType.OPTIMIZED_IMAGE,
        image_config=ImageConfig(max_width=720, max_height=540, quality=80, format="jpeg"),
    ),
    "img_mobile_large": ProfileConfig(
        id="img_mobile_large",
        name="Mobile Large Image",
        device_type=DeviceType.HIGH_END,
        profile_type=ProfileType.OPTIMIZED_IMAGE,
        image_config=ImageConfig(max_width=1080, max_height=810, quality=85, format="jpeg"),
    ),
    "img_webp_optimized": ProfileConfig(
        id="img_webp_optimized",
        name="WebP Optimized",
        device_type=DeviceType.PREMIUM,
        profile_type=ProfileType.OPTIMIZED_IMAGE,
        image_config=ImageConfig(max_width=1080, max_height=810, quality=90, format="webp"),
    ),
}


# =============================================================================
# PROFILE SETS BY INPUT TYPE
# =============================================================================


def get_profiles_for_video_input() -> List[ProfileConfig]:
    """Trả về tất cả profiles cần thiết cho video input"""
    profiles = []
    profiles.extend(MOBILE_VIDEO_PROFILES.values())
    profiles.extend(PREVIEW_VIDEO_PROFILES.values())
    profiles.extend(THUMBNAIL_IMAGE_PROFILES.values())
    return profiles


def get_profiles_for_image_input() -> List[ProfileConfig]:
    """Trả về tất cả profiles cần thiết cho image input"""
    profiles = []
    profiles.extend(IMAGE_OPTIMIZATION_PROFILES.values())
    return profiles


def get_profiles_by_device_type(
    device_type: DeviceType, media_type: MediaType
) -> List[ProfileConfig]:
    """Trả về profiles phù hợp với device type và media type"""
    if media_type == MediaType.VIDEO:
        all_profiles = get_profiles_for_video_input()
    else:
        all_profiles = get_profiles_for_image_input()

    return [p for p in all_profiles if p.device_type == device_type]


# =============================================================================
# GPU CODEC DETECTION AND FALLBACK
# =============================================================================


def _check_gpu_codec_availability() -> dict:
    """Check which GPU codecs are available in FFmpeg"""
    try:
        result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=10)
        encoders = result.stdout.lower()

        return {
            "h264_nvenc": "h264_nvenc" in encoders,
            "h265_nvenc": "h265_nvenc" in encoders or "hevc_nvenc" in encoders,
            "hevc_nvenc": "hevc_nvenc" in encoders,
        }
    except Exception as e:
        logging.warning(f"Could not check GPU codec availability: {e}")
        return {
            "h264_nvenc": False,
            "h265_nvenc": False,
            "hevc_nvenc": False,
        }


def _get_fallback_codec(gpu_codec: str) -> str:
    """Get CPU fallback codec for GPU codec"""
    fallback_map = {
        "h264_nvenc": "libx264",
        "h265_nvenc": "libx265",
        "hevc_nvenc": "libx265",
    }
    return fallback_map.get(gpu_codec, "libx264")


def _adapt_profile_for_cpu(profile: "ProfileConfig") -> "ProfileConfig":
    """Adapt GPU profile for CPU by changing codec and settings"""
    if not profile.video_config:
        return profile

    # Create a copy of the profile with CPU codec
    video_config = profile.video_config.copy()

    # Change GPU codec to CPU codec
    if video_config.codec in ["h264_nvenc", "h265_nvenc", "hevc_nvenc"]:
        video_config.codec = _get_fallback_codec(video_config.codec)

        # Adjust preset for CPU (GPU presets don't work with CPU)
        preset_map = {
            "slow": "slow",
            "medium": "medium",
            "fast": "fast",
            "hp": "fast",
            "hq": "slow",
            "bd": "slow",
            "ll": "ultrafast",
            "llhq": "fast",
            "llhp": "ultrafast",
        }
        video_config.preset = preset_map.get(video_config.preset, "medium")

    # Create new profile with adapted config
    adapted_profile = profile.copy()
    adapted_profile.video_config = video_config
    adapted_profile.description += " (CPU fallback)"

    return adapted_profile


# =============================================================================
# FFMPEG COMMAND BUILDER
# =============================================================================


def _ensure_even_dimensions(width: int, height: int) -> tuple[int, int]:
    """Ensure dimensions are even numbers for H.264 encoder compatibility"""
    # H.264 encoder requires even dimensions
    # Round up to next even number using bitwise operation
    even_width = (width + 1) & ~1
    even_height = (height + 1) & ~1
    return even_width, even_height


def _parse_bitrate_to_kbps(bitrate_str: str) -> int:
    """Parse bitrate string to kbps value (handles 'k', 'M' suffixes)"""
    bitrate_str = bitrate_str.lower()
    if bitrate_str.endswith("m"):
        # Convert M to k (multiply by 1000)
        return int(float(bitrate_str.rstrip("m")) * 1000)
    elif bitrate_str.endswith("k"):
        # Already in k format
        return int(float(bitrate_str.rstrip("k")))
    else:
        # Assume it's in bits per second, convert to k
        return int(float(bitrate_str) / 1000)


def _create_fps_filter(max_fps: int) -> str:
    """Create FPS filter compatible with older FFmpeg versions"""
    # For older FFmpeg, use simple fps filter
    # For newer FFmpeg, we could use more complex expressions
    return f"fps={max_fps}"


def build_ffmpeg_args(
    profile: ProfileConfig, keep_aspect_ratio: bool = True, check_gpu_availability: bool = True
) -> List[str]:
    """Build FFmpeg arguments from profile config with GPU codec fallback"""
    args = []

    if profile.video_config:
        # Check GPU codec availability and fallback if needed
        if check_gpu_availability and profile.video_config.codec in [
            "h264_nvenc",
            "h265_nvenc",
            "hevc_nvenc",
        ]:
            gpu_codecs = _check_gpu_codec_availability()
            if not gpu_codecs.get(profile.video_config.codec, False):
                logging.warning(
                    f"GPU codec {
                        profile.video_config.codec} not available, falling back to CPU"
                )
                adapted_profile = _adapt_profile_for_cpu(profile)
                return _build_video_args(adapted_profile.video_config, keep_aspect_ratio)

        return _build_video_args(profile.video_config, keep_aspect_ratio)
    elif profile.image_config:
        return _build_image_args(profile.image_config, keep_aspect_ratio)

    return args


def _build_video_args(config: VideoConfig, keep_aspect_ratio: bool = True) -> List[str]:
    """Build video transcoding arguments"""
    args = []

    # Video filters
    filters = []

    # Speed adjustment (before other filters)
    if hasattr(config, "speed") and config.speed and config.speed != 1.0:
        # Use setpts filter to change playback speed
        # For 2x speed: setpts=0.5*PTS (inverse relationship)
        pts_multiplier = 1.0 / config.speed
        filters.append(f"setpts={pts_multiplier}*PTS")

    # Scaling with aspect ratio preservation
    if config.max_width or config.max_height:
        if keep_aspect_ratio:
            if config.max_width and config.max_height:
                # Use aspect ratio scaling first, then force even dimensions
                even_width, even_height = _ensure_even_dimensions(
                    config.max_width, config.max_height
                )
                scale = f"scale={even_width}:{even_height}:force_original_aspect_ratio=decrease"
                # Add a second filter to ensure final dimensions are even
                filters.append(scale)
                # Force even dimensions
                filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
            elif config.max_width:
                even_width, _ = _ensure_even_dimensions(config.max_width, 0)
                scale = f"scale={even_width}:-2"  # -2 ensures even height
                filters.append(scale)
                # Force even dimensions
                filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
            else:
                _, even_height = _ensure_even_dimensions(0, config.max_height)
                scale = f"scale=-2:{even_height}"  # -2 ensures even width
                filters.append(scale)
                # Force even dimensions
                filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
        else:
            # For fixed scaling, also ensure even dimensions
            width = config.max_width or -1
            height = config.max_height or -1
            if width > 0 and height > 0:
                even_width, even_height = _ensure_even_dimensions(width, height)
                scale = f"scale={even_width}:{even_height}"
                filters.append(scale)
            elif width > 0:
                even_width, _ = _ensure_even_dimensions(width, 0)
                scale = f"scale={even_width}:-2"
                filters.append(scale)
                # Force even dimensions
                filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
            elif height > 0:
                _, even_height = _ensure_even_dimensions(0, height)
                scale = f"scale=-2:{even_height}"
                filters.append(scale)
                # Force even dimensions
                filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
            else:
                scale = f"scale={width}:{height}"
                filters.append(scale)

    # Duration and start time for previews
    if config.start_time > 0:
        args.extend(["-ss", str(config.start_time)])

    if config.duration:
        args.extend(["-t", str(config.duration)])

    # Video codec
    args.extend(["-c:v", config.codec])

    # GPU codec optimizations
    is_gpu_codec = config.codec in ["h264_nvenc", "h265_nvenc", "hevc_nvenc"]

    # Quality control
    if config.crf:
        if is_gpu_codec:
            # NVENC uses 'cq' instead of 'crf'
            args.extend(["-cq", str(config.crf)])
        else:
            args.extend(["-crf", str(config.crf)])
    elif config.bitrate:
        args.extend(["-b:v", config.bitrate])

    if config.max_bitrate:
        args.extend(["-maxrate", config.max_bitrate])

        # Calculate bufsize as 2x max_bitrate (FFmpeg best practice)
        bitrate_kbps = _parse_bitrate_to_kbps(config.max_bitrate)
        bufsize = str(bitrate_kbps * 2) + "k"
        args.extend(["-bufsize", bufsize])

    # Encoding preset - GPU codecs have different presets
    if is_gpu_codec:
        # NVENC presets: slow, medium, fast, hp, hq, bd, ll, llhq, llhp,
        # lossless
        nvenc_preset_map = {
            "ultrafast": "fast",
            "superfast": "fast",
            "veryfast": "fast",
            "faster": "fast",
            "fast": "fast",
            "medium": "medium",
            "slow": "slow",
            "slower": "slow",
            "veryslow": "slow",
        }
        nvenc_preset = nvenc_preset_map.get(config.preset, "medium")
        args.extend(["-preset", nvenc_preset])

        # Add GPU-specific optimizations
        args.extend(["-rc", "vbr"])  # Variable bitrate for better quality
        args.extend(["-rc-lookahead", "20"])  # Lookahead for better encoding
    else:
        args.extend(["-preset", config.preset])

    # Profile and level
    if config.profile:
        args.extend(["-profile:v", config.profile])
    if config.level:
        args.extend(["-level", config.level])

    # Frame rate - use output option for better compatibility with older FFmpeg
    if config.fps:
        # Fixed fps
        args.extend(["-r", str(config.fps)])
    elif config.max_fps:
        # Max fps limitation - use output option instead of filter for
        # compatibility
        args.extend(["-r", str(config.max_fps)])

    # Audio
    if config.remove_audio:
        args.extend(["-an"])  # No audio
    elif config.audio_codec:
        args.extend(["-c:a", config.audio_codec])
        if config.audio_bitrate:
            args.extend(["-b:a", config.audio_bitrate])

    # Apply filters
    if filters:
        args.extend(["-vf", ",".join(filters)])

    return args


def _build_image_args(config: ImageConfig, keep_aspect_ratio: bool = True) -> List[str]:
    """Build image processing arguments"""
    args = []

    # Extract single frame
    args.extend(["-vframes", "1"])

    # Video filters
    filters = []

    # Scaling
    if config.max_width or config.max_height:
        if keep_aspect_ratio:
            if config.max_width and config.max_height:
                scale = f"scale={
                    config.max_width}:{
                    config.max_height}:force_original_aspect_ratio=decrease"
            elif config.max_width:
                scale = f"scale={config.max_width}:-1"
            else:
                scale = f"scale=-1:{config.max_height}"
        else:
            scale = f"scale={config.max_width or -1}:{config.max_height or -1}"
        filters.append(scale)

    # Thumbnail selection
    if config.thumbnail_mode:
        filters.append("thumbnail")

    # Extract time for video input
    if config.extract_time:
        args.extend(["-ss", str(config.extract_time)])

    # Apply filters
    if filters:
        args.extend(["-vf", ",".join(filters)])

    # Quality and format
    if config.format == "webp":
        args.extend(["-c:v", "libwebp"])
        args.extend(["-quality", str(config.quality)])
        args.extend(["-f", "webp"])
    elif config.format == "png":
        args.extend(["-f", "png"])
    else:  # jpeg
        # Convert 0-100 to 1-31
        args.extend(["-q:v", str(31 - int(config.quality * 0.3))])
        args.extend(["-f", "image2"])

    return args


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

if __name__ == "__main__":
    # Example: Get all profiles for video input
    video_profiles = get_profiles_for_video_input()
    print(f"Video input cần {len(video_profiles)} profiles")

    # Example: Get profiles for specific device
    low_end_profiles = get_profiles_by_device_type(DeviceType.LOW_END, MediaType.VIDEO)
    print(f"Low-end device cần {len(low_end_profiles)} profiles")

    # Example: Build FFmpeg command
    profile = MOBILE_VIDEO_PROFILES["main_high_720p"]
    ffmpeg_args = build_ffmpeg_args(profile)
    print(f"FFmpeg args: {' '.join(ffmpeg_args)}")
