#!/usr/bin/env python3
"""
Universal Media Converter - Consolidated converter combining WebP and standard formats
Supports: Image/Video → WebP, JPG, MP4 with comprehensive parameter control
Combines functionality from MediaToWebPConverter and MediaTranscodeConverter
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional


class UniversalMediaConverter:
    def __init__(self):
        self.ffmpeg_path = "/opt/homebrew/bin/ffmpeg"
        
        # Supported file extensions
        self.video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.flv', '.wmv', '.m2ts', '.ts'}
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.heic', '.raw'}
        
        # Output formats
        self.supported_outputs = {'webp', 'jpg', 'jpeg', 'mp4'}

    def _detect_media_type(self, input_path: str) -> str:
        """Detect if input is video or image"""
        ext = Path(input_path).suffix.lower()
        
        if ext in self.video_extensions:
            return 'video'
        elif ext in self.image_extensions:
            return 'image'
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _detect_output_format(self, output_path: str) -> str:
        """Detect output format from extension"""
        ext = Path(output_path).suffix.lower().lstrip('.')
        if ext in self.supported_outputs:
            return ext
        else:
            raise ValueError(f"Unsupported output format: {ext}")

    def _is_animated_image(self, input_path: str) -> bool:
        """Check if image is animated (GIF/WebP)"""
        ext = Path(input_path).suffix.lower()
        return ext in {'.gif', '.webp'}

    def convert(self,
                input_path: str,
                output_path: str,
                
                # Common settings
                width: Optional[int] = None,
                height: Optional[int] = None,
                quality: int = 85,
                
                # Video timing settings
                fps: Optional[float] = None,
                duration: Optional[float] = None,
                start_time: float = 0,
                speed: float = 1.0,
                
                # Image/Video filter settings
                contrast: float = 1.0,
                brightness: float = 0.0,
                saturation: float = 1.0,
                gamma: float = 1.0,
                enable_denoising: bool = False,
                enable_sharpening: bool = False,
                auto_filter: bool = False,
                
                # WebP-specific settings
                lossless: bool = False,
                method: int = 4,
                preset: str = "default",
                near_lossless: Optional[int] = None,
                alpha_quality: int = 100,
                alpha_method: int = 1,
                animated: bool = True,
                loop: int = 0,
                pass_count: int = 1,
                target_size: Optional[int] = None,
                save_frames: bool = False,
                
                # JPG-specific settings
                jpeg_quality: int = 90,
                optimize: bool = True,
                progressive: bool = False,
                
                # MP4-specific settings
                codec: str = "h264",
                crf: int = 23,
                mp4_preset: str = "medium",
                bitrate: Optional[str] = None,
                max_bitrate: Optional[str] = None,
                buffer_size: Optional[str] = None,
                profile: str = "high",
                level: str = "4.1",
                pixel_format: str = "yuv420p",
                
                # Audio settings (MP4)
                audio_codec: str = "aac",
                audio_bitrate: str = "128k",
                audio_sample_rate: int = 44100,
                
                # System settings
                two_pass: bool = False,
                hardware_accel: bool = False,
                verbose: bool = True
                ) -> Dict[str, Any]:
        """
        Universal media conversion with format auto-detection
        
        Returns:
            Dict with conversion results: success, output_path, file_size, etc.
        """
        
        try:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Input file not found: {input_path}")
            
            # Detect input and output types
            input_type = self._detect_media_type(input_path)
            output_format = self._detect_output_format(output_path)
            
            # Create output directory
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Build command based on output format
            if output_format == 'webp':
                cmd = self._build_webp_command(
                    input_path=input_path,
                    output_path=output_path,
                    input_type=input_type,
                    width=width, height=height, quality=quality,
                    fps=fps, duration=duration, start_time=start_time, speed=speed,
                    contrast=contrast, brightness=brightness, saturation=saturation,
                    enable_denoising=enable_denoising, enable_sharpening=enable_sharpening,
                    lossless=lossless, method=method, preset=preset,
                    near_lossless=near_lossless, alpha_quality=alpha_quality, alpha_method=alpha_method,
                    animated=animated, loop=loop, pass_count=pass_count, target_size=target_size,
                    auto_filter=auto_filter, save_frames=save_frames, verbose=verbose
                )
            elif output_format in ['jpg', 'jpeg']:
                cmd = self._build_jpg_command(
                    input_path=input_path,
                    output_path=output_path,
                    width=width, height=height,
                    jpeg_quality=jpeg_quality, optimize=optimize, progressive=progressive,
                    contrast=contrast, brightness=brightness, saturation=saturation, gamma=gamma,
                    enable_denoising=enable_denoising, enable_sharpening=enable_sharpening,
                    verbose=verbose
                )
            elif output_format == 'mp4':
                cmd = self._build_mp4_command(
                    input_path=input_path,
                    output_path=output_path,
                    width=width, height=height,
                    codec=codec, crf=crf, preset=mp4_preset,
                    fps=fps, duration=duration, start_time=start_time,
                    bitrate=bitrate, max_bitrate=max_bitrate, buffer_size=buffer_size,
                    profile=profile, level=level, pixel_format=pixel_format,
                    audio_codec=audio_codec, audio_bitrate=audio_bitrate, audio_sample_rate=audio_sample_rate,
                    two_pass=two_pass, hardware_accel=hardware_accel,
                    contrast=contrast, brightness=brightness, saturation=saturation, gamma=gamma,
                    enable_denoising=enable_denoising, enable_sharpening=enable_sharpening,
                    verbose=verbose
                )
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
            
            if verbose:
                print(f"🎬 Converting: {input_path} ({input_type}) → {output_path} ({output_format.upper()})")
                print(f"⚙️  Command: {' '.join(cmd)}")
                print("-" * 80)
            
            # Execute conversion
            start_time_exec = time.time()
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            end_time_exec = time.time()
            conversion_time = end_time_exec - start_time_exec
            
            # Check result
            if process.returncode != 0:
                error_msg = process.stderr
                if verbose:
                    print(f"❌ Error: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "command": ' '.join(cmd),
                    "input_type": input_type,
                    "output_format": output_format
                }
            
            # Get output file info
            result = self._get_output_info(output_path, conversion_time, input_type, output_format, verbose)
            result["command"] = ' '.join(cmd)
            result["success"] = True
            result["input_type"] = input_type
            result["output_format"] = output_format
            
            if verbose:
                self._print_result_summary(result)
            
            return result
            
        except Exception as e:
            if verbose:
                print(f"❌ Exception: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "command": ' '.join(cmd) if 'cmd' in locals() else "",
                "input_type": input_type if 'input_type' in locals() else "unknown",
                "output_format": output_format if 'output_format' in locals() else "unknown"
            }

    def _build_webp_command(self, **kwargs) -> list:
        """Build FFmpeg command for WebP conversion (from MediaToWebPConverter logic)"""
        cmd = [self.ffmpeg_path, "-y"]
        
        input_type = kwargs['input_type']
        
        # Input handling
        if input_type == 'video' and kwargs['start_time'] > 0:
            cmd.extend(["-ss", str(kwargs['start_time'])])
        
        cmd.extend(["-i", kwargs['input_path']])
        
        # Duration for video
        if input_type == 'video' and kwargs['duration']:
            cmd.extend(["-t", str(kwargs['duration'])])
        
        # Build video filters
        filters = []
        
        # Scale filter
        if kwargs['width'] or kwargs['height']:
            if kwargs['width'] and kwargs['height']:
                filters.append(f"scale={kwargs['width']}:{kwargs['height']}")
            elif kwargs['width'] and not kwargs['height']:
                filters.append(f"scale={kwargs['width']}:-1")
            elif kwargs['height'] and not kwargs['width']:
                filters.append(f"scale=-1:{kwargs['height']}")
        
        # FPS filter for video
        if input_type == 'video' and kwargs['fps']:
            filters.append(f"fps={kwargs['fps']}")
        
        # Speed filter for video
        if input_type == 'video' and kwargs['speed'] != 1.0:
            filters.append(f"setpts={1/kwargs['speed']}*PTS")
        
        # Color adjustments
        if (kwargs['contrast'] != 1.0 or kwargs['brightness'] != 0.0 or kwargs['saturation'] != 1.0):
            eq_filter = f"eq=contrast={kwargs['contrast']}:brightness={kwargs['brightness']}:saturation={kwargs['saturation']}"
            filters.append(eq_filter)
        
        # Denoising
        if kwargs['enable_denoising']:
            filters.append("hqdn3d")
        
        # Sharpening
        if kwargs['enable_sharpening']:
            filters.append("unsharp=5:5:1.0")
        
        # Apply filters
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        
        # WebP codec
        cmd.extend(["-c:v", "libwebp"])
        
        # WebP-specific parameters (only use FFmpeg libwebp supported options)
        if kwargs['lossless']:
            cmd.extend(["-lossless", "1"])
        else:
            cmd.extend(["-quality", str(kwargs['quality'])])
        
        # Only use valid preset values for FFmpeg libwebp
        valid_presets = ['default', 'picture', 'photo', 'drawing', 'icon', 'text']
        if kwargs['preset'] in valid_presets:
            # Map preset string to FFmpeg preset number
            preset_map = {
                'default': 0, 'picture': 1, 'photo': 2, 
                'drawing': 3, 'icon': 4, 'text': 5
            }
            cmd.extend(["-preset", str(preset_map[kwargs['preset']])])
        
        # Animation settings for video or animated images
        if input_type == 'video' or self._is_animated_image(kwargs['input_path']):
            if kwargs['animated']:
                cmd.extend(["-loop", str(kwargs['loop'])])  # This actually works with FFmpeg libwebp!
            else:
                cmd.extend(["-frames:v", "1"])  # Single frame for static output
        
        # Additional WebP parameters that work with FFmpeg libwebp
        # Note: Some are undocumented but functional
        if kwargs.get('method') is not None:
            cmd.extend(["-method", str(kwargs['method'])])
        
        if kwargs.get('alpha_quality') is not None:
            cmd.extend(["-alpha_quality", str(kwargs['alpha_quality'])])
        
        if kwargs.get('near_lossless') is not None:
            cmd.extend(["-near_lossless", str(kwargs['near_lossless'])])
        
        if kwargs.get('target_size') is not None:
            cmd.extend(["-target_size", str(kwargs['target_size'] * 1024)])  # Convert KB to bytes
        
        # Note: alpha_method is NOT supported and will cause errors
        # auto_filter and pass_count are also not supported by FFmpeg libwebp
        
        # Verbose/quiet
        if not kwargs['verbose']:
            cmd.extend(["-loglevel", "quiet"])
        
        # Output file
        cmd.append(kwargs['output_path'])
        
        return cmd

    def _build_jpg_command(self, **kwargs) -> list:
        """Build FFmpeg command for JPG conversion (from MediaTranscodeConverter logic)"""
        cmd = [self.ffmpeg_path, "-y"]
        
        # Input file
        cmd.extend(["-i", kwargs['input_path']])
        
        # Video filters
        filters = []
        
        # Scale filter
        if kwargs['width'] or kwargs['height']:
            if kwargs['width'] and kwargs['height']:
                filters.append(f"scale={kwargs['width']}:{kwargs['height']}")
            elif kwargs['width'] and not kwargs['height']:
                filters.append(f"scale={kwargs['width']}:-1")
            elif kwargs['height'] and not kwargs['width']:
                filters.append(f"scale=-1:{kwargs['height']}")
        
        # Color adjustments
        if (kwargs['contrast'] != 1.0 or kwargs['brightness'] != 0.0 or 
                kwargs['saturation'] != 1.0 or kwargs['gamma'] != 1.0):
            eq_filter = f"eq=contrast={kwargs['contrast']}:brightness={kwargs['brightness']}:saturation={kwargs['saturation']}:gamma={kwargs['gamma']}"
            filters.append(eq_filter)
        
        # Denoising
        if kwargs['enable_denoising']:
            filters.append("hqdn3d")
        
        # Sharpening
        if kwargs['enable_sharpening']:
            filters.append("unsharp=5:5:1.0")
        
        # Apply filters
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        
        # JPEG specific parameters
        cmd.extend(["-c:v", "mjpeg"])
        cmd.extend(["-q:v", str(100 - kwargs['jpeg_quality'])])  # FFmpeg uses inverse scale
        
        # JPEG optimization
        if kwargs['optimize']:
            cmd.extend(["-huffman", "optimal"])
        
        # Progressive JPEG
        if kwargs['progressive']:
            cmd.extend(["-flags", "+global_header"])
        
        # Output format
        cmd.extend(["-f", "image2"])
        
        # Verbose/quiet
        if not kwargs['verbose']:
            cmd.extend(["-loglevel", "quiet"])
        
        # Output file
        cmd.append(kwargs['output_path'])
        
        return cmd

    def _build_mp4_command(self, **kwargs) -> list:
        """Build FFmpeg command for MP4 conversion (from MediaTranscodeConverter logic)"""
        cmd = [self.ffmpeg_path, "-y"]
        
        # Hardware acceleration
        if kwargs['hardware_accel']:
            cmd.extend(["-hwaccel", "auto"])
        
        # Input parameters
        if kwargs['start_time'] > 0:
            cmd.extend(["-ss", str(kwargs['start_time'])])
        
        cmd.extend(["-i", kwargs['input_path']])
        
        # Duration
        if kwargs['duration']:
            cmd.extend(["-t", str(kwargs['duration'])])
        
        # Video filters
        filters = []
        
        # Scale filter
        if kwargs['width'] or kwargs['height']:
            if kwargs['width'] and kwargs['height']:
                filters.append(f"scale={kwargs['width']}:{kwargs['height']}")
            elif kwargs['width'] and not kwargs['height']:
                filters.append(f"scale={kwargs['width']}:-1")
            elif kwargs['height'] and not kwargs['width']:
                filters.append(f"scale=-1:{kwargs['height']}")
        
        # FPS filter
        if kwargs['fps']:
            filters.append(f"fps={kwargs['fps']}")
        
        # Color adjustments
        if (kwargs['contrast'] != 1.0 or kwargs['brightness'] != 0.0 or 
                kwargs['saturation'] != 1.0 or kwargs['gamma'] != 1.0):
            eq_filter = f"eq=contrast={kwargs['contrast']}:brightness={kwargs['brightness']}:saturation={kwargs['saturation']}:gamma={kwargs['gamma']}"
            filters.append(eq_filter)
        
        # Denoising
        if kwargs['enable_denoising']:
            filters.append("hqdn3d")
        
        # Sharpening
        if kwargs['enable_sharpening']:
            filters.append("unsharp=5:5:1.0")
        
        # Apply filters
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        
        # Video codec
        if kwargs['codec'] == 'h265':
            cmd.extend(["-c:v", "libx265"])
        else:
            cmd.extend(["-c:v", "libx264"])
        
        # CRF (Constant Rate Factor)
        cmd.extend(["-crf", str(kwargs['crf'])])
        
        # Preset
        cmd.extend(["-preset", kwargs['preset']])
        
        # Profile and level
        cmd.extend(["-profile:v", kwargs['profile']])
        cmd.extend(["-level", kwargs['level']])
        
        # Pixel format
        cmd.extend(["-pix_fmt", kwargs['pixel_format']])
        
        # Bitrate settings
        if kwargs['bitrate']:
            cmd.extend(["-b:v", kwargs['bitrate']])
        if kwargs['max_bitrate']:
            cmd.extend(["-maxrate", kwargs['max_bitrate']])
        if kwargs['buffer_size']:
            cmd.extend(["-bufsize", kwargs['buffer_size']])
        
        # Audio settings
        if kwargs['audio_codec'] == 'none':
            cmd.extend(["-an"])
        else:
            if kwargs['audio_codec'] == 'aac':
                cmd.extend(["-c:a", "aac"])
            elif kwargs['audio_codec'] == 'mp3':
                cmd.extend(["-c:a", "mp3"])
            
            cmd.extend(["-b:a", kwargs['audio_bitrate']])
            cmd.extend(["-ar", str(kwargs['audio_sample_rate'])])
        
        # Output format
        cmd.extend(["-f", "mp4"])
        cmd.extend(["-movflags", "+faststart"])  # Enable streaming
        
        # Verbose/quiet
        if not kwargs['verbose']:
            cmd.extend(["-loglevel", "quiet"])
        
        # Output file
        cmd.append(kwargs['output_path'])
        
        return cmd

    def _get_output_info(self, output_path: str, conversion_time: float, input_type: str, output_format: str, verbose: bool) -> Dict[str, Any]:
        """Get information about the output file"""
        try:
            if not os.path.exists(output_path):
                return {"error": "Output file not created"}
            
            # File size
            file_size = os.path.getsize(output_path)
            file_size_mb = file_size / (1024 * 1024)
            
            info = {
                "output_path": output_path,
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size_mb, 2),
                "conversion_time_seconds": round(conversion_time, 2),
                "input_type": input_type,
                "output_format": output_format
            }
            
            # Get media info using ffprobe
            probe_cmd = [
                "/opt/homebrew/bin/ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", output_path
            ]
            
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True)
            
            if probe_result.returncode == 0:
                try:
                    probe_data = json.loads(probe_result.stdout)
                    
                    if 'streams' in probe_data and probe_data['streams']:
                        video_stream = probe_data['streams'][0]
                        info.update({
                            "width": video_stream.get('width', 0),
                            "height": video_stream.get('height', 0),
                            "duration": float(video_stream.get('duration', 0)) if video_stream.get('duration') else 0,
                            "codec": video_stream.get('codec_name'),
                            "pixel_format": video_stream.get('pix_fmt')
                        })
                        
                        if output_format in ['mp4', 'webp']:
                            info.update({
                                "fps": eval(video_stream.get('r_frame_rate', '0/1')) if video_stream.get('r_frame_rate') != '0/1' else 0,
                                "frames": int(video_stream.get('nb_frames', 0))
                            })
                    
                    if 'format' in probe_data:
                        format_info = probe_data['format']
                        info.update({
                            "format_name": format_info.get('format_name'),
                            "bit_rate": int(format_info.get('bit_rate', 0))
                        })
                except json.JSONDecodeError:
                    pass
            
            # Set defaults if not found
            if 'width' not in info:
                info['width'] = 0
            if 'height' not in info:
                info['height'] = 0
            if 'codec' not in info:
                info['codec'] = output_format
            
            return info
            
        except Exception as e:
            return {"error": f"Failed to get output info: {str(e)}"}

    def _print_result_summary(self, result: Dict[str, Any]):
        """Print conversion result summary"""
        print("\n" + "=" * 80)
        print(f"🎯 {result.get('input_type', 'MEDIA').upper()} → {result.get('output_format', 'FORMAT').upper()} CONVERSION RESULTS")
        print("=" * 80)
        
        if result.get('success'):
            print(f"✅ Status: SUCCESS")
            print(f"📁 Output: {result.get('output_path')}")
            print(f"📏 Size: {result.get('file_size_mb', 0):.2f} MB ({result.get('file_size_bytes', 0):,} bytes)")
            print(f"⏱️  Time: {result.get('conversion_time_seconds', 0):.2f} seconds")
            
            if result.get('width') and result.get('height'):
                print(f"📐 Dimensions: {result.get('width')}×{result.get('height')}")
            
            if result.get('codec'):
                print(f"🎥 Codec: {result.get('codec')}")
            
            if result.get('duration'):
                print(f"⏰ Duration: {result.get('duration'):.2f} seconds")
            
            if result.get('fps'):
                print(f"🎞️  FPS: {result.get('fps'):.2f}")
            
            if result.get('bit_rate'):
                bitrate_kbps = result.get('bit_rate') / 1000
                print(f"📊 Bitrate: {bitrate_kbps:.1f} kbps")
        
        else:
            print(f"❌ Status: FAILED")
            print(f"🚫 Error: {result.get('error', 'Unknown error')}")
        
        print("=" * 80)


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description="Universal Media Converter - WebP, JPG, MP4 support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Image/Video to WebP
  python universal_media_converter.py input.jpg output.webp --quality 90 --width 800
  python universal_media_converter.py input.mp4 output.webp --fps 15 --duration 6
  
  # Image to JPG
  python universal_media_converter.py input.png output.jpg --jpeg-quality 95 --width 800
  
  # Video to MP4 
  python universal_media_converter.py input.avi output.mp4 --codec h264 --crf 20
        """
    )
    
    # Required arguments
    parser.add_argument("input", help="Input file path")
    parser.add_argument("output", help="Output file path")
    
    # Common settings
    parser.add_argument("--width", type=int, help="Output width (pixels)")
    parser.add_argument("--height", type=int, help="Output height (pixels)")
    parser.add_argument("--quality", type=int, default=85, help="General quality 0-100")
    
    # Video timing
    parser.add_argument("--fps", type=float, help="Output FPS")
    parser.add_argument("--duration", type=float, help="Output duration (seconds)")
    parser.add_argument("--start-time", type=float, default=0, help="Start time (seconds)")
    parser.add_argument("--speed", type=float, default=1.0, help="Speed multiplier")
    
    # Filter settings
    parser.add_argument("--contrast", type=float, default=1.0, help="Contrast adjustment")
    parser.add_argument("--brightness", type=float, default=0.0, help="Brightness adjustment")
    parser.add_argument("--saturation", type=float, default=1.0, help="Saturation adjustment")
    parser.add_argument("--gamma", type=float, default=1.0, help="Gamma adjustment")
    parser.add_argument("--denoise", action="store_true", help="Enable denoising")
    parser.add_argument("--sharpen", action="store_true", help="Enable sharpening")
    
    # WebP settings
    parser.add_argument("--lossless", action="store_true", help="WebP lossless mode")
    parser.add_argument("--method", type=int, default=4, help="WebP method 0-6")
    parser.add_argument("--preset", choices=["default", "photo", "picture", "drawing", "icon", "text"], default="default")
    parser.add_argument("--animated", action="store_true", default=True, help="Enable animation for WebP")
    parser.add_argument("--loop", type=int, default=0, help="WebP loop count (0=infinite)")
    
    # JPG settings
    parser.add_argument("--jpeg-quality", type=int, default=90, help="JPEG quality 0-100")
    parser.add_argument("--optimize", action="store_true", help="Optimize JPEG")
    parser.add_argument("--progressive", action="store_true", help="Progressive JPEG")
    
    # MP4 settings
    parser.add_argument("--codec", choices=["h264", "h265"], default="h264", help="Video codec")
    parser.add_argument("--crf", type=int, default=23, help="CRF value 0-51 (lower=better)")
    parser.add_argument("--mp4-preset", choices=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"], default="medium")
    parser.add_argument("--bitrate", help="Video bitrate (e.g., 2M, 5000k)")
    parser.add_argument("--audio-codec", choices=["aac", "mp3", "none"], default="aac")
    parser.add_argument("--audio-bitrate", default="128k", help="Audio bitrate")
    
    # System settings
    parser.add_argument("--two-pass", action="store_true", help="Two-pass encoding")
    parser.add_argument("--hardware-accel", action="store_true", help="Hardware acceleration")
    parser.add_argument("--quiet", action="store_true", help="Reduce output")
    
    args = parser.parse_args()
    
    # Create converter
    converter = UniversalMediaConverter()
    
    # Convert
    result = converter.convert(
        input_path=args.input,
        output_path=args.output,
        width=args.width,
        height=args.height,
        quality=args.quality,
        fps=args.fps,
        duration=args.duration,
        start_time=args.start_time,
        speed=args.speed,
        contrast=args.contrast,
        brightness=args.brightness,
        saturation=args.saturation,
        gamma=args.gamma,
        enable_denoising=args.denoise,
        enable_sharpening=args.sharpen,
        lossless=args.lossless,
        method=args.method,
        preset=args.preset,
        animated=args.animated,
        loop=args.loop,
        jpeg_quality=args.jpeg_quality,
        optimize=args.optimize,
        progressive=args.progressive,
        codec=args.codec,
        crf=args.crf,
        mp4_preset=args.mp4_preset,
        bitrate=args.bitrate,
        audio_codec=args.audio_codec,
        audio_bitrate=args.audio_bitrate,
        two_pass=args.two_pass,
        hardware_accel=args.hardware_accel,
        verbose=not args.quiet
    )
    
    # Exit with appropriate code
    sys.exit(0 if result.get('success') else 1)


if __name__ == "__main__":
    main()