from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class OutputFormat(str, Enum):
    """Supported output formats for UniversalMediaConverter"""

    WEBP = "webp"
    JPG = "jpg"
    JPEG = "jpeg"
    MP4 = "mp4"


class S3OutputConfig(BaseModel):
    """Configuration for S3 output storage"""

    # Core S3 configuration
    bucket: Optional[str] = None  # If None, uses default from settings
    base_path: str = "transcode-outputs"
    folder_structure: str = "{task_id}/profiles/{profile_id}"

    # Face detection specific paths
    face_avatar_path: str = "{task_id}/faces/avatars"
    face_image_path: str = "{task_id}/faces/images"

    # AWS credentials override (optional - falls back to settings)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_endpoint_url: Optional[str] = None
    aws_endpoint_public_url: Optional[str] = None

    # Cleanup configuration
    cleanup_on_task_reset: bool = True
    cleanup_temp_files: bool = True
    cleanup_failed_outputs: bool = False

    # Upload configuration
    upload_timeout: int = 900
    max_retries: int = 3

    @classmethod
    def with_defaults(cls, data: dict, fallback_settings=None):
        """Create S3OutputConfig with fallbacks to environment settings"""
        config_data = {}

        # Core paths
        config_data.update(
            {
                "base_path": data.get("base_path", "transcode-outputs"),
                "folder_structure": data.get("folder_structure", "{task_id}/profiles/{profile_id}"),
                "face_avatar_path": data.get("face_avatar_path", "{task_id}/faces/avatars"),
                "face_image_path": data.get("face_image_path", "{task_id}/faces/images"),
            }
        )

        # AWS credentials
        if fallback_settings:
            config_data.update(
                {
                    "bucket": data.get("bucket")
                              or getattr(fallback_settings, "aws_bucket_name", None),
                    "aws_access_key_id": data.get("aws_access_key_id")
                                         or getattr(fallback_settings, "aws_access_key_id", None),
                    "aws_secret_access_key": data.get("aws_secret_access_key")
                                             or getattr(fallback_settings, "aws_secret_access_key", None),
                    "aws_endpoint_url": data.get("aws_endpoint_url")
                                        or getattr(fallback_settings, "aws_endpoint_url", None),
                    "aws_endpoint_public_url": data.get("aws_endpoint_public_url")
                                               or getattr(fallback_settings, "aws_endpoint_public_url", None),
                }
            )
        else:
            config_data.update(
                {
                    "bucket": data.get("bucket"),
                    "aws_access_key_id": data.get("aws_access_key_id"),
                    "aws_secret_access_key": data.get("aws_secret_access_key"),
                    "aws_endpoint_url": data.get("aws_endpoint_url"),
                    "aws_endpoint_public_url": data.get("aws_endpoint_public_url"),
                }
            )

        # Cleanup and upload settings
        config_data.update(
            {
                "cleanup_on_task_reset": data.get("cleanup_on_task_reset", True),
                "cleanup_temp_files": data.get("cleanup_temp_files", True),
                "cleanup_failed_outputs": data.get("cleanup_failed_outputs", False),
                "upload_timeout": data.get("upload_timeout", 900),
                "max_retries": data.get("max_retries", 3),
            }
        )

        return cls(**config_data)


class UniversalConverterConfig(BaseModel):
    """Configuration parameters for UniversalMediaConverter"""

    # Output format (auto-detected from file extension if not specified)
    output_format: Optional[OutputFormat] = Field(
        default=None, description="Output format (auto-detected if None)"
    )

    # Common settings
    width: Optional[int] = Field(default=None, description="Output width (pixels)")
    height: Optional[int] = Field(default=None, description="Output height (pixels)")
    quality: int = Field(default=85, ge=0, le=100, description="General quality 0-100")

    # Video timing settings
    fps: Optional[float] = Field(default=None, description="Output FPS")
    duration: Optional[float] = Field(default=None, description="Output duration (seconds)")
    start_time: float = Field(default=0, description="Start time (seconds)")
    speed: float = Field(default=1.0, description="Speed multiplier")

    # Image/Video filter settings
    contrast: float = Field(default=1.0, description="Contrast adjustment")
    brightness: float = Field(default=0.0, description="Brightness adjustment")
    saturation: float = Field(default=1.0, description="Saturation adjustment")
    gamma: float = Field(default=1.0, description="Gamma adjustment")
    enable_denoising: bool = Field(default=False, description="Enable denoising")
    enable_sharpening: bool = Field(default=False, description="Enable sharpening")
    auto_filter: bool = Field(default=False, description="Auto filter")

    # WebP-specific settings
    lossless: bool = Field(default=False, description="WebP lossless mode")
    method: Optional[int] = Field(default=4, ge=0, le=6, description="WebP method 0-6")
    preset: str = Field(default="default", description="WebP preset")
    near_lossless: Optional[int] = Field(
        default=None, ge=0, le=100, description="WebP near lossless"
    )
    alpha_quality: int = Field(default=100, description="WebP alpha quality")
    animated: bool = Field(default=True, description="Enable animation for WebP")
    loop: int = Field(default=0, description="WebP loop count (0=infinite)")
    pass_count: int = Field(default=1, description="WebP pass count")
    target_size: Optional[int] = Field(default=None, description="Target size in KB")
    save_frames: bool = Field(default=False, description="Save frames")

    # JPG-specific settings
    jpeg_quality: int = Field(default=90, ge=0, le=100, description="JPEG quality 0-100")
    optimize: bool = Field(default=True, description="Optimize JPEG")
    progressive: bool = Field(default=False, description="Progressive JPEG")

    # MP4-specific settings
    codec: str = Field(default="h264", description="Video codec")
    crf: int = Field(default=23, ge=0, le=51, description="CRF value 0-51 (lower=better)")
    mp4_preset: str = Field(default="medium", description="MP4 preset")
    bitrate: Optional[str] = Field(default=None, description="Video bitrate (e.g., 2M, 5000k)")
    max_bitrate: Optional[str] = Field(default=None, description="Max bitrate")
    buffer_size: Optional[str] = Field(default=None, description="Buffer size")
    profile: str = Field(default="high", description="Video profile")
    level: str = Field(default="4.1", description="Video level")
    pixel_format: str = Field(default="yuv420p", description="Pixel format")

    # Audio settings (MP4)
    audio_codec: str = Field(default="aac", description="Audio codec")
    audio_bitrate: str = Field(default="128k", description="Audio bitrate")
    audio_sample_rate: int = Field(default=44100, description="Audio sample rate")

    # System settings
    two_pass: bool = Field(default=False, description="Two-pass encoding")
    hardware_accel: bool = Field(default=False, description="Hardware acceleration")
    verbose: bool = Field(default=False, description="Verbose output")


class UniversalTranscodeProfile(BaseModel):
    """Profile for UniversalMediaConverter"""

    id_profile: str
    input_type: Optional[str] = Field(
        default=None, description="Input media type filter: 'image' or 'video'"
    )
    output_filename: Optional[str] = Field(
        default=None, description="Custom output filename (without extension)"
    )
    config: UniversalConverterConfig


class UniversalTranscodeConfig(BaseModel):
    """Configuration for UniversalMediaConverter-based transcoding"""

    profiles: List[UniversalTranscodeProfile]
    s3_output_config: S3OutputConfig
    face_detection_config: Optional[Dict] = Field(
        default=None, description="Face detection configuration"
    )


class UniversalTranscodeMessage(BaseModel):
    """Message for UniversalMediaConverter processing"""

    task_id: str
    source_url: Optional[str] = None  # For downloading from URL
    source_path: Optional[str] = None  # For shared volume file path
    profile: UniversalTranscodeProfile
    s3_output_config: S3OutputConfig
    source_key: Optional[str] = None

    def model_post_init(self, __context) -> None:
        """Validate that either source_url or source_path is provided"""
        if not self.source_url and not self.source_path:
            raise ValueError("Either source_url or source_path must be provided")
        if self.source_url and self.source_path:
            raise ValueError("Only one of source_url or source_path should be provided")


class MediaMetadata(BaseModel):
    """Media metadata extracted from files"""

    file_size: Optional[int] = None
    duration: Optional[int] = None  # seconds
    bitrate: Optional[str] = None
    format: Optional[str] = None
    dimensions: Optional[str] = None  # "1920×1080"
    fps: Optional[int] = None
    codec: Optional[str] = None


class UniversalTranscodeResult(BaseModel):
    """Result of Universal transcoding task"""

    task_id: str
    profile_id: str
    status: str  # "completed" or "failed"
    output_urls: Optional[List[str]] = None
    metadata: Optional[List[MediaMetadata]] = None
    error_message: Optional[str] = None
    completed_at: datetime
    input_type: Optional[str] = None
    output_format: Optional[str] = None
    command: Optional[str] = None


class CallbackAuth(BaseModel):
    """Authentication for callback URLs"""

    type: str = Field(description="Auth type: 'bearer', 'basic', 'custom'")
    token: Optional[str] = Field(default=None, description="Bearer token or custom auth value")
    username: Optional[str] = Field(default=None, description="Username for basic auth")
    password: Optional[str] = Field(default=None, description="Password for basic auth")
    headers: Optional[Dict[str, str]] = Field(default=None, description="Custom headers")


# ============ Additional classes merged from schemas.py (v1) ============

class OutputType(str, Enum):
    """Legacy output types from v1"""
    VIDEO = "video"
    IMAGE = "image"
    GIF = "gif"
    WEBP = "webp"


class FaceDetectionConfig(BaseModel):
    """Configuration for face detection"""
    enabled: bool = Field(default=False, description="Enable face detection for this task")
    similarity_threshold: float = Field(
        default=0.6, description="Similarity threshold for face clustering"
    )
    min_faces_in_group: int = Field(default=1, description="Minimum faces required for a group")
    sample_interval: int = Field(default=5, description="Process every Nth frame")
    ignore_frames: List[int] = Field(default=[], description="List of frame numbers to ignore")
    ignore_ranges: List[List[int]] = Field(default=[], description="List of frame ranges to ignore")
    start_frame: int = Field(default=0, description="Frame number to start processing from")
    end_frame: Optional[int] = Field(default=None, description="Frame number to end processing at")
    face_detector_size: str = Field(default="640x640", description="Size for face detector input")
    face_detector_score_threshold: float = Field(
        default=0.5, description="Confidence threshold for detection"
    )
    face_landmarker_score_threshold: float = Field(
        default=0.85, description="Threshold for landmarker"
    )
    iou_threshold: float = Field(default=0.4, description="IOU threshold for NMS")
    min_appearance_ratio: float = Field(
        default=0.25, description="Min ratio of group size to frames"
    )
    min_frontality: float = Field(default=0.2, description="Minimum acceptable frontality")
    avatar_size: int = Field(default=112, description="Size of face avatar")
    avatar_padding: float = Field(default=0.07, description="Padding percentage for face avatar")
    avatar_quality: int = Field(default=85, description="JPEG quality for avatars")
    save_faces: bool = Field(default=True, description="Save face avatars to S3")
    max_workers: int = Field(default=4, description="Maximum worker threads")


class FaceDetectionMessage(BaseModel):
    """Message for face detection tasks"""
    task_id: str
    source_url: Optional[str] = None  # For downloading from URL
    source_path: Optional[str] = None  # For shared volume file path
    config: Dict

    def model_post_init(self, __context) -> None:
        """Validate that either source_url or source_path is provided"""
        if not self.source_url and not self.source_path:
            raise ValueError("Either source_url or source_path must be provided")
        if self.source_url and self.source_path:
            raise ValueError("Only one of source_url or source_path should be provided")


class UniversalConfigTemplateRequest(BaseModel):
    """Request to create/update Universal Transcode config template (v2)"""
    
    name: str = Field(description="Template name")
    description: Optional[str] = Field(default=None, description="Template description")
    profiles: List[UniversalTranscodeProfile] = Field(description="List of transcode profiles")
    s3_output_config: Optional[S3OutputConfig] = Field(default=None, description="Default S3 output configuration")
    face_detection_config: Optional[Dict] = Field(default=None, description="Default face detection configuration")


class UniversalConfigTemplate(BaseModel):
    """Universal Transcode config template (v2)"""
    
    template_id: str
    name: str
    description: Optional[str] = None
    profiles: List[UniversalTranscodeProfile]
    s3_output_config: Optional[S3OutputConfig] = None
    face_detection_config: Optional[Dict] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class FaceDetectionResult(BaseModel):
    """Result of face detection task"""
    task_id: str
    status: str
    faces: Optional[List[Dict]] = None
    is_change_index: Optional[bool] = None
    output_urls: Optional[List[str]] = None
    error_message: Optional[str] = None
    completed_at: datetime


