"""
Media detection and profile filtering service
"""

import logging
import mimetypes
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from ..models.schemas_v2 import TranscodeProfile

logger = logging.getLogger(__name__)


class MediaDetectionService:
    """Service for detecting media type and filtering appropriate profiles"""

    # Media type mappings
    VIDEO_EXTENSIONS = {
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
        ".webm",
        ".m4v",
        ".3gp",
        ".flv",
        ".wmv",
        ".mpg",
        ".mpeg",
    }
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif", ".svg"}

    VIDEO_MIME_TYPES = {
        "video/mp4",
        "video/avi",
        "video/quicktime",
        "video/x-msvideo",
        "video/webm",
        "video/x-matroska",
        "video/3gpp",
        "video/x-flv",
    }

    IMAGE_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/bmp",
        "image/webp",
        "image/tiff",
        "image/svg+xml",
    }

    @classmethod
    def detect_media_type(
            cls,
            filename: Optional[str] = None,
            content_type: Optional[str] = None,
            url: Optional[str] = None,
    ) -> str:
        """
        Detect media type from filename, content type, or URL

        Args:
            filename: Original filename
            content_type: MIME content type
            url: Media URL

        Returns:
            'image' or 'video'
        """
        logger.debug(
            f"Detecting media type for filename={filename}, content_type={content_type}, url={url}"
        )

        # Try content type first (most reliable)
        if content_type:
            if content_type.lower() in cls.VIDEO_MIME_TYPES:
                logger.info(f"Detected VIDEO from content_type: {content_type}")
                return "video"
            elif content_type.lower() in cls.IMAGE_MIME_TYPES:
                logger.info(f"Detected IMAGE from content_type: {content_type}")
                return "image"

        # Try filename extension
        target_filename = filename or (urlparse(url).path if url else None)
        if target_filename:
            ext = Path(target_filename).suffix.lower()
            if ext in cls.VIDEO_EXTENSIONS:
                logger.info(f"Detected VIDEO from extension: {ext}")
                return "video"
            elif ext in cls.IMAGE_EXTENSIONS:
                logger.info(f"Detected IMAGE from extension: {ext}")
                return "image"

        # Try guessing from URL
        if url:
            guessed_type, _ = mimetypes.guess_type(url)
            if guessed_type:
                if guessed_type.startswith("video/"):
                    logger.info(f"Detected VIDEO from URL guess: {guessed_type}")
                    return "video"
                elif guessed_type.startswith("image/"):
                    logger.info(f"Detected IMAGE from URL guess: {guessed_type}")
                    return "image"

        # Default to video if can't determine
        logger.warning("Could not determine media type, defaulting to VIDEO")
        return "video"

    @classmethod
    def filter_profiles_by_input_type(
            cls, profiles: List[TranscodeProfile], media_type: str
    ) -> Tuple[List[TranscodeProfile], List[str]]:
        """
        Filter profiles based on detected media type

        Args:
            profiles: List of transcode profiles
            media_type: Detected media type ('image' or 'video')

        Returns:
            Tuple of (filtered_profiles, skipped_profile_ids)
        """
        if not profiles:
            return [], []

        filtered_profiles = []
        skipped_profiles = []

        for profile in profiles:
            # Check if profile has input_type field
            profile_input_type = getattr(profile, "input_type", None)

            if profile_input_type is None:
                # No input_type specified, include all profiles (backward
                # compatibility)
                filtered_profiles.append(profile)
                logger.debug(
                    f"Profile {
                    profile.id_profile} has no input_type, including"
                )
            elif profile_input_type == media_type:
                # Input type matches, include this profile
                filtered_profiles.append(profile)
                logger.debug(
                    f"Profile {
                    profile.id_profile} matches input_type: {media_type}"
                )
            else:
                # Input type doesn't match, skip this profile
                skipped_profiles.append(profile.id_profile)
                logger.info(
                    f"Skipping profile {
                    profile.id_profile}: input_type={profile_input_type}, media_type={media_type}"
                )

        logger.info(
            f"Filtered {
            len(filtered_profiles)} profiles for {media_type} input, skipped {
            len(skipped_profiles)} profiles"
        )

        return filtered_profiles, skipped_profiles

    @classmethod
    def get_profile_summary(
            cls, original_count: int, filtered_count: int, skipped_profiles: List[str], media_type: str
    ) -> dict:
        """Get filtering summary for logging/response"""
        return {
            "detected_media_type": media_type,
            "original_profiles_count": original_count,
            "filtered_profiles_count": filtered_count,
            "skipped_profiles_count": len(skipped_profiles),
            "skipped_profiles": skipped_profiles,
        }


# Global instance
media_detection_service = MediaDetectionService()
