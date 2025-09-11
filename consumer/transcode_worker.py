import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging for consumer
import logging.handlers

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Setup logging handlers
handlers = [logging.StreamHandler()]

# Add file handler only if logs directory is writable
try:
    handlers.append(logging.handlers.RotatingFileHandler('logs/consumer.log', maxBytes=5 * 1024 * 1024, backupCount=3))
except (OSError, PermissionError):
    print("Warning: Cannot write to logs directory, using console output only")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
from services import s3_service, pubsub_service
from models.schemas import TranscodeMessage, TranscodeResult, OutputType, MediaMetadata
from mobile_profile_system import build_ffmpeg_args, ProfileConfig, ProfileType

# Import GIF processing libraries
try:
    import imageio
    from PIL import Image

    HAS_GIF_LIBS = True
except ImportError:
    HAS_GIF_LIBS = False
    logging.warning("GIF processing libraries not available. Install: pip install imageio pillow")

logger = logging.getLogger("consumer")


def extract_media_metadata(file_path: str) -> MediaMetadata:
    """Extract metadata from media file using ffprobe"""
    try:
        # Get file size
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None
        
        # Get media metadata using ffprobe
        cmd = [
            'ffprobe', 
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.warning(f"ffprobe failed for {file_path}: {result.stderr}")
            return MediaMetadata(file_size=file_size)
        
        # Parse ffprobe output
        probe_data = json.loads(result.stdout)
        
        # Extract metadata
        metadata = MediaMetadata(file_size=file_size)
        
        if 'format' in probe_data:
            format_info = probe_data['format']
            if 'duration' in format_info:
                try:
                    metadata.duration = int(float(format_info['duration']))
                except (ValueError, TypeError):
                    pass
            
            if 'bit_rate' in format_info:
                try:
                    bitrate_bps = int(format_info['bit_rate'])
                    metadata.bitrate = f"{bitrate_bps // 1000}k"
                except (ValueError, TypeError):
                    pass
            
            if 'format_name' in format_info:
                metadata.format = format_info['format_name']
        
        # Extract video stream info
        for stream in probe_data.get('streams', []):
            if stream.get('codec_type') == 'video':
                # Get dimensions
                width = stream.get('width')
                height = stream.get('height')
                if width and height:
                    metadata.dimensions = f"{width}×{height}"
                
                # Get FPS
                fps_str = stream.get('r_frame_rate', '0/1')
                try:
                    if '/' in fps_str:
                        num, den = fps_str.split('/')
                        if int(den) > 0:
                            metadata.fps = int(float(num) / float(den))
                except (ValueError, ZeroDivisionError):
                    pass
                
                break  # Take first video stream
        
        logger.info(f"Extracted metadata for {file_path}: {metadata.model_dump()}")
        return metadata
        
    except Exception as e:
        logger.warning(f"Failed to extract metadata for {file_path}: {e}")
        return MediaMetadata(file_size=file_size if 'file_size' in locals() else None)


class TranscodeWorker:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="transcode_")
        logger.info(f"Created temp directory: {self.temp_dir}")

    def __del__(self):
        # Clean up temp directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up temp directory: {self.temp_dir}")

    def process_transcode_task(self, message: TranscodeMessage):
        """Process a single transcode task"""
        logger.info(f"🔄 === CONSUMER PROCESSING START: task {message.task_id}, profile {message.profile.id_profile} ===")
        logger.info(f"Profile details: output_type={message.profile.output_type}, input_type={getattr(message.profile, 'input_type', 'None')}")
        logger.info(f"Source: {'S3 key: ' + str(message.source_key) if message.source_key else 'URL: ' + message.source_url}")
        
        # 📊 S3 CONFIG LOGGING: Show S3 config received in consumer
        logger.info(f"📊 S3 CONFIG in CONSUMER for task {message.task_id}, profile {message.profile.id_profile}:")
        if hasattr(message, 's3_output_config') and message.s3_output_config:
            s3_config = message.s3_output_config
            logger.info(f"   📦 Using bucket: {s3_config.bucket}")
            logger.info(f"   📁 Using base_path: {s3_config.base_path}")
            logger.info(f"   🗂️  Using folder_structure: {s3_config.folder_structure}")
            logger.info(f"   🧹 Cleanup temp files: {getattr(s3_config, 'cleanup_temp_files', 'N/A')}")
            logger.info(f"   ⏱️  Upload timeout: {getattr(s3_config, 'upload_timeout', 'N/A')}s")
            logger.info(f"   🔄 Max retries: {getattr(s3_config, 'max_retries', 'N/A')}")
        else:
            logger.warning(f"   ⚠️  NO S3 config found in message!")

        temp_input = None
        temp_outputs = []

        try:
            # Handle source file - either download from S3 or use URL directly
            # Use profile-specific temp file to avoid race conditions between parallel profiles
            temp_input = os.path.join(self.temp_dir, f"{message.task_id}_{message.profile.id_profile}_input")

            if message.source_url:
                # Download from public URL (both uploaded files and external URLs)
                if not s3_service.download_file_from_url(message.source_url, temp_input):
                    raise Exception(f"Failed to download source file from URL: {message.source_url}")
            else:
                raise Exception("No source URL provided")

            # Process based on output type
            output_urls = []

            if message.profile.output_type == OutputType.GIF:
                # Process GIF using specialized libraries
                output_urls = self._process_gif(message, temp_input, temp_outputs)
            elif message.profile.output_type == OutputType.WEBP:
                # Process WebP using FFmpeg
                output_urls = self._process_webp(message, temp_input, temp_outputs)
            else:
                # Process VIDEO or IMAGE using FFmpeg (check for config vs args)
                output_urls = self._process_ffmpeg_with_config(message, temp_input, temp_outputs)

            # Extract metadata for each output file
            metadata_list = []
            for i, temp_output in enumerate(temp_outputs):
                if os.path.exists(temp_output):
                    metadata = extract_media_metadata(temp_output)
                    metadata_list.append(metadata)
                else:
                    # Fallback metadata if file doesn't exist
                    metadata_list.append(MediaMetadata())

            # Send success result
            result = TranscodeResult(
                task_id=message.task_id,
                profile_id=message.profile.id_profile,
                status="completed",
                output_urls=output_urls,
                metadata=metadata_list,
                completed_at=datetime.now(timezone.utc)
            )
            logger.info(f"Publishing result for task {message.task_id}, profile {message.profile.id_profile}")
            message_id = pubsub_service.publish_transcode_result(result)
            logger.info(f"✅ Result published with message_id: {message_id}")

            logger.info(f"✅ === CONSUMER PROCESSING COMPLETE: task {message.task_id}, profile {message.profile.id_profile} ===")

        except Exception as e:
            logger.error(f"❌ === CONSUMER PROCESSING FAILED: task {message.task_id}, profile {message.profile.id_profile} ===")
            logger.error(f"Error details: {str(e)}")
            
            # Send failure result
            try:
                result = TranscodeResult(
                    task_id=message.task_id,
                    profile_id=message.profile.id_profile,
                    status="failed",
                    error_message=str(e),
                    completed_at=datetime.now(timezone.utc)
                )
                logger.info(f"Publishing failure result for task {message.task_id}, profile {message.profile.id_profile}")
                message_id = pubsub_service.publish_transcode_result(result)
                logger.info(f"❌ Failure result published with message_id: {message_id}")
            except Exception as result_error:
                logger.error(f"Failed to publish failure result: {result_error}")

        finally:
            # Clean up temp files based on S3 config
            cleanup_enabled = hasattr(message.s3_output_config, 'cleanup_temp_files') and message.s3_output_config.cleanup_temp_files
            logger.info(f"🗑️  CLEANUP CONFIG: cleanup_temp_files = {cleanup_enabled}")
            
            if cleanup_enabled:
                cleanup_count = 0
                if temp_input and temp_input != message.source_url and os.path.exists(temp_input):
                    os.remove(temp_input)
                    cleanup_count += 1
                    logger.info(f"   ✅ Cleaned up temp input file: {temp_input}")

                for temp_output in temp_outputs:
                    if os.path.exists(temp_output):
                        os.remove(temp_output)
                        cleanup_count += 1
                        logger.info(f"   ✅ Cleaned up temp output file: {temp_output}")
                
                logger.info(f"🗑️  CLEANUP COMPLETE: Removed {cleanup_count} temporary files")
            else:
                logger.info("🗑️  CLEANUP SKIPPED: Temp file cleanup disabled by S3 config")

    def _process_ffmpeg_with_config(self, message: TranscodeMessage, temp_input: str, temp_outputs: List[str]) -> List[
        str]:
        """Process video/image using FFmpeg - check for config vs args priority"""
        profile = message.profile

        # Priority: ffmpeg_args > video_config/image_config
        if profile.ffmpeg_args:
            logger.info(f"Using ffmpeg_args for profile {profile.id_profile}")
            return self._process_ffmpeg(message, temp_input, temp_outputs)

        # Use video_config or image_config to build ffmpeg_args
        elif profile.video_config or profile.image_config:
            logger.info(f"Building ffmpeg_args from config for profile {profile.id_profile}")

            # Create a ProfileConfig-like object to use build_ffmpeg_args
            from mobile_profile_system import VideoConfig as MobileVideoConfig, ImageConfig as MobileImageConfig, \
                DeviceType

            if profile.video_config:
                # Convert schema VideoConfig to mobile VideoConfig
                mobile_config = ProfileConfig(
                    id=profile.id_profile,
                    name=f"Dynamic {profile.id_profile}",
                    device_type=DeviceType.HIGH_END,  # Default device type
                    profile_type=ProfileType.MAIN_VIDEO,
                    video_config=MobileVideoConfig(**profile.video_config.model_dump()),
                    description="Generated from video_config"
                )
            else:  # image_config
                # Convert schema ImageConfig to mobile ImageConfig  
                mobile_config = ProfileConfig(
                    id=profile.id_profile,
                    name=f"Dynamic {profile.id_profile}",
                    device_type=DeviceType.HIGH_END,
                    profile_type=ProfileType.THUMBNAIL_IMAGE,
                    image_config=MobileImageConfig(**profile.image_config.model_dump()),
                    description="Generated from image_config"
                )

            # Build ffmpeg args from config with GPU codec detection and fallback
            generated_args = build_ffmpeg_args(mobile_config, keep_aspect_ratio=True, check_gpu_availability=True)

            # Create temporary profile with generated args
            temp_profile = message.profile.model_copy()
            temp_profile.ffmpeg_args = generated_args

            # Create temporary message
            temp_message = message.model_copy()
            temp_message.profile = temp_profile

            logger.info(f"Generated FFmpeg args: {' '.join(generated_args)}")
            return self._process_ffmpeg(temp_message, temp_input, temp_outputs)

        else:
            raise Exception(f"Profile {profile.id_profile} has no ffmpeg_args, video_config, or image_config")

    def _process_ffmpeg(self, message: TranscodeMessage, temp_input: str, temp_outputs: List[str]) -> List[str]:
        """Process video/image using FFmpeg"""
        logger.info(f"Processing {message.profile.output_type} with FFmpeg")

        # Simple output extension detection
        output_ext = '.mp4'  # default for video
        if message.profile.output_type == OutputType.IMAGE:
            output_ext = '.jpg'  # default for image

        # Check format flag for extension override
        if message.profile.ffmpeg_args and '-f' in message.profile.ffmpeg_args:
            f_idx = message.profile.ffmpeg_args.index('-f')
            if f_idx + 1 < len(message.profile.ffmpeg_args):
                format_type = message.profile.ffmpeg_args[f_idx + 1]
                # Simplified format mapping - only common formats
                if format_type == 'image2':
                    output_ext = '.jpg'
                elif format_type == 'png':
                    output_ext = '.png'
                elif format_type == 'webp':
                    output_ext = '.webp'
                elif format_type == 'webm':
                    output_ext = '.webm'
                elif format_type == 'mp4':
                    output_ext = '.mp4'

        # Check codec for additional extension hints
        if message.profile.ffmpeg_args and '-c:v' in message.profile.ffmpeg_args:
            codec_idx = message.profile.ffmpeg_args.index('-c:v')
            if codec_idx + 1 < len(message.profile.ffmpeg_args):
                codec = message.profile.ffmpeg_args[codec_idx + 1]
                # Support for GPU codecs
                if codec in ['libwebp']:
                    output_ext = '.webp'
                elif codec in ['libvpx', 'libvpx-vp9']:
                    output_ext = '.webm'
                elif codec in ['libx264', 'libx265', 'h264_nvenc', 'hevc_nvenc', 'h264_qsv', 'hevc_qsv']:
                    output_ext = '.mp4'

        # Create temp output file
        temp_output = os.path.join(
            self.temp_dir,
            f"{message.task_id}_{message.profile.id_profile}_output{output_ext}"
        )
        temp_outputs.append(temp_output)

        # Build complete ffmpeg command
        cmd = ['ffmpeg', '-i', temp_input] + message.profile.ffmpeg_args + [temp_output]

        logger.info(f"Executing ffmpeg command: {' '.join(cmd)}")

        # Execute ffmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        if result.returncode != 0:
            raise Exception(f"FFmpeg failed: {result.stderr}")

        # Upload outputs to S3
        output_urls = []
        for i, temp_output in enumerate(temp_outputs):
            if os.path.exists(temp_output):
                # Generate output filename with correct extension
                file_ext = os.path.splitext(temp_output)[1]
                output_filename = f"{message.profile.id_profile}_output_{i}{file_ext}"

                # Generate S3 key based on config
                s3_config = message.s3_output_config.model_dump()
                logger.info(f"📤 S3 UPLOAD CONFIG for {output_filename}:")
                logger.info(f"   📦 S3 bucket: {s3_config.get('bucket', 'N/A')}")
                logger.info(f"   📁 Base path: {s3_config.get('base_path', 'N/A')}")
                logger.info(f"   🗂️  Folder structure: {s3_config.get('folder_structure', 'N/A')}")
                
                output_key = s3_service.generate_output_key(
                    message.task_id,
                    message.profile.id_profile,
                    output_filename,
                    s3_config
                )
                logger.info(f"   🔑 Generated S3 key: {output_key}")

                # Upload to S3 (key already includes base_path from generate_output_key)
                logger.info(f"📤 Uploading {output_filename} to S3...")
                output_url = s3_service.upload_file_from_path(temp_output, output_key, skip_base_folder=True)
                output_urls.append(output_url)
                logger.info(f"   ✅ Upload success: {output_url}")

                logger.info(f"Uploaded FFmpeg output to: {output_url}")

        return output_urls

    def _process_gif(self, message: TranscodeMessage, temp_input: str, temp_outputs: List[str]) -> List[str]:
        """Process GIF using specialized libraries"""
        if not HAS_GIF_LIBS:
            raise Exception("GIF processing libraries not available. Install: pip install imageio pillow")

        if not message.profile.gif_config:
            raise Exception("GIF config is required for GIF output")

        logger.info(f"Processing GIF with config: {message.profile.gif_config}")

        gif_config = message.profile.gif_config

        # Create temp output file
        temp_output = os.path.join(
            self.temp_dir,
            f"{message.task_id}_{message.profile.id_profile}_output.gif"
        )
        temp_outputs.append(temp_output)

        try:
            # Read video with imageio
            reader = imageio.get_reader(temp_input)
            fps = reader.get_meta_data().get('fps', 25)  # Default to 25 fps if not available

            # Calculate frame selection
            total_frames = reader.count_frames()
            start_frame = int(gif_config.start_time * fps)

            if gif_config.duration:
                end_frame = start_frame + int(gif_config.duration * fps)
            else:
                end_frame = total_frames

            # Ensure we don't exceed video bounds
            start_frame = max(0, start_frame)
            end_frame = min(total_frames, end_frame)

            # Calculate frame step for target FPS
            frame_step = max(1, int(fps / gif_config.fps))

            # Extract frames
            frames = []
            for i in range(start_frame, end_frame, frame_step):
                try:
                    frame = reader.get_data(i)

                    # Convert to PIL Image for processing
                    img = Image.fromarray(frame)

                    # Resize if dimensions specified
                    if gif_config.width or gif_config.height:
                        # Calculate dimensions maintaining aspect ratio
                        original_width, original_height = img.size
                        
                        # Determine target canvas size and content size
                        if gif_config.width and gif_config.height:
                            # Canvas size is the configured dimensions
                            canvas_width = gif_config.width
                            canvas_height = gif_config.height
                            
                            # Calculate content size maintaining aspect ratio
                            width_ratio = gif_config.width / original_width
                            height_ratio = gif_config.height / original_height
                            # Use the smaller ratio to ensure image fits within bounds
                            ratio = min(width_ratio, height_ratio)
                            content_width = int(original_width * ratio)
                            content_height = int(original_height * ratio)
                            
                            # Resize the content
                            img = img.resize((content_width, content_height), Image.Resampling.LANCZOS)
                            
                            # Create canvas and paste content centered
                            canvas = Image.new('RGB', (canvas_width, canvas_height), (0, 0, 0))
                            x_offset = (canvas_width - content_width) // 2
                            y_offset = (canvas_height - content_height) // 2
                            canvas.paste(img, (x_offset, y_offset))
                            img = canvas
                            
                        elif gif_config.width:
                            ratio = gif_config.width / original_width
                            new_size = (gif_config.width, int(original_height * ratio))
                            img = img.resize(new_size, Image.Resampling.LANCZOS)
                        else:  # gif_config.height
                            ratio = gif_config.height / original_height
                            new_size = (int(original_width * ratio), gif_config.height)
                            img = img.resize(new_size, Image.Resampling.LANCZOS)

                    frames.append(img)

                except Exception as e:
                    logger.warning(f"Error processing frame {i}: {e}")
                    continue

            reader.close()

            if not frames:
                raise Exception("No frames extracted for GIF")

            # Optimize colors if needed
            if gif_config.colors < 256:
                # Convert to indexed color mode with specified palette size
                frames = [frame.convert('P', palette=Image.ADAPTIVE, colors=gif_config.colors) for frame in frames]

            # Calculate duration per frame in milliseconds
            frame_duration = int(1000 / gif_config.fps)

            # Save GIF
            frames[0].save(
                temp_output,
                format='GIF',
                save_all=True,
                append_images=frames[1:],
                duration=frame_duration,
                loop=gif_config.loop,
                optimize=gif_config.optimize,
                dither=Image.FLOYDSTEINBERG if gif_config.dither else Image.NONE
            )

            logger.info(f"Created GIF with {len(frames)} frames")

        except Exception as e:
            raise Exception(f"GIF processing failed: {str(e)}")

        # Upload to S3
        output_urls = []
        if os.path.exists(temp_output):
            output_filename = f"{message.profile.id_profile}_output.gif"

            # Generate S3 key based on config
            s3_config = message.s3_output_config.model_dump()
            output_key = s3_service.generate_output_key(
                message.task_id,
                message.profile.id_profile,
                output_filename,
                s3_config
            )

            # Upload to S3 (key already includes base_path from generate_output_key)
            output_url = s3_service.upload_file_from_path(temp_output, output_key, skip_base_folder=True)
            output_urls.append(output_url)

            logger.info(f"Uploaded GIF output to: {output_url}")

        return output_urls

    def _process_webp(self, message: TranscodeMessage, temp_input: str, temp_outputs: List[str]) -> List[str]:
        """Process WebP using FFmpeg"""
        if not message.profile.webp_config:
            raise Exception("WebP config is required for WebP output")

        logger.info(f"Processing WebP with config: {message.profile.webp_config}")

        webp_config = message.profile.webp_config

        # Create temp output file
        temp_output = os.path.join(
            self.temp_dir,
            f"{message.task_id}_{message.profile.id_profile}_output.webp"
        )
        temp_outputs.append(temp_output)

        try:
            # Use FFmpeg for WebP processing (both static and animated)
            cmd = ['ffmpeg']
            
            # Input with timing
            if webp_config.start_time > 0:
                cmd.extend(['-ss', str(webp_config.start_time)])
            
            if webp_config.duration:
                cmd.extend(['-t', str(webp_config.duration)])
            
            cmd.extend(['-i', temp_input])

            # Build filter chain for scaling and processing
            filter_parts = []
            
            # Add scaling if dimensions specified
            if webp_config.width or webp_config.height:
                # Calculate dimensions maintaining aspect ratio
                if webp_config.width and webp_config.height:
                    scale_filter = f'scale={webp_config.width}:{webp_config.height}:force_original_aspect_ratio=decrease,pad={webp_config.width}:{webp_config.height}:(ow-iw)/2:(oh-ih)/2:black'
                elif webp_config.width:
                    scale_filter = f'scale={webp_config.width}:-1'
                else:  # webp_config.height
                    scale_filter = f'scale=-1:{webp_config.height}'
                filter_parts.append(scale_filter)

            # Set frame rate for animated WebP
            if webp_config.animated and webp_config.fps:
                filter_parts.append(f'fps={webp_config.fps}')

            # Apply filters if any
            if filter_parts:
                cmd.extend(['-vf', ','.join(filter_parts)])

            # WebP encoder settings
            cmd.extend(['-c:v', 'libwebp'])
            
            # Quality and compression settings
            if webp_config.lossless:
                cmd.extend(['-lossless', '1'])
                if webp_config.quality > 0:
                    cmd.extend(['-quality', str(webp_config.quality)])
            else:
                cmd.extend(['-quality', str(webp_config.quality)])
            
            # Compression method
            cmd.extend(['-compression_level', str(webp_config.method)])
            
            # Loop setting for animated WebP
            if webp_config.animated:
                cmd.extend(['-loop', str(webp_config.loop)])
            else:
                # For single frame WebP, extract just one frame
                cmd.extend(['-vframes', '1'])

            # Force overwrite
            cmd.extend(['-y', temp_output])

            logger.info(f"Executing FFmpeg WebP command: {' '.join(cmd)}")

            # Execute ffmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode != 0:
                logger.error(f"FFmpeg WebP processing failed: {result.stderr}")
                raise Exception(f"FFmpeg WebP failed: {result.stderr}")

            logger.info(f"Successfully created WebP with {len(temp_outputs)} output files")

        except Exception as e:
            raise Exception(f"WebP processing failed: {str(e)}")

        # Upload to S3
        output_urls = []
        if os.path.exists(temp_output):
            output_filename = f"{message.profile.id_profile}_output.webp"

            # Generate S3 key based on config
            s3_config = message.s3_output_config.model_dump()
            logger.info(f"📤 S3 UPLOAD CONFIG for {output_filename}:")
            logger.info(f"   📦 S3 bucket: {s3_config.get('bucket', 'N/A')}")
            logger.info(f"   📁 Base path: {s3_config.get('base_path', 'N/A')}")
            logger.info(f"   🗂️  Folder structure: {s3_config.get('folder_structure', 'N/A')}")
            
            output_key = s3_service.generate_output_key(
                message.task_id,
                message.profile.id_profile,
                output_filename,
                s3_config
            )
            logger.info(f"   🔑 Generated S3 key: {output_key}")

            # Upload to S3 (key already includes base_path from generate_output_key)
            logger.info(f"📤 Uploading {output_filename} to S3...")
            output_url = s3_service.upload_file_from_path(temp_output, output_key, skip_base_folder=True)
            output_urls.append(output_url)
            logger.info(f"   ✅ Upload success: {output_url}")

            logger.info(f"Uploaded WebP output to: {output_url}")

        return output_urls


def main():
    """Main consumer loop"""
    logger.info("Starting transcode consumer...")

    worker = TranscodeWorker()

    try:
        # Subscribe to transcode tasks
        pubsub_service.subscribe_to_tasks(
            callback=worker.process_transcode_task,
            timeout=None  # Run forever
        )
    except KeyboardInterrupt:
        logger.info("Consumer stopped by user")
    except Exception as e:
        logger.error(f"Consumer error: {e}")
    finally:
        del worker


if __name__ == "__main__":
    main()
