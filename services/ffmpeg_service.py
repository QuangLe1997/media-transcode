import os
import json
import subprocess
import logging
import ffmpeg
from typing import Dict, List, Union, Optional, Tuple
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class FFmpegService:
    def __init__(self, ffmpeg_path: str, ffprobe_path: str, gpu_enabled: bool = True, gpu_type: str = 'nvidia'):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.gpu_enabled = gpu_enabled
        self.gpu_type = gpu_type.lower()  # 'nvidia' or 'amd'

        # Use absolute paths
        os.environ['FFMPEG_BINARY'] = self.ffmpeg_path
        os.environ['FFPROBE_BINARY'] = self.ffprobe_path

    def get_media_info(self, file_path: str) -> Dict:
        """Get metadata for a media file using ffprobe."""
        try:
            probe = ffmpeg.probe(file_path, cmd=self.ffprobe_path)

            # Initialize with defaults
            info = {
                'format': probe['format'],
                'duration': float(probe['format'].get('duration', 0)),
                'size': int(probe['format'].get('size', 0)),
                'bit_rate': int(probe['format'].get('bit_rate', 0)),
                'width': None,
                'height': None,
                'video_codec': None,
                'audio_codec': None,
                'frame_rate': None,
                'nb_streams': len(probe['streams'])
            }

            # Get video stream info
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            if video_stream:
                info['width'] = int(video_stream.get('width', 0))
                info['height'] = int(video_stream.get('height', 0))
                info['video_codec'] = video_stream.get('codec_name')
                # Calculate frame rate
                if 'avg_frame_rate' in video_stream:
                    fps_parts = video_stream['avg_frame_rate'].split('/')
                    if len(fps_parts) == 2 and int(fps_parts[1]) != 0:
                        info['frame_rate'] = float(int(fps_parts[0]) / int(fps_parts[1]))

            # Get audio stream info
            audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
            if audio_stream:
                info['audio_codec'] = audio_stream.get('codec_name')

            return info

        except Exception as e:
            logger.error(f"Error getting media info: {str(e)}")
            raise

    def get_hardware_encoder(self, codec: str = 'h264') -> Optional[str]:
        """Get the appropriate hardware encoder based on GPU type and codec."""
        if not self.gpu_enabled:
            return None

        if self.gpu_type == 'nvidia':
            if codec == 'h264':
                return 'h264_nvenc'
            elif codec == 'hevc':
                return 'hevc_nvenc'
        elif self.gpu_type == 'amd':
            if codec == 'h264':
                return 'h264_amf'
            elif codec == 'hevc':
                return 'hevc_amf'

        # Fallback to software encoder
        return None

    def transcode_video(self,
                        input_path: str,
                        output_path: str,
                        width: int,
                        height: int,
                        codec: str = 'libx264',
                        preset: str = 'medium',
                        crf: int = 23,
                        format: str = 'mp4',
                        audio_codec: str = 'aac',
                        audio_bitrate: str = '128k',
                        use_gpu: bool = True) -> bool:
        """Transcode a video file using ffmpeg."""
        try:
            # Setup input
            stream = ffmpeg.input(input_path)

            # Determine encoder
            video_codec = codec
            if use_gpu and self.gpu_enabled:
                hw_encoder = self.get_hardware_encoder()
                if hw_encoder:
                    video_codec = hw_encoder

            # Video & audio stream
            v_stream = stream.video.filter('scale', width, height)
            a_stream = stream.audio

            # Output options
            output_options = {
                'c:v': video_codec,
                'c:a': audio_codec,
                'b:a': audio_bitrate,
                'format': format
            }

            # Add hardware-specific options
            if use_gpu and self.gpu_enabled and video_codec.startswith(('h264_nvenc', 'hevc_nvenc')):
                output_options.update({
                    'preset': 'p4',  # For NVENC
                    'rc': 'vbr'  # Rate control
                })
            elif video_codec in ('libx264', 'libx265'):
                output_options.update({
                    'preset': preset,
                    'crf': str(crf)
                })

            # Run ffmpeg
            ffmpeg.output(v_stream, a_stream, output_path, **output_options).run(
                cmd=self.ffmpeg_path,
                overwrite_output=True,
                quiet=True
            )

            return True

        except Exception as e:
            logger.error(f"Error transcoding video: {str(e)}")
            return False

    def transcode_video_segment(self,
                                input_path: str,
                                output_path: str,
                                start_time: float,
                                end_time: float,
                                width: int,
                                height: int,
                                codec: str = 'libx264',
                                preset: str = 'medium',
                                crf: int = 23,
                                format: str = 'mp4',
                                audio_codec: str = 'aac',
                                audio_bitrate: str = '128k',
                                use_gpu: bool = True) -> bool:
        """Transcode a specific segment of a video file using ffmpeg."""
        try:
            # Convert start and end time to string format (HH:MM:SS.mmm)
            start_str = self._format_timestamp(start_time)
            end_str = self._format_timestamp(end_time)

            # Calculate duration
            duration = end_time - start_time
            duration_str = self._format_timestamp(duration)

            # Setup input with segment parameters
            stream = ffmpeg.input(input_path, ss=start_str, t=duration_str)

            # Determine encoder
            video_codec = codec
            if use_gpu and self.gpu_enabled:
                hw_encoder = self.get_hardware_encoder()
                if hw_encoder:
                    video_codec = hw_encoder

            # Video & audio stream
            v_stream = stream.video.filter('scale', width, height)
            a_stream = stream.audio

            # Output options
            output_options = {
                'c:v': video_codec,
                'c:a': audio_codec,
                'b:a': audio_bitrate,
                'format': format
            }

            # Add hardware-specific options
            if use_gpu and self.gpu_enabled and video_codec.startswith(('h264_nvenc', 'hevc_nvenc')):
                output_options.update({
                    'preset': 'p4',  # For NVENC
                    'rc': 'vbr'  # Rate control
                })
            elif video_codec in ('libx264', 'libx265'):
                output_options.update({
                    'preset': preset,
                    'crf': str(crf)
                })

            # Run ffmpeg
            ffmpeg.output(v_stream, a_stream, output_path, **output_options).run(
                cmd=self.ffmpeg_path,
                overwrite_output=True,
                quiet=True
            )

            return True

        except Exception as e:
            logger.error(f"Error transcoding video segment: {str(e)}")
            return False

    def create_video_preview(self,
                             input_path: str,
                             output_path: str,
                             duration: int,
                             width: int,
                             height: int,
                             codec: str = 'libx264',
                             preset: str = 'medium',
                             crf: int = 23,
                             format: str = 'mp4',
                             audio_codec: str = 'aac',
                             audio_bitrate: str = '128k',
                             use_gpu: bool = True) -> bool:
        """Create a preview video of specified duration from the beginning of the original video."""
        try:
            # Determine encoder
            video_codec = codec
            if use_gpu and self.gpu_enabled:
                hw_encoder = self.get_hardware_encoder()
                if hw_encoder:
                    video_codec = hw_encoder

            # Setup ffmpeg command
            stream = ffmpeg.input(input_path, t=duration)  # Limit duration

            v_stream = stream.video.filter('scale', width, height)
            a_stream = stream.audio

            # Output options
            output_options = {
                'c:v': video_codec,
                'c:a': audio_codec,
                'b:a': audio_bitrate,
                'format': format
            }

            # Add hardware-specific options
            if use_gpu and self.gpu_enabled and video_codec.startswith(('h264_nvenc', 'hevc_nvenc')):
                output_options.update({
                    'preset': 'p4',  # For NVENC
                    'rc': 'vbr'  # Rate control
                })
            elif video_codec in ('libx264', 'libx265'):
                output_options.update({
                    'preset': preset,
                    'crf': str(crf)
                })

            # Run ffmpeg
            ffmpeg.output(v_stream, a_stream, output_path, **output_options).run(
                cmd=self.ffmpeg_path,
                overwrite_output=True,
                quiet=True
            )

            return True

        except Exception as e:
            logger.error(f"Error creating video preview: {str(e)}")
            return False

    def create_gif_from_video(self,
                              input_path: str,
                              output_path: str,
                              start: float = 0,
                              end: float = 5,
                              fps: int = 10,
                              width: int = 320,
                              height: int = 180,
                              quality: int = 75) -> bool:
        """Create a GIF from a video segment."""
        try:
            # Calculate duration
            duration = end - start

            # Convert start to string format (HH:MM:SS.mmm)
            start_str = self._format_timestamp(start)

            # Create filters for GIF creation
            filters = [
                # Select the time segment and scale
                f"fps={fps}",  # Set frames per second
                f"scale={width}:{height}:flags=lanczos",  # Scale with good quality
            ]

            # Create palette for better quality (optional step)
            palette_path = output_path + ".palette.png"

            # Generate palette
            (
                ffmpeg
                .input(input_path, ss=start_str, t=duration)
                .filter('fps', fps)
                .filter('scale', width, height)
                .filter('palettegen')
                .output(palette_path)
                .run(cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            )

            # Apply palette to create final GIF
            (
                ffmpeg
                .input(input_path, ss=start_str, t=duration)
                .filter('fps', fps)
                .filter('scale', width, height)
                .filter('paletteuse', dither='sierra2_4a')
                .output(output_path)
                .run(cmd=self.ffmpeg_path, overwrite_output=True, quiet=True)
            )

            # Remove temporary palette file
            if os.path.exists(palette_path):
                os.remove(palette_path)

            return True

        except Exception as e:
            logger.error(f"Error creating GIF from video: {str(e)}")
            # Clean up if failure
            if os.path.exists(palette_path):
                os.remove(palette_path)
            return False

    def extract_video_thumbnail(self,
                                input_path: str,
                                output_path: str,
                                timestamp: str,
                                width: int,
                                height: int,
                                format: str = 'jpg',
                                quality: int = 90) -> bool:
        """Extract a thumbnail from a video at the specified timestamp."""
        try:
            # Setup ffmpeg command
            stream = ffmpeg.input(input_path, ss=timestamp)  # Seek to timestamp

            # Extract single frame and scale
            v_stream = stream.video.filter('scale', width, height).filter('thumbnail', 1)

            # Quality options
            output_options = {}
            if format == 'jpg':
                output_options['q:v'] = quality  # JPEG quality (1-31, lower is better)
            elif format == 'webp':
                output_options['quality'] = quality  # WebP quality (0-100)
            elif format == 'png':
                output_options['compression_level'] = 3  # PNG compression (0-9)

            # Run ffmpeg
            ffmpeg.output(v_stream, output_path, vframes=1, **output_options).run(
                cmd=self.ffmpeg_path,
                overwrite_output=True,
                quiet=True
            )

            return True

        except Exception as e:
            logger.error(f"Error extracting video thumbnail: {str(e)}")
            return False

    def transcode_image(self,
                        input_path: str,
                        output_path: str,
                        resize: bool = False,
                        width: Optional[int] = None,
                        height: Optional[int] = None,
                        maintain_aspect_ratio: bool = True,
                        format: str = 'webp',
                        quality: int = 85) -> bool:
        """Transcode an image with optional resizing."""
        try:
            # Setup ffmpeg command
            stream = ffmpeg.input(input_path)

            # Apply scaling if resize is True
            if resize and width and height:
                if maintain_aspect_ratio:
                    v_stream = stream.filter('scale', width, height, force_original_aspect_ratio='decrease')
                else:
                    v_stream = stream.filter('scale', width, height)
            else:
                v_stream = stream

            # Quality options
            output_options = {}
            if format == 'jpg':
                output_options['q:v'] = quality  # JPEG quality (1-31, lower is better)
            elif format == 'webp':
                output_options['quality'] = quality  # WebP quality (0-100)
            elif format == 'png':
                output_options['compression_level'] = 3  # PNG compression (0-9)

            # Run ffmpeg
            ffmpeg.output(v_stream, output_path, format=format, **output_options).run(
                cmd=self.ffmpeg_path,
                overwrite_output=True,
                quiet=True
            )

            return True

        except Exception as e:
            logger.error(f"Error transcoding image: {str(e)}")
            return False

    def check_gpu_availability(self) -> Tuple[bool, str]:
        """Check if GPU is available for transcoding."""
        if not self.gpu_enabled:
            return False, "GPU support disabled in configuration"

        try:
            if self.gpu_type == 'nvidia':
                # Check for NVIDIA GPU
                result = subprocess.run(['nvidia-smi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    return True, "NVIDIA GPU available"
                else:
                    return False, "NVIDIA GPU not found or drivers not installed"

            elif self.gpu_type == 'amd':
                # Check for AMD GPU
                result = subprocess.run(['rocm-smi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if result.returncode == 0:
                    return True, "AMD GPU available"
                else:
                    return False, "AMD GPU not found or drivers not installed"

            return False, f"Unsupported GPU type: {self.gpu_type}"

        except Exception as e:
            return False, f"Error checking GPU availability: {str(e)}"

    def get_supported_hw_encoders(self) -> List[str]:
        """Get list of supported hardware encoders on this system."""
        try:
            # Get ffmpeg encoders
            result = subprocess.run(
                [self.ffmpeg_path, '-encoders'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            encoders = []
            in_encoders_section = False

            for line in result.stdout.splitlines():
                if not in_encoders_section:
                    if line.startswith('  V'):
                        in_encoders_section = True
                    continue

                if line.startswith(' '):
                    # Check for hardware encoders
                    if any(x in line for x in ['nvenc', 'amf', 'qsv', 'v4l2', 'vaapi']):
                        parts = line.split()
                        if parts and len(parts) >= 2:
                            encoders.append(parts[1])

            return encoders

        except Exception as e:
            logger.error(f"Error getting supported encoders: {str(e)}")
            return []

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to ffmpeg timestamp format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"