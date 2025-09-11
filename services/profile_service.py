"""
Profile service for mobile-optimized transcoding
Handles profile detection, selection, and conversion
"""

import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import mimetypes

from mobile_profile_system import (
    ProfileConfig, MediaType, DeviceType, ProfileType,
    get_profiles_for_video_input, get_profiles_for_image_input,
    get_profiles_by_device_type, build_ffmpeg_args,
    MOBILE_VIDEO_PROFILES, PREVIEW_VIDEO_PROFILES, 
    THUMBNAIL_IMAGE_PROFILES, IMAGE_OPTIMIZATION_PROFILES
)
from models.schemas import TranscodeProfile, OutputType

logger = logging.getLogger(__name__)

class ProfileService:
    """Service for handling mobile profile selection and conversion"""
    
    @staticmethod
    def detect_media_type(filename: str, content_type: Optional[str] = None) -> MediaType:
        """Detect media type from filename or content type"""
        # Use content type if available
        if content_type:
            if content_type.startswith('video/'):
                return MediaType.VIDEO
            elif content_type.startswith('image/'):
                return MediaType.IMAGE
        
        # Fallback to file extension
        ext = Path(filename).suffix.lower()
        
        video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.3gp', '.flv'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
        
        if ext in video_extensions:
            return MediaType.VIDEO
        elif ext in image_extensions:
            return MediaType.IMAGE
        
        # Default to video if unknown
        logger.warning(f"Unknown media type for {filename}, defaulting to VIDEO")
        return MediaType.VIDEO
    
    @staticmethod
    def get_default_profiles(media_type: MediaType) -> List[ProfileConfig]:
        """Get default profile set based on media type"""
        if media_type == MediaType.VIDEO:
            return get_profiles_for_video_input()
        else:
            return get_profiles_for_image_input()
    
    @staticmethod
    def get_profiles_by_device(device_type: DeviceType, media_type: MediaType) -> List[ProfileConfig]:
        """Get profiles filtered by device type"""
        return get_profiles_by_device_type(device_type, media_type)
    
    @staticmethod
    def get_custom_profile_set(
        include_main: bool = True,
        include_preview: bool = True, 
        include_thumbnails: bool = True,
        device_types: Optional[List[DeviceType]] = None,
        media_type: MediaType = MediaType.VIDEO
    ) -> List[ProfileConfig]:
        """Get custom profile set based on requirements"""
        profiles = []
        
        # Filter by device types if specified
        target_devices = device_types or [DeviceType.LOW_END, DeviceType.MID_RANGE, DeviceType.HIGH_END, DeviceType.PREMIUM]
        
        if media_type == MediaType.VIDEO:
            # Main videos
            if include_main:
                for device in target_devices:
                    main_profiles = [p for p in MOBILE_VIDEO_PROFILES.values() 
                                   if p.device_type == device and p.profile_type == ProfileType.MAIN_VIDEO]
                    profiles.extend(main_profiles)
            
            # Preview videos
            if include_preview:
                for device in target_devices:
                    preview_profiles = [p for p in PREVIEW_VIDEO_PROFILES.values()
                                      if p.device_type == device and p.profile_type == ProfileType.PREVIEW_VIDEO]
                    profiles.extend(preview_profiles)
            
            # Thumbnail images
            if include_thumbnails:
                for device in target_devices:
                    thumb_profiles = [p for p in THUMBNAIL_IMAGE_PROFILES.values()
                                    if p.device_type == device and p.profile_type == ProfileType.THUMBNAIL_IMAGE]
                    profiles.extend(thumb_profiles)
        
        else:  # IMAGE
            # Optimized images
            for device in target_devices:
                img_profiles = [p for p in IMAGE_OPTIMIZATION_PROFILES.values()
                              if p.device_type == device and p.profile_type == ProfileType.OPTIMIZED_IMAGE]
                profiles.extend(img_profiles)
        
        return profiles
    
    @staticmethod
    def convert_to_transcode_profiles(profile_configs: List[ProfileConfig]) -> List[TranscodeProfile]:
        """Convert ProfileConfig list to TranscodeProfile list for existing system"""
        transcode_profiles = []
        
        for profile_config in profile_configs:
            try:
                # Build FFmpeg args with GPU codec detection and fallback
                ffmpeg_args = build_ffmpeg_args(profile_config, keep_aspect_ratio=True, check_gpu_availability=True)
                
                # Determine output type
                if profile_config.profile_type in [ProfileType.MAIN_VIDEO, ProfileType.PREVIEW_VIDEO]:
                    output_type = OutputType.VIDEO
                elif profile_config.profile_type in [ProfileType.THUMBNAIL_IMAGE, ProfileType.OPTIMIZED_IMAGE]:
                    output_type = OutputType.IMAGE
                else:
                    logger.warning(f"Unknown profile type: {profile_config.profile_type}")
                    continue
                
                # Create TranscodeProfile using config instead of ffmpeg_args
                from models.schemas import VideoConfig as SchemaVideoConfig, ImageConfig as SchemaImageConfig
                
                if output_type == OutputType.VIDEO and profile_config.video_config:
                    transcode_profile = TranscodeProfile(
                        id_profile=profile_config.id,
                        output_type=output_type,
                        video_config=SchemaVideoConfig(**profile_config.video_config.model_dump())
                    )
                elif output_type == OutputType.IMAGE and profile_config.image_config:
                    transcode_profile = TranscodeProfile(
                        id_profile=profile_config.id,
                        output_type=output_type,
                        image_config=SchemaImageConfig(**profile_config.image_config.model_dump())
                    )
                else:
                    # Fallback to ffmpeg_args for backward compatibility
                    transcode_profile = TranscodeProfile(
                        id_profile=profile_config.id,
                        output_type=output_type,
                        ffmpeg_args=ffmpeg_args
                    )
                
                transcode_profiles.append(transcode_profile)
                logger.debug(f"Converted profile {profile_config.id}: {output_type} - {' '.join(ffmpeg_args[:5])}...")
                
            except Exception as e:
                logger.error(f"Error converting profile {profile_config.id}: {e}")
                continue
        
        return transcode_profiles
    
    @staticmethod
    def get_profile_summary(profiles: List[ProfileConfig]) -> Dict[str, Any]:
        """Get summary of profiles for logging/debugging"""
        summary = {
            "total_profiles": len(profiles),
            "by_type": {},
            "by_device": {},
            "profile_list": []
        }
        
        for profile in profiles:
            # Count by type
            profile_type = profile.profile_type.value
            summary["by_type"][profile_type] = summary["by_type"].get(profile_type, 0) + 1
            
            # Count by device
            device_type = profile.device_type.value
            summary["by_device"][device_type] = summary["by_device"].get(device_type, 0) + 1
            
            # Profile details
            summary["profile_list"].append({
                "id": profile.id,
                "name": profile.name,
                "type": profile_type,
                "device": device_type,
                "description": profile.description
            })
        
        return summary

# Global instance
profile_service = ProfileService()

# =============================================================================
# PRESET CONFIGURATIONS
# =============================================================================

# Preset configurations for common use cases
PRESET_CONFIGS = {
    "mobile_complete": {
        "description": "Complete mobile workflow - all profiles for all devices",
        "video": {
            "include_main": True,
            "include_preview": True,
            "include_thumbnails": True,
            "device_types": [DeviceType.LOW_END, DeviceType.MID_RANGE, DeviceType.HIGH_END, DeviceType.PREMIUM]
        },
        "image": {
            "device_types": [DeviceType.LOW_END, DeviceType.MID_RANGE, DeviceType.HIGH_END, DeviceType.PREMIUM]
        }
    },
    
    "mobile_basic": {
        "description": "Basic mobile support - essential profiles only",
        "video": {
            "include_main": True,
            "include_preview": True,
            "include_thumbnails": True,
            "device_types": [DeviceType.LOW_END, DeviceType.MID_RANGE, DeviceType.HIGH_END]
        },
        "image": {
            "device_types": [DeviceType.LOW_END, DeviceType.MID_RANGE, DeviceType.HIGH_END]
        }
    },
    
    "mobile_premium_only": {
        "description": "Premium devices only - high quality profiles",
        "video": {
            "include_main": True,
            "include_preview": True,
            "include_thumbnails": True,
            "device_types": [DeviceType.HIGH_END, DeviceType.PREMIUM]
        },
        "image": {
            "device_types": [DeviceType.HIGH_END, DeviceType.PREMIUM]
        }
    },
    
    "thumbnails_only": {
        "description": "Thumbnails only - for preview generation",
        "video": {
            "include_main": False,
            "include_preview": True,
            "include_thumbnails": True,
            "device_types": [DeviceType.LOW_END, DeviceType.MID_RANGE, DeviceType.HIGH_END]
        },
        "image": {
            "device_types": [DeviceType.LOW_END, DeviceType.MID_RANGE]
        }
    }
}

def get_preset_profiles(preset_name: str, media_type: MediaType) -> List[ProfileConfig]:
    """Get profiles for a preset configuration"""
    if preset_name not in PRESET_CONFIGS:
        raise ValueError(f"Unknown preset: {preset_name}")
    
    preset = PRESET_CONFIGS[preset_name]
    
    if media_type == MediaType.VIDEO:
        video_config = preset["video"]
        return profile_service.get_custom_profile_set(
            include_main=video_config.get("include_main", True),
            include_preview=video_config.get("include_preview", True),
            include_thumbnails=video_config.get("include_thumbnails", True),
            device_types=video_config.get("device_types"),
            media_type=media_type
        )
    else:
        image_config = preset["image"]
        return profile_service.get_custom_profile_set(
            device_types=image_config.get("device_types"),
            media_type=media_type
        )