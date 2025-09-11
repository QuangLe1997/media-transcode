from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OutputType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    GIF = "gif"
    WEBP = "webp"


class S3OutputConfig(BaseModel):
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
    cleanup_on_task_reset: bool = True  # Clean up S3 files when task is reset
    cleanup_temp_files: bool = True     # Clean up temporary files after processing
    cleanup_failed_outputs: bool = False  # Clean up outputs from failed tasks
    
    # Upload configuration
    upload_timeout: int = 900  # Upload timeout in seconds (15 minutes)
    max_retries: int = 3       # Max retry attempts for uploads
    
    @classmethod
    def with_defaults(cls, data: dict, fallback_settings=None):
        """Create S3OutputConfig with fallbacks to environment settings"""
        # Merge provided data with defaults
        config_data = {}
        
        # Core paths (always from message if provided)
        config_data.update({
            'base_path': data.get('base_path', 'transcode-outputs'),
            'folder_structure': data.get('folder_structure', '{task_id}/profiles/{profile_id}'),
            'face_avatar_path': data.get('face_avatar_path', '{task_id}/faces/avatars'),
            'face_image_path': data.get('face_image_path', '{task_id}/faces/images'),
        })
        
        # AWS credentials (use message values if provided, otherwise fall back to settings)
        if fallback_settings:
            config_data.update({
                'bucket': data.get('bucket') or getattr(fallback_settings, 'aws_bucket_name', None),
                'aws_access_key_id': data.get('aws_access_key_id') or getattr(fallback_settings, 'aws_access_key_id', None),
                'aws_secret_access_key': data.get('aws_secret_access_key') or getattr(fallback_settings, 'aws_secret_access_key', None),
                'aws_endpoint_url': data.get('aws_endpoint_url') or getattr(fallback_settings, 'aws_endpoint_url', None),
                'aws_endpoint_public_url': data.get('aws_endpoint_public_url') or getattr(fallback_settings, 'aws_endpoint_public_url', None),
            })
        else:
            # Just use what's in the message
            config_data.update({
                'bucket': data.get('bucket'),
                'aws_access_key_id': data.get('aws_access_key_id'),
                'aws_secret_access_key': data.get('aws_secret_access_key'),
                'aws_endpoint_url': data.get('aws_endpoint_url'),
                'aws_endpoint_public_url': data.get('aws_endpoint_public_url'),
            })
        
        # Cleanup and upload settings (with sensible defaults)
        config_data.update({
            'cleanup_on_task_reset': data.get('cleanup_on_task_reset', True),
            'cleanup_temp_files': data.get('cleanup_temp_files', True),
            'cleanup_failed_outputs': data.get('cleanup_failed_outputs', False),
            'upload_timeout': data.get('upload_timeout', 900),
            'max_retries': data.get('max_retries', 3),
        })
        
        return cls(**config_data)


class VideoConfig(BaseModel):
    """Configuration for video transcoding"""
    # Video codec
    codec: str = Field(description="Video codec")
    
    # Resolution (giữ aspect ratio)
    max_width: Optional[int] = Field(default=None, description="Chiều rộng tối đa")
    max_height: Optional[int] = Field(default=None, description="Chiều cao tối đa")
    
    @model_validator(mode='after')
    def ensure_even_dimensions(self):
        """Ensure dimensions are even numbers for H.264 encoder compatibility"""
        if self.max_width is not None and self.max_width > 0:
            self.max_width = (self.max_width + 1) & ~1  # Round up to next even number
        if self.max_height is not None and self.max_height > 0:
            self.max_height = (self.max_height + 1) & ~1  # Round up to next even number
        return self
    
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
    speed: Optional[float] = Field(default=None, description="Playback speed (2.0 = 2x faster, 0.5 = 2x slower)")


class ImageConfig(BaseModel):
    """Configuration for image processing"""
    # Resolution
    max_width: Optional[int] = Field(default=None, description="Chiều rộng tối đa")
    max_height: Optional[int] = Field(default=None, description="Chiều cao tối đa")
    
    # Quality
    quality: int = Field(default=80, ge=1, le=100, description="Image quality")
    
    # Format
    format: str = Field(default="jpeg", description="Output format")
    
    # Processing
    thumbnail_mode: bool = Field(default=False, description="Use thumbnail selection")
    extract_time: Optional[float] = Field(default=None, description="Time to extract frame (for video input)")


class GifConfig(BaseModel):
    """Configuration for GIF generation"""
    fps: int = Field(default=10, ge=1, le=30, description="Frames per second for GIF")
    width: Optional[int] = Field(default=None, ge=32, le=1920, description="Width in pixels (auto if None)")
    height: Optional[int] = Field(default=None, ge=32, le=1080, description="Height in pixels (auto if None)")
    duration: Optional[float] = Field(default=None, gt=0, description="Duration in seconds (full video if None)")
    start_time: float = Field(default=0, ge=0, description="Start time in seconds")
    quality: int = Field(default=80, ge=1, le=100, description="Quality percentage")
    colors: int = Field(default=256, ge=2, le=256, description="Number of colors in palette")
    dither: bool = Field(default=True, description="Enable dithering for better quality")
    optimize: bool = Field(default=True, description="Optimize GIF file size")
    loop: int = Field(default=0, description="Loop count (0 = infinite)")
    
    @model_validator(mode='after')
    def ensure_even_dimensions(self):
        """Ensure dimensions are even numbers for video processing compatibility"""
        if self.width is not None and self.width > 0:
            self.width = (self.width + 1) & ~1  # Round up to next even number
        if self.height is not None and self.height > 0:
            self.height = (self.height + 1) & ~1  # Round up to next even number
        return self


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
    
    @model_validator(mode='after')
    def ensure_even_dimensions(self):
        """Ensure dimensions are even numbers for video processing compatibility"""
        if self.width is not None and self.width > 0:
            self.width = (self.width + 1) & ~1  # Round up to next even number
        if self.height is not None and self.height > 0:
            self.height = (self.height + 1) & ~1  # Round up to next even number
        return self


class TranscodeProfile(BaseModel):
    id_profile: str
    output_type: OutputType
    input_type: Optional[str] = Field(default=None, description="Input media type filter: 'image' or 'video'")
    ffmpeg_args: Optional[List[str]] = Field(default=None, description="FFmpeg arguments for video/image output")
    video_config: Optional[VideoConfig] = Field(default=None, description="Video configuration (alternative to ffmpeg_args)")
    image_config: Optional[ImageConfig] = Field(default=None, description="Image configuration (alternative to ffmpeg_args)")
    gif_config: Optional[GifConfig] = Field(default=None, description="GIF-specific configuration")
    webp_config: Optional[WebPConfig] = Field(default=None, description="WebP-specific configuration")

    @model_validator(mode='after')
    def validate_profile_configs(self):
        """Validate that the appropriate config is provided based on output type"""
        if self.output_type == OutputType.VIDEO:
            # For VIDEO: either ffmpeg_args OR video_config is required
            if not self.ffmpeg_args and not self.video_config:
                raise ValueError("Either ffmpeg_args or video_config is required for VIDEO output")
            if self.ffmpeg_args and self.video_config:
                raise ValueError("Cannot use both ffmpeg_args and video_config. Choose one.")
            if self.image_config:
                raise ValueError("image_config cannot be used with VIDEO output")
                
        elif self.output_type == OutputType.IMAGE:
            # For IMAGE: either ffmpeg_args OR image_config is required
            if not self.ffmpeg_args and not self.image_config:
                raise ValueError("Either ffmpeg_args or image_config is required for IMAGE output")
            if self.ffmpeg_args and self.image_config:
                raise ValueError("Cannot use both ffmpeg_args and image_config. Choose one.")
            if self.video_config:
                raise ValueError("video_config cannot be used with IMAGE output")
                
        elif self.output_type == OutputType.GIF:
            # For GIF: only gif_config is allowed
            if not self.gif_config:
                raise ValueError("gif_config is required for GIF output")
            if self.ffmpeg_args:
                raise ValueError("ffmpeg_args should not be used with GIF output, use gif_config instead")
            if self.video_config or self.image_config:
                raise ValueError("video_config and image_config cannot be used with GIF output")
                
        elif self.output_type == OutputType.WEBP:
            # For WEBP: only webp_config is allowed
            if not self.webp_config:
                raise ValueError("webp_config is required for WEBP output")
            if self.ffmpeg_args:
                raise ValueError("ffmpeg_args should not be used with WEBP output, use webp_config instead")
            if self.video_config or self.image_config or self.gif_config:
                raise ValueError("video_config, image_config, and gif_config cannot be used with WEBP output")
        
        return self


class FaceDetectionConfig(BaseModel):
    """Configuration for face detection"""
    enabled: bool = Field(default=False, description="Enable face detection for this task")
    similarity_threshold: float = Field(default=0.6, description="Similarity threshold for face clustering")
    min_faces_in_group: int = Field(default=1, description="Minimum faces required for a group")
    sample_interval: int = Field(default=5, description="Process every Nth frame")
    ignore_frames: List[int] = Field(default=[], description="List of frame numbers to ignore")
    ignore_ranges: List[List[int]] = Field(default=[], description="List of frame ranges to ignore")
    start_frame: int = Field(default=0, description="Frame number to start processing from")
    end_frame: Optional[int] = Field(default=None, description="Frame number to end processing at")
    face_detector_size: str = Field(default="640x640", description="Size for face detector input")
    face_detector_score_threshold: float = Field(default=0.5, description="Confidence threshold for detection")
    face_landmarker_score_threshold: float = Field(default=0.85, description="Threshold for landmarker")
    iou_threshold: float = Field(default=0.4, description="IOU threshold for NMS")
    min_appearance_ratio: float = Field(default=0.25, description="Min ratio of group size to frames")
    min_frontality: float = Field(default=0.2, description="Minimum acceptable frontality")
    avatar_size: int = Field(default=112, description="Size of face avatar")
    avatar_padding: float = Field(default=0.07, description="Padding percentage for face avatar")
    avatar_quality: int = Field(default=85, description="JPEG quality for avatars")
    save_faces: bool = Field(default=True, description="Save face avatars to S3")
    max_workers: int = Field(default=4, description="Maximum worker threads")


class TranscodeConfig(BaseModel):
    profiles: List[TranscodeProfile]
    s3_output_config: S3OutputConfig
    face_detection_config: Optional[FaceDetectionConfig] = Field(default=None, description="Face detection configuration")


class TranscodeTask(BaseModel):
    task_id: str
    source_url: str
    config: TranscodeConfig
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime
    updated_at: Optional[datetime] = None
    error_message: Optional[str] = None
    outputs: Optional[Dict[str, List[str]]] = None


class TranscodeMessage(BaseModel):
    task_id: str
    source_url: str
    profile: TranscodeProfile
    s3_output_config: S3OutputConfig
    source_key: Optional[str] = None  # Optional for URL inputs


class MediaMetadata(BaseModel):
    """Metadata for media files extracted by consumer"""
    file_size: Optional[int] = None  # File size in bytes
    dimensions: Optional[str] = None  # Format: "1920×1080"
    duration: Optional[int] = None   # Duration in seconds
    fps: Optional[int] = None        # Frames per second
    format: Optional[str] = None     # File format (mp4, jpg, etc.)
    bitrate: Optional[str] = None    # Bitrate for videos


class TranscodeResult(BaseModel):
    task_id: str
    profile_id: str
    status: str
    output_urls: Optional[List[str]] = None
    metadata: Optional[List[MediaMetadata]] = None  # Metadata for each output URL
    error_message: Optional[str] = None
    completed_at: datetime


class CallbackAuth(BaseModel):
    """Authentication for callback requests"""
    type: str  # "bearer", "basic", "header"
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    headers: Optional[Dict[str, str]] = None


class TranscodeRequest(BaseModel):
    """Enhanced transcode request supporting both file upload and URL"""
    config: TranscodeConfig
    callback_url: Optional[str] = None
    callback_auth: Optional[CallbackAuth] = None


class CallbackData(BaseModel):
    """Data sent to callback URL when task completes"""
    task_id: str
    status: TaskStatus
    source_url: str
    outputs: Optional[Dict[str, List[str]]] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: datetime


class FaceDetectionMessage(BaseModel):
    """Message for face detection tasks"""
    task_id: str
    source_url: str
    config: Dict


class FaceDetectionResult(BaseModel):
    """Result of face detection task"""
    task_id: str
    status: str
    faces: Optional[List[Dict]] = None
    is_change_index: Optional[bool] = None
    output_urls: Optional[List[str]] = None
    error_message: Optional[str] = None
    completed_at: datetime


class ConfigTemplate(BaseModel):
    """Config template for reuse"""
    template_id: Optional[str] = None
    name: str
    config: List[TranscodeProfile]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConfigTemplateRequest(BaseModel):
    """Request to create/update config template"""
    name: str
    config: List[TranscodeProfile]


class ConfigTemplateResponse(BaseModel):
    """Response for config template operations"""
    template_id: str
    name: str
    config: List[TranscodeProfile]
    created_at: datetime
    updated_at: Optional[datetime] = None
