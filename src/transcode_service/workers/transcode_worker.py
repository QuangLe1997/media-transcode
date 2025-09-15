#!/usr/bin/env python3
"""
TranscodeWorker v2 - Using UniversalMediaConverter
Simplified worker that only supports WebP, JPG, and MP4 outputs
No GIF processing - only formats supported by UniversalMediaConverter
"""

import json
import logging.handlers
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from ..models.schemas_v2 import MediaMetadata, UniversalTranscodeMessage, UniversalTranscodeResult
from ..services.pubsub_service import pubsub_service
from ..services.s3_service import s3_service

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging for consumer

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Setup logging handlers
handlers = [logging.StreamHandler()]

# Add file handler only if logs directory is writable
try:
    handlers.append(
        logging.handlers.RotatingFileHandler(
            "logs/consumer_v2.log", maxBytes=5 * 1024 * 1024, backupCount=3
        )
    )
except (OSError, PermissionError):
    print("Warning: Cannot write to logs directory, using console output only")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers,
)

logger = logging.getLogger("consumer_v2")

# UniversalMediaConverter is now available as part of the package

try:
    from ..core.universal_media_converter import UniversalMediaConverter

    HAS_UNIVERSAL_CONVERTER = True
    logger.info("✅ UniversalMediaConverter imported successfully")
except ImportError as e:
    HAS_UNIVERSAL_CONVERTER = False
    logger.error(f"❌ Failed to import UniversalMediaConverter: {e}")


def extract_media_metadata(file_path: str) -> MediaMetadata:
    """Extract metadata from media file using ffprobe"""
    try:
        # Get file size
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None

        # Get media metadata using ffprobe
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            logger.warning(f"ffprobe failed for {file_path}: {result.stderr}")
            return MediaMetadata(file_size=file_size)

        # Parse ffprobe output
        probe_data = json.loads(result.stdout)

        # Extract metadata
        metadata = MediaMetadata(file_size=file_size)

        if "format" in probe_data:
            format_info = probe_data["format"]
            if "duration" in format_info:
                try:
                    metadata.duration = int(float(format_info["duration"]))
                except (ValueError, TypeError):
                    pass

            if "bit_rate" in format_info:
                try:
                    bitrate_bps = int(format_info["bit_rate"])
                    metadata.bitrate = f"{bitrate_bps // 1000}k"
                except (ValueError, TypeError):
                    pass

            if "format_name" in format_info:
                metadata.format = format_info["format_name"]

        # Extract video stream info
        for stream in probe_data.get("streams", []):
            if stream.get("codec_type") == "video":
                # Get dimensions
                width = stream.get("width")
                height = stream.get("height")
                if width and height:
                    metadata.dimensions = f"{width}×{height}"

                # Get FPS
                fps_str = stream.get("r_frame_rate", "0/1")
                try:
                    if "/" in fps_str:
                        num, den = fps_str.split("/")
                        if int(den) > 0:
                            metadata.fps = int(float(num) / float(den))
                except (ValueError, ZeroDivisionError):
                    pass

                break  # Take first video stream

        logger.info(
            f"Extracted metadata for {file_path}: {metadata.model_dump()}"
        )
        return metadata

    except Exception as e:
        logger.warning(f"Failed to extract metadata for {file_path}: {e}")
        return MediaMetadata(file_size=file_size if "file_size" in locals() else None)


class TranscodeWorkerV2:
    def __init__(self):
        if not HAS_UNIVERSAL_CONVERTER:
            raise ImportError("UniversalMediaConverter is required but not available")

        self.converter = UniversalMediaConverter()
        self.temp_dir = tempfile.mkdtemp(prefix="transcode_v2_")
        logger.info(f"Created temp directory: {self.temp_dir}")

    def __del__(self):
        # Clean up temp directory
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up temp directory: {self.temp_dir}")

    def process_transcode_task(self, message: UniversalTranscodeMessage):
        """Process a single transcode task using UniversalMediaConverter"""
        logger.info(
            f"🔄 === CONSUMER V2 PROCESSING START: task {message.task_id}, profile {message.profile.id_profile} ==="
        )
        logger.info(f"Source: {message.source_url}")
        logger.info(f"Config: {message.profile.config.model_dump()}")

        # 📊 S3 CONFIG LOGGING
        logger.info(
            f"📊 S3 CONFIG in CONSUMER V2 for task {message.task_id}, profile {message.profile.id_profile}:"
        )
        if message.s3_output_config:
            s3_config = message.s3_output_config
            logger.info(f"   📦 Using bucket: {s3_config.bucket}")
            logger.info(f"   📁 Using base_path: {s3_config.base_path}")
            logger.info(
                f"   🗂️  Using folder_structure: {s3_config.folder_structure}"
            )
            logger.info(
                f"   🧹 Cleanup temp files: {getattr(s3_config, 'cleanup_temp_files', 'N/A')}"
            )
        else:
            logger.warning(f"   ⚠️  NO S3 config found in message!")

        temp_input = None
        temp_outputs = []

        try:
            # Handle source file - use shared path or download from URL
            if message.source_path:
                # Use shared volume file directly - no download needed!
                temp_input = message.source_path
                logger.info(f"📁 Using shared file: {temp_input}")

                # Verify shared file exists
                if not os.path.exists(temp_input):
                    raise Exception(f"Shared file not found: {temp_input}")

            elif message.source_url:
                # Fallback: download from URL (backward compatibility)
                # Extract file extension from URL if present
                from urllib.parse import urlparse
                url_path = urlparse(message.source_url).path
                file_ext = Path(url_path).suffix if url_path else ""

                # If no extension in URL, try to detect from content
                if not file_ext:
                    file_ext = ".mp4"  # Default to mp4 for videos

                temp_input = os.path.join(
                    self.temp_dir,
                    f"{message.task_id}_{message.profile.id_profile}_input{file_ext}",
                )

                logger.info(f"🔗 Downloading from URL: {message.source_url}")
                if not s3_service.download_file_from_url(message.source_url, temp_input):
                    raise Exception(f"Failed to download source file from URL: {message.source_url}")
            else:
                raise Exception("No source URL or source path provided")

            # Process using UniversalMediaConverter
            output_urls = self._process_with_universal_converter(message, temp_input, temp_outputs)

            # Extract metadata for each output file
            metadata_list = []
            for i, temp_output in enumerate(temp_outputs):
                if os.path.exists(temp_output):
                    metadata = extract_media_metadata(temp_output)
                    metadata_list.append(metadata)
                else:
                    metadata_list.append(MediaMetadata())

            # Send success result
            result = UniversalTranscodeResult(
                task_id=message.task_id,
                profile_id=message.profile.id_profile,
                status="completed",
                output_urls=output_urls,
                metadata=metadata_list,
                completed_at=datetime.now(timezone.utc),
                input_type=message.profile.input_type,
                output_format=message.profile.config.output_format,
            )
            logger.info(
                f"Publishing result for task {message.task_id}, profile {message.profile.id_profile}"
            )
            message_id = pubsub_service.publish_universal_transcode_result(result)
            logger.info(f"✅ Result published with message_id: {message_id}")

            logger.info(
                f"✅ === CONSUMER V2 PROCESSING COMPLETE: task {message.task_id}, profile {message.profile.id_profile} ==="
            )

        except Exception as e:
            logger.error(
                f"❌ === CONSUMER V2 PROCESSING FAILED: task {message.task_id}, profile {message.profile.id_profile} ==="
            )
            logger.error(f"Error details: {str(e)}")

            # Send failure result
            try:
                result = UniversalTranscodeResult(
                    task_id=message.task_id,
                    profile_id=message.profile.id_profile,
                    status="failed",
                    error_message=str(e),
                    completed_at=datetime.now(timezone.utc),
                )
                logger.info(
                    f"Publishing failure result for task {message.task_id}, profile {message.profile.id_profile}"
                )
                message_id = pubsub_service.publish_universal_transcode_result(result)
                logger.info(f"❌ Failure result published with message_id: {message_id}")
            except Exception as result_error:
                logger.error(f"Failed to publish failure result: {result_error}")

        finally:
            # Clean up temp files based on S3 config
            cleanup_enabled = (
                    hasattr(message.s3_output_config, "cleanup_temp_files")
                    and message.s3_output_config.cleanup_temp_files
            )
            logger.info(f"🗑️  CLEANUP CONFIG: cleanup_temp_files = {cleanup_enabled}")

            if cleanup_enabled:
                cleanup_count = 0

                # Only cleanup downloaded files, NOT shared volume files
                if (temp_input and
                        temp_input != message.source_url and  # Not a URL
                        not message.source_path and  # Not using shared volume
                        os.path.exists(temp_input)):
                    os.remove(temp_input)
                    cleanup_count += 1
                    logger.info(f"   ✅ Cleaned up downloaded input file: {temp_input}")
                elif message.source_path:
                    logger.info(f"   ⏭️  Skipped cleanup of shared file: {temp_input}")

                for temp_output in temp_outputs:
                    if os.path.exists(temp_output):
                        os.remove(temp_output)
                        cleanup_count += 1
                        logger.info(f"   ✅ Cleaned up temp output file: {temp_output}")

                logger.info(f"🗑️  CLEANUP COMPLETE: Removed {cleanup_count} temporary files")
            else:
                logger.info("🗑️  CLEANUP SKIPPED: Temp file cleanup disabled by S3 config")

    def _process_with_universal_converter(
            self, message: UniversalTranscodeMessage, temp_input: str, temp_outputs: List[str]
    ) -> List[str]:
        """Process media using UniversalMediaConverter"""
        logger.info(f"Processing with UniversalMediaConverter")

        profile = message.profile
        config = profile.config

        # Determine output format based on config or auto-detect
        output_format = config.output_format.value
        if output_format:
            # Get the string value from enum if it's an enum, otherwise use as-is
            if hasattr(output_format, 'value'):
                output_format = output_format.value
            else:
                output_format = str(output_format).lower()
        else:
            # Auto-detect from filename if provided, otherwise use webp as default
            if profile.output_filename:
                ext = Path(profile.output_filename).suffix.lower().lstrip(".")
                if ext in ["webp", "jpg", "jpeg", "mp4", "gif"]:
                    output_format = ext
                else:
                    output_format = "webp"  # Default fallback
            else:
                output_format = "webp"  # Default fallback

        # Create temp output file
        temp_output = os.path.join(
            self.temp_dir,
            f"{message.task_id}_{profile.id_profile}.{output_format}",
        )
        temp_outputs.append(temp_output)

        logger.info(f"Converting {temp_input} -> {temp_output} (format: {output_format})")

        # Get source video info for validation if input is video and output is mp4
        source_info = None
        if profile.input_type == "video" and output_format == "mp4":
            source_info = self._get_source_video_info(temp_input)
            logger.info(f"Source video info: {source_info}")

        # Validate and adjust parameters based on source info
        validated_config = self._validate_target_params(config, source_info) if source_info else config
        
        # Handle CRF vs Bitrate mode selection
        has_explicit_crf = hasattr(config, 'crf') and config.crf is not None
        has_explicit_bitrate = hasattr(config, 'bitrate') and config.bitrate is not None
        
        if has_explicit_crf and has_explicit_bitrate:
            logger.warning(f"⚠️  Both CRF ({validated_config.crf}) and bitrate ({validated_config.bitrate}) are set. FFmpeg will prioritize CRF and ignore bitrate!")
        elif has_explicit_bitrate and not has_explicit_crf:
            # Pure bitrate mode
            logger.info(f"Using bitrate mode ({validated_config.bitrate})")
            validated_config.crf = None
        elif has_explicit_crf and not has_explicit_bitrate:
            # Pure CRF mode  
            logger.info(f"Using CRF mode ({validated_config.crf})")
        else:
            # No explicit mode set - let FFmpeg use its defaults
            logger.info(f"No encoding mode specified, using FFmpeg defaults")
            validated_config.crf = None

        # Convert config to UniversalMediaConverter parameters
        convert_params = {
            # Basic parameters
            "width": validated_config.width,
            "height": validated_config.height,
            "quality": validated_config.quality,
            "fps": validated_config.fps,
            "duration": validated_config.duration,
            "start_time": validated_config.start_time,
            "speed": validated_config.speed,
            "contrast": validated_config.contrast,
            "brightness": validated_config.brightness,
            "saturation": validated_config.saturation,
            "gamma": validated_config.gamma,
            "enable_denoising": validated_config.enable_denoising,
            "enable_sharpening": validated_config.enable_sharpening,
            "auto_filter": validated_config.auto_filter,
            # WebP-specific
            "lossless": validated_config.lossless,
            "method": validated_config.method,
            "preset": validated_config.preset,
            "near_lossless": validated_config.near_lossless,
            "alpha_quality": validated_config.alpha_quality,
            "animated": validated_config.animated,
            "loop": validated_config.loop,
            "pass_count": validated_config.pass_count,
            "target_size": validated_config.target_size,
            "save_frames": validated_config.save_frames,
            # JPG-specific
            "jpeg_quality": validated_config.jpeg_quality,
            "optimize": validated_config.optimize,
            "progressive": validated_config.progressive,
            # MP4-specific
            "codec": validated_config.codec,
            "crf": validated_config.crf,
            "mp4_preset": validated_config.mp4_preset,
            "bitrate": validated_config.bitrate,
            "max_bitrate": validated_config.max_bitrate,
            "buffer_size": validated_config.buffer_size,
            "profile": validated_config.profile,
            "level": validated_config.level,
            "pixel_format": validated_config.pixel_format,
            "audio_codec": validated_config.audio_codec,
            "audio_bitrate": validated_config.audio_bitrate,
            "audio_sample_rate": validated_config.audio_sample_rate,
            "two_pass": config.two_pass,
            "hardware_accel": config.hardware_accel,
            "verbose": config.verbose,
        }

        # Execute conversion
        logger.info(f"Executing UniversalMediaConverter with parameters: {convert_params}")

        result = self.converter.convert(
            input_path=temp_input, output_path=temp_output, **convert_params
        )

        if not result.get("success", False):
            error_msg = result.get("error", "Unknown conversion error")
            command = result.get("command", "")
            logger.error(f"UniversalMediaConverter failed: {error_msg}")
            logger.error(f"Command used: {command}")
            raise Exception(f"Media conversion failed: {error_msg}")

        logger.info(f"✅ Conversion successful: {result}")

        # Upload outputs to S3
        output_urls = []
        for i, temp_output in enumerate(temp_outputs):
            if os.path.exists(temp_output):
                # Generate output filename with correct extension
                file_ext = os.path.splitext(temp_output)[1]
                if profile.output_filename:
                    output_filename = f"{Path(profile.output_filename).stem}{file_ext}"
                else:
                    output_filename = f"{profile.id_profile}_output_{i}{file_ext}"

                # Generate S3 key based on config
                s3_config = message.s3_output_config.model_dump()
                logger.info(f"📤 S3 UPLOAD CONFIG for {output_filename}:")
                logger.info(
                    f"   📦 S3 bucket: {s3_config.get('bucket', 'N/A')}"
                )
                logger.info(
                    f"   📁 Base path: {s3_config.get('base_path', 'N/A')}"
                )
                logger.info(
                    f"   🗂️  Folder structure: {s3_config.get('folder_structure', 'N/A')}"
                )

                output_key = s3_service.generate_output_key(
                    message.task_id, message.profile.id_profile, output_filename, s3_config
                )
                logger.info(f"   🔑 Generated S3 key: {output_key}")

                # Upload to S3
                logger.info(f"📤 Uploading {output_filename} to S3...")
                output_url = s3_service.upload_file_from_path(
                    temp_output, output_key, skip_base_folder=True
                )
                output_urls.append(output_url)
                logger.info(f"   ✅ Upload success: {output_url}")

        return output_urls

    def _get_source_video_info(self, input_path: str) -> dict:
        """Get source video information using ffprobe"""
        import subprocess
        import json
        
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "stream=bit_rate,width,height,r_frame_rate,sample_rate",
                "-select_streams", "v:0",  # First video stream
                "-of", "json",
                input_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            stream = data.get("streams", [{}])[0]
            
            # Parse frame rate (e.g., "30/1" -> 30.0)
            fps_str = stream.get("r_frame_rate", "0/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den) if float(den) != 0 else 0.0
            else:
                fps = float(fps_str)
            
            # Get audio info
            audio_cmd = [
                "ffprobe",
                "-v", "quiet", 
                "-show_entries", "stream=bit_rate,sample_rate",
                "-select_streams", "a:0",  # First audio stream
                "-of", "json",
                input_path
            ]
            
            audio_result = subprocess.run(audio_cmd, capture_output=True, text=True)
            audio_data = {}
            if audio_result.returncode == 0:
                audio_json = json.loads(audio_result.stdout)
                audio_stream = audio_json.get("streams", [{}])[0]
                audio_data = {
                    "audio_bitrate": audio_stream.get("bit_rate"),
                    "audio_sample_rate": audio_stream.get("sample_rate")
                }
            
            source_info = {
                "width": stream.get("width"),
                "height": stream.get("height"),
                "fps": fps,
                "bitrate": stream.get("bit_rate"),
                **audio_data
            }
            
            logger.info(f"Source video info extracted: {source_info}")
            return source_info
            
        except Exception as e:
            logger.warning(f"Failed to get source video info: {e}")
            return {}

    def _validate_target_params(self, config, source_info: dict):
        """Validate and adjust target parameters to not exceed source"""
        if not source_info:
            return config
            
        # Create a copy of config to modify
        import copy
        validated_config = copy.deepcopy(config)
        
        # Validate width/height
        if source_info.get("width") and config.width:
            if config.width > source_info["width"]:
                logger.warning(f"Target width {config.width} > source {source_info['width']}, adjusting to source")
                validated_config.width = source_info["width"]
                
        if source_info.get("height") and config.height:
            if config.height > source_info["height"]:
                logger.warning(f"Target height {config.height} > source {source_info['height']}, adjusting to source")
                validated_config.height = source_info["height"]
        
        # Validate FPS
        if source_info.get("fps") and config.fps:
            if config.fps > source_info["fps"]:
                logger.warning(f"Target fps {config.fps} > source {source_info['fps']}, adjusting to source")
                validated_config.fps = source_info["fps"]
        
        # Validate bitrate (convert string to int for comparison)
        if source_info.get("bitrate") and config.bitrate:
            try:
                source_bitrate = int(source_info["bitrate"])
                target_bitrate_str = config.bitrate.replace("M", "000000").replace("k", "000")
                target_bitrate = int(float(target_bitrate_str))
                
                if target_bitrate > source_bitrate:
                    # Convert back to appropriate format
                    if source_bitrate >= 1000000:
                        new_bitrate = f"{source_bitrate / 1000000:.1f}M"
                    else:
                        new_bitrate = f"{source_bitrate / 1000:.0f}k"
                    logger.warning(f"Target bitrate {config.bitrate} > source {source_bitrate}, adjusting to {new_bitrate}")
                    validated_config.bitrate = new_bitrate
            except (ValueError, AttributeError):
                pass
        
        # Validate audio sample rate
        if source_info.get("audio_sample_rate") and config.audio_sample_rate:
            source_sample_rate = int(source_info["audio_sample_rate"])
            if config.audio_sample_rate > source_sample_rate:
                logger.warning(f"Target audio sample rate {config.audio_sample_rate} > source {source_sample_rate}, adjusting to source")
                validated_config.audio_sample_rate = source_sample_rate
        
        # Validate audio bitrate
        if source_info.get("audio_bitrate") and config.audio_bitrate:
            try:
                source_audio_bitrate = int(source_info["audio_bitrate"])
                target_audio_bitrate_str = config.audio_bitrate.replace("k", "000")
                target_audio_bitrate = int(target_audio_bitrate_str)
                
                if target_audio_bitrate > source_audio_bitrate:
                    new_audio_bitrate = f"{source_audio_bitrate / 1000:.0f}k"
                    logger.warning(f"Target audio bitrate {config.audio_bitrate} > source {source_audio_bitrate}, adjusting to {new_audio_bitrate}")
                    validated_config.audio_bitrate = new_audio_bitrate
            except (ValueError, AttributeError):
                pass
        
        # Adaptive CRF based on resolution (if CRF is used)
        if config.crf and not config.bitrate:  # Only adjust if using CRF mode
            target_width = validated_config.width or source_info.get("width", 720)
            adaptive_crf = self._get_adaptive_crf(target_width, config.crf)
            if adaptive_crf != config.crf:
                logger.info(f"Adjusting CRF from {config.crf} to {adaptive_crf} based on resolution {target_width}p")
                validated_config.crf = adaptive_crf
        
        return validated_config

    def _get_adaptive_crf(self, width: int, base_crf: int) -> int:
        """Get adaptive CRF based on resolution - optimize for smaller file size"""
        # Resolution-based CRF adjustment (higher CRF = smaller file)
        if width >= 1920:    # 4K/1080p+
            return min(base_crf + 1, 28)  # Increase CRF for smaller file at high res
        elif width >= 1280:  # 720p
            return base_crf  # Keep original
        elif width >= 640:   # 480p
            return max(base_crf - 1, 18)  # Decrease CRF to maintain quality at low res
        else:                # Very low res
            return max(base_crf - 2, 18)  # Much better quality needed for very low res


def main():
    """Main consumer loop for v2 worker"""
    logger.info("Starting transcode consumer v2...")

    worker = TranscodeWorkerV2()

    try:
        # Subscribe to transcode tasks - use v2 message format
        def process_universal_message(message_data):
            """Process UniversalTranscodeMessage format"""
            try:
                if isinstance(message_data, UniversalTranscodeMessage):
                    message = message_data
                else:
                    message = UniversalTranscodeMessage(**message_data)
                worker.process_transcode_task(message)
            except Exception as e:
                logger.error(f"Failed to process message: {e}")
                logger.error(f"Message data: {message_data}")

        pubsub_service.listen_for_transcode_messages(
            callback=process_universal_message, timeout=None  # Run forever
        )
    except KeyboardInterrupt:
        logger.info("Consumer v2 stopped by user")
    except Exception as e:
        logger.error(f"Consumer v2 error: {e}")
    finally:
        del worker


if __name__ == "__main__":
    main()
