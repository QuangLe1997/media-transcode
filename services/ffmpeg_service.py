import logging
import os
import platform
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Dict, List, Optional

import ffmpeg

logger = logging.getLogger(__name__)

# Lock cho singleton pattern
_ffmpeg_service_lock = threading.Lock()
_ffmpeg_service_instance = None


class FFmpegConfig:
    """Quản lý cấu hình FFmpeg và khả năng tương thích."""

    def __init__(self, ffmpeg_path: str, ffprobe_path: str):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.version = self._get_ffmpeg_version()
        self.capabilities = self._detect_capabilities()

    def _get_ffmpeg_version(self) -> str:
        """Lấy phiên bản FFmpeg."""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if result.returncode == 0:
                first_line = result.stdout.splitlines()[0]
                return first_line
            return "Unknown"
        except Exception:
            return "Unknown"

    def _detect_capabilities(self) -> Dict:
        """Phát hiện khả năng của FFmpeg."""
        capabilities = {
            'encoders': [],
            'hw_encoders': [],
            'decoders': [],
            'filters': [],
            'hw_accelerations': []
        }

        # Phát hiện encoders
        try:
            encoders = subprocess.run(
                [self.ffmpeg_path, '-encoders'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if encoders.returncode == 0:
                for line in encoders.stdout.splitlines():
                    if line.startswith(' '):
                        parts = line.split()
                        if len(parts) >= 2:
                            capabilities['encoders'].append(parts[1])
                            # Check if it's a hardware encoder
                            if any(hw in parts[1] for hw in ['nvenc', 'amf', 'qsv', 'vaapi', 'videotoolbox']):
                                capabilities['hw_encoders'].append(parts[1])
        except Exception:
            pass

        # Phát hiện filters
        try:
            filters = subprocess.run(
                [self.ffmpeg_path, '-filters'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if filters.returncode == 0:
                for line in filters.stdout.splitlines():
                    if line.startswith(' '):
                        parts = line.split()
                        if len(parts) >= 2:
                            capabilities['filters'].append(parts[1])
        except Exception:
            pass

        # Phát hiện hw acceleration
        acceleration_types = ['nvenc', 'amf', 'qsv', 'videotoolbox', 'vaapi']
        for acc_type in acceleration_types:
            try:
                # Thử tìm một encoder đại diện cho mỗi loại hw acceleration
                encoder_name = f'h264_{acc_type}' if acc_type != 'vaapi' else 'h264_vaapi'
                help_output = subprocess.run(
                    [self.ffmpeg_path, '-h', f'encoder={encoder_name}'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if help_output.returncode == 0 and len(help_output.stdout) > 0:
                    capabilities['hw_accelerations'].append(acc_type)
            except Exception:
                pass

        return capabilities

    def is_encoder_supported(self, encoder: str) -> bool:
        """Kiểm tra xem encoder có được hỗ trợ không."""
        return encoder in self.capabilities['encoders']

    def get_best_encoder(self, codec: str, hw_acceleration: str) -> str:
        """Lấy encoder tốt nhất cho codec và tăng tốc phần cứng cụ thể."""
        # Ánh xạ từ codec và acceleration đến encoder
        encoder_map = {
            'h264': {
                'nvenc': 'h264_nvenc',
                'amf': 'h264_amf',
                'qsv': 'h264_qsv',
                'vaapi': 'h264_vaapi',
                'videotoolbox': 'h264_videotoolbox',
                'none': 'libx264'
            },
            'hevc': {
                'nvenc': 'hevc_nvenc',
                'amf': 'hevc_amf',
                'qsv': 'hevc_qsv',
                'vaapi': 'hevc_vaapi',
                'videotoolbox': 'hevc_videotoolbox',
                'none': 'libx265'
            }
        }

        # Mặc định software encoder
        default_encoder = 'libx264' if codec == 'h264' else 'libx265'

        # Kiểm tra xem codec có trong ánh xạ không
        if codec not in encoder_map:
            return default_encoder

        # Kiểm tra xem hw_acceleration có trong ánh xạ không
        if hw_acceleration not in encoder_map[codec]:
            return encoder_map[codec]['none']

        # Lấy encoder phù hợp
        encoder = encoder_map[codec][hw_acceleration]

        # Kiểm tra xem encoder có được hỗ trợ không
        if self.is_encoder_supported(encoder):
            return encoder

        # Fallback to software encoder
        return encoder_map[codec]['none']


class EncoderFactory:
    """Factory class để tạo và cấu hình encoder cho mỗi nền tảng."""

    @staticmethod
    def create_encoder_options(hw_acceleration: str, codec: str, crf: int = 23, preset: str = 'medium') -> Dict:
        """Tạo tùy chọn encoder phù hợp cho nền tảng và phần cứng cụ thể."""
        options = {}

        if hw_acceleration == 'nvenc':
            # NVIDIA GPU
            options = {
                'preset': 'p4',
                'b:v': '5M'
            }
            # Thêm các tùy chọn nâng cao nếu cần
            try:
                # Kiểm tra phiên bản driver (chỉ trên Linux/Windows)
                if platform.system() in ('Linux', 'Windows'):
                    nvidia_smi = subprocess.run(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
                                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    driver_version = nvidia_smi.stdout.strip() if nvidia_smi.returncode == 0 else ""

                    # Thêm tùy chọn dựa trên phiên bản driver
                    if driver_version:
                        major = int(driver_version.split('.')[0])
                        if major >= 450:  # Newer drivers support better options
                            options.update({
                                'rc:v': 'vbr',
                                'cq:v': str(crf),
                                'spatial-aq': '1',  # Spatial AQ for better quality
                                'temporal-aq': '1'  # Temporal AQ
                            })
            except Exception as e:
                # Fallback options if detection fails
                logger.warning(f"Error detecting NVIDIA driver version: {e}")
                options.update({
                    'b:v': '5M',
                    'maxrate:v': '10M',
                    'bufsize:v': '10M'
                })

        elif hw_acceleration == 'amf':
            # AMD GPU
            options = {
                'quality': 'quality',
                'b:v': '5M'
            }
            # Một số phiên bản có thể không hỗ trợ các tùy chọn này
            try:
                amf_help = subprocess.run(['ffmpeg', '-h', 'encoder=h264_amf'],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if 'usage: rc' in amf_help.stdout.lower():
                    options['rc'] = 'vbr_latency'
            except Exception:
                pass

        elif hw_acceleration == 'qsv':
            # Intel QuickSync
            options = {
                'b:v': '5M',
                'maxrate': '10M',
            }
            # Thêm các tùy chọn nâng cao nếu được hỗ trợ
            try:
                qsv_help = subprocess.run(['ffmpeg', '-h', 'encoder=h264_qsv'],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if 'look_ahead' in qsv_help.stdout:
                    options['look_ahead'] = '1'
            except Exception:
                pass

        elif hw_acceleration == 'videotoolbox':
            # macOS (Apple Silicon or Intel)
            options = {
                'b:v': '5M',
                'tag:v': 'avc1',
                'allow_sw': '1'  # Allow software fallback if needed
            }
            # Kiểm tra xem videotoolbox có hỗ trợ cài đặt quality không
            try:
                vtb_help = subprocess.run(['ffmpeg', '-h', 'encoder=h264_videotoolbox'],
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # Trong một số phiên bản mới, có thể hỗ trợ tùy chọn chất lượng
                if 'q:v' in vtb_help.stdout:
                    options['q:v'] = str(min(crf * 5, 100))  # Convert CRF to quality scale (0-100)
            except Exception:
                pass

        elif hw_acceleration == 'vaapi':
            # Linux VAAPI
            options = {
                'b:v': '5M'
            }
            # Thêm các tùy chọn nâng cao nếu được hỗ trợ
            try:
                vaapi_help = subprocess.run(['ffmpeg', '-h', 'encoder=h264_vaapi'],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if 'qp' in vaapi_help.stdout:
                    options['qp'] = str(crf)
            except Exception:
                pass

        else:
            # Software encoding (CPU)
            if codec in ('h264', 'libx264', 'hevc', 'libx265'):
                options = {
                    'preset': preset,
                    'crf': str(crf)
                }
            else:
                # Fallback for other codecs
                options = {
                    'b:v': '5M'
                }

        return options


class FFmpegService:
    def __init__(self, ffmpeg_path: Optional[str] = None, ffprobe_path: Optional[str] = None, gpu_enabled: bool = True):
        # Tự động phát hiện đường dẫn nếu không được cung cấp
        self.ffmpeg_path = ffmpeg_path or self._find_ffmpeg()
        self.ffprobe_path = ffprobe_path or self._find_ffprobe()
        self.gpu_enabled = gpu_enabled

        # Phát hiện hệ thống và GPU
        self.system_info = self._detect_system()
        self.gpu_info = self._detect_gpu()

        # Thiết lập GPU type dựa trên GPU được phát hiện
        self.gpu_type = self.gpu_info.get('type', 'none')
        self.hw_acceleration = self._detect_hw_acceleration()

        # Tạo cấu hình FFmpeg
        self.config = FFmpegConfig(self.ffmpeg_path, self.ffprobe_path)

        # Ghi log thông tin hệ thống
        logger.info(f"System: {self.system_info['os']} {self.system_info['arch']}")
        logger.info(f"FFmpeg: {self.ffmpeg_path}")
        logger.info(f"FFprobe: {self.ffprobe_path}")
        logger.info(f"FFmpeg version: {self.config.version}")
        logger.info(f"GPU: {self.gpu_info['name'] if self.gpu_info else 'None'}")
        logger.info(f"HW Acceleration: {self.hw_acceleration}")
        logger.info(f"Supported HW Encoders: {', '.join(self.config.capabilities['hw_encoders'])}")

        # Use absolute paths
        if self.ffmpeg_path:
            os.environ['FFMPEG_BINARY'] = self.ffmpeg_path
        if self.ffprobe_path:
            os.environ['FFPROBE_BINARY'] = self.ffprobe_path

    def _find_ffmpeg(self) -> str:
        """Tự động tìm đường dẫn đến ffmpeg executable."""
        # Thử tìm trong PATH
        ffmpeg_path = shutil.which('ffmpeg')
        if ffmpeg_path:
            return ffmpeg_path

        # Các vị trí phổ biến theo hệ thống
        if platform.system() == 'Darwin':  # macOS
            common_paths = [
                '/usr/local/bin/ffmpeg',
                '/opt/homebrew/bin/ffmpeg',
                '/opt/local/bin/ffmpeg'
            ]
        elif platform.system() == 'Linux':
            common_paths = [
                '/usr/bin/ffmpeg',
                '/usr/local/bin/ffmpeg'
            ]
        else:  # Windows
            common_paths = [
                r'C:\ffmpeg\bin\ffmpeg.exe',
                r'C:\Program Files\ffmpeg\bin\ffmpeg.exe'
            ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        raise FileNotFoundError("Could not find ffmpeg executable. Please install ffmpeg or provide the path manually.")

    def _find_ffprobe(self) -> str:
        """Tự động tìm đường dẫn đến ffprobe executable."""
        # Tương tự như _find_ffmpeg
        ffprobe_path = shutil.which('ffprobe')
        if ffprobe_path:
            return ffprobe_path

        # Các vị trí phổ biến theo hệ thống
        if platform.system() == 'Darwin':  # macOS
            common_paths = [
                '/usr/local/bin/ffprobe',
                '/opt/homebrew/bin/ffprobe',
                '/opt/local/bin/ffprobe'
            ]
        elif platform.system() == 'Linux':
            common_paths = [
                '/usr/bin/ffprobe',
                '/usr/local/bin/ffprobe'
            ]
        else:  # Windows
            common_paths = [
                r'C:\ffmpeg\bin\ffprobe.exe',
                r'C:\Program Files\ffmpeg\bin\ffprobe.exe'
            ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        raise FileNotFoundError(
            "Could not find ffprobe executable. Please install ffmpeg or provide the path manually.")

    def _detect_system(self) -> Dict:
        """Phát hiện thông tin hệ thống."""
        system = {
            'os': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'arch': platform.machine()
        }

        # Phát hiện processor
        if system['os'] == 'Darwin':
            # Check if M1/M2 (arm64)
            system['processor'] = 'Apple Silicon' if system['arch'] == 'arm64' else 'Intel'
        else:
            system['processor'] = platform.processor()

        return system

    def _detect_gpu(self) -> Dict:
        """Phát hiện GPU và thông tin liên quan."""
        gpu_info = {
            'available': False,
            'type': 'none',
            'name': 'Unknown'
        }

        # macOS (Apple Silicon or Intel)
        if self.system_info['os'] == 'Darwin':
            if self.system_info['arch'] == 'arm64':
                # Apple Silicon (M1/M2)
                gpu_info['available'] = True
                gpu_info['type'] = 'videotoolbox'
                gpu_info['name'] = 'Apple Silicon GPU'
            else:
                # Intel Mac
                gpu_info['available'] = True
                gpu_info['type'] = 'videotoolbox'
                gpu_info['name'] = 'Intel Integrated GPU'

        # Linux
        elif self.system_info['os'] == 'Linux':
            # Check for NVIDIA GPU
            try:
                nvidia_smi = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if nvidia_smi.returncode == 0 and nvidia_smi.stdout.strip():
                    gpu_info['available'] = True
                    gpu_info['type'] = 'nvenc'
                    gpu_info['name'] = nvidia_smi.stdout.strip()
            except FileNotFoundError:
                # NVIDIA tools not installed, try AMD
                try:
                    rocm_smi = subprocess.run(['rocm-smi', '--showproductname'],
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if rocm_smi.returncode == 0 and 'GPU' in rocm_smi.stdout:
                        gpu_info['available'] = True
                        gpu_info['type'] = 'amf'
                        gpu_info['name'] = 'AMD GPU'
                except FileNotFoundError:
                    # Try Intel
                    try:
                        intel_gpu = subprocess.run(['lspci', '-vnn', '|', 'grep', 'VGA'],
                                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                                   shell=True)
                        if intel_gpu.returncode == 0 and 'Intel' in intel_gpu.stdout:
                            gpu_info['available'] = True
                            gpu_info['type'] = 'qsv'
                            gpu_info['name'] = 'Intel GPU'
                    except FileNotFoundError:
                        # No GPU detected, will use CPU
                        pass

        # Windows (basic detection)
        elif self.system_info['os'] == 'Windows':
            try:
                # Check for NVIDIA GPU on Windows
                nvidia_smi = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if nvidia_smi.returncode == 0 and nvidia_smi.stdout.strip():
                    gpu_info['available'] = True
                    gpu_info['type'] = 'nvenc'
                    gpu_info['name'] = nvidia_smi.stdout.strip()
            except FileNotFoundError:
                # Simple fallback detection via available FFmpeg encoders
                encoders = self.get_supported_hw_encoders()
                if any('nvenc' in enc for enc in encoders):
                    gpu_info['available'] = True
                    gpu_info['type'] = 'nvenc'
                    gpu_info['name'] = 'NVIDIA GPU'
                elif any('amf' in enc for enc in encoders):
                    gpu_info['available'] = True
                    gpu_info['type'] = 'amf'
                    gpu_info['name'] = 'AMD GPU'
                elif any('qsv' in enc for enc in encoders):
                    gpu_info['available'] = True
                    gpu_info['type'] = 'qsv'
                    gpu_info['name'] = 'Intel GPU'

        return gpu_info

    def _detect_hw_acceleration(self) -> str:
        """Xác định phương thức tăng tốc phần cứng tốt nhất cho hệ thống hiện tại."""
        # Default to software encoding
        acceleration = 'none'

        # Kiểm tra xem GPU có sẵn và được bật không
        if not self.gpu_enabled or not self.gpu_info['available']:
            return acceleration

        # Kiểm tra các encoder được hỗ trợ
        encoders = self.get_supported_hw_encoders()

        # macOS (Apple Silicon hoặc Intel)
        if self.system_info['os'] == 'Darwin':
            if 'h264_videotoolbox' in encoders:
                acceleration = 'videotoolbox'

        # Linux hoặc Windows với NVIDIA GPU
        elif self.gpu_info['type'] == 'nvenc' and any('nvenc' in enc for enc in encoders):
            acceleration = 'nvenc'

        # Linux hoặc Windows với AMD GPU
        elif self.gpu_info['type'] == 'amf' and any('amf' in enc for enc in encoders):
            acceleration = 'amf'

        # Intel GPU/CPU
        elif any('qsv' in enc for enc in encoders):
            acceleration = 'qsv'

        # VAAPI (Linux)
        elif any('vaapi' in enc for enc in encoders):
            acceleration = 'vaapi'

        return acceleration

    def get_hardware_encoder(self, codec: str = 'h264') -> Optional[str]:
        """Lấy encoder phần cứng phù hợp cho hệ thống hiện tại và codec."""
        if not self.gpu_enabled or self.hw_acceleration == 'none':
            return None

        # Ánh xạ codec và phương thức tăng tốc phần cứng
        encoders = {
            'nvenc': {
                'h264': 'h264_nvenc',
                'hevc': 'hevc_nvenc'
            },
            'amf': {
                'h264': 'h264_amf',
                'hevc': 'hevc_amf'
            },
            'qsv': {
                'h264': 'h264_qsv',
                'hevc': 'hevc_qsv'
            },
            'vaapi': {
                'h264': 'h264_vaapi',
                'hevc': 'hevc_vaapi'
            },
            'videotoolbox': {
                'h264': 'h264_videotoolbox',
                'hevc': 'hevc_videotoolbox'
            }
        }

        # Lấy encoder phù hợp
        if self.hw_acceleration in encoders and codec in encoders[self.hw_acceleration]:
            encoder = encoders[self.hw_acceleration][codec]

            # Kiểm tra xem encoder có được hỗ trợ trong FFmpeg không
            if encoder in self.get_supported_hw_encoders():
                return encoder

        # Fallback to software encoding
        return None

    def get_supported_hw_encoders(self) -> List[str]:
        """Lấy danh sách encoder phần cứng được hỗ trợ trên hệ thống."""
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
                    if any(x in line for x in ['nvenc', 'amf', 'qsv', 'vaapi', 'videotoolbox', 'v4l2']):
                        parts = line.split()
                        if parts and len(parts) >= 2:
                            encoders.append(parts[1])

            return encoders

        except Exception as e:
            logger.error(f"Error getting supported encoders: {str(e)}")
            return []

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

    def transcode_video(self,
                        input_path: str,
                        output_path: str,
                        width: int,
                        height: int,
                        codec: str = 'h264',
                        preset: str = 'medium',
                        crf: int = 23,
                        format: str = 'mp4',
                        audio_codec: str = 'aac',
                        audio_bitrate: str = '128k',
                        use_gpu: bool = True) -> bool:
        """Chuyển đổi video với tự động phát hiện và điều chỉnh theo nền tảng."""
        try:
            # Kiểm tra file đầu vào
            if not os.path.exists(input_path):
                logger.error(f"Input file does not exist: {input_path}")
                return False

            # Tạo thư mục đầu ra nếu chưa tồn tại
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Xác định hardware acceleration và encoder
            hw_acceleration = self.hw_acceleration if self.gpu_enabled and use_gpu else 'none'

            # Lấy encoder tốt nhất
            video_encoder = self.config.get_best_encoder(codec, hw_acceleration)
            logger.info(f"Using video encoder: {video_encoder} for file {input_path}")

            # Lấy tùy chọn encoder phù hợp
            encoder_options = EncoderFactory.create_encoder_options(
                hw_acceleration=hw_acceleration,
                codec=codec,
                crf=crf,
                preset=preset
            )

            # Xây dựng lệnh ffmpeg cơ bản
            cmd = [self.ffmpeg_path, '-i', input_path]

            # Thêm tùy chọn video encoder
            cmd.extend(['-c:v', video_encoder])

            # Thêm tùy chọn scale
            cmd.extend(['-vf', f'scale={width}:{height}'])

            # Thêm các tùy chọn encoder
            for key, value in encoder_options.items():
                if value is not None:  # Bỏ qua giá trị None
                    cmd.extend([f'-{key}', str(value)])

            # Kiểm tra audio stream
            has_audio = True  # Giả định có audio
            try:
                probe = ffmpeg.probe(input_path, cmd=self.ffprobe_path)
                has_audio = any(s['codec_type'] == 'audio' for s in probe['streams'])
            except Exception as e:
                logger.warning(f"Error probing audio streams: {e}")

            # Thêm tùy chọn audio nếu có
            if has_audio:
                cmd.extend([
                    '-c:a', audio_codec,
                    '-b:a', audio_bitrate
                ])
            else:
                cmd.extend(['-an'])  # No audio

            # Format output
            cmd.extend(['-f', format])

            # Force overwrite
            cmd.extend(['-y'])

            # Output path
            cmd.append(output_path)

            # Log lệnh
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")

            # Chạy ffmpeg trong subprocess với timeout để tránh treo
            try:
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3600  # 1 giờ timeout
                )
            except subprocess.TimeoutExpired:
                logger.error(f"FFmpeg process timed out after 1 hour for file: {input_path}")
                return False

            # Log stderr nếu có
            if process.stderr:
                if process.returncode != 0:
                    logger.error(f"FFmpeg error: {process.stderr}")
                else:
                    logger.debug(f"FFmpeg output: {process.stderr}")

            # Kiểm tra kết quả
            if process.returncode != 0:
                logger.error(f"FFmpeg process failed with return code {process.returncode}")
                # Phân tích lỗi để cung cấp thông tin chi tiết hơn
                error_analysis = self._analyze_ffmpeg_error(process.stderr)
                logger.error(f"Error analysis: {error_analysis}")
                return False

            # Kiểm tra file output
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error(f"Output file was not created properly: {output_path}")
                return False

            logger.info(f"Successfully transcoded video to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error transcoding video: {str(e)}", exc_info=True)
            return False

    def _analyze_ffmpeg_error(self, stderr: str) -> Dict:
        """Phân tích lỗi ffmpeg để cung cấp thông tin chi tiết hơn."""
        analysis = {
            'error_type': 'unknown',
            'message': 'Unknown error',
            'solution': 'Check input file and ffmpeg installation.'
        }

        if not stderr:
            return analysis

        # Các mẫu lỗi phổ biến
        error_patterns = [
            {
                'pattern': 'Unknown encoder',
                'type': 'encoder_not_supported',
                'solution': 'Use a different encoder or install the required FFmpeg version with support for this encoder.'
            },
            {
                'pattern': 'Unrecognized option',
                'type': 'invalid_option',
                'solution': 'Remove or correct the unsupported option.'
            },
            {
                'pattern': 'No such file or directory',
                'type': 'file_not_found',
                'solution': 'Check that the input file exists and is accessible.'
            },
            {
                'pattern': 'Permission denied',
                'type': 'permission_error',
                'solution': 'Check file and directory permissions.'
            },
            {
                'pattern': 'Invalid data found when processing input',
                'type': 'invalid_input',
                'solution': 'The input file may be corrupted or in an unsupported format.'
            },
            {
                'pattern': 'Error while opening encoder',
                'type': 'encoder_error',
                'solution': 'Try using a different codec or check your hardware acceleration settings.'
            },
            {
                'pattern': 'Not enough memory',
                'type': 'memory_error',
                'solution': 'Reduce the resolution or bitrate, or allocate more memory to the process.'
            },
            {
                'pattern': 'Connection refused',
                'type': 'connection_error',
                'solution': 'Check network connections if using network inputs/outputs.'
            },
            {
                'pattern': 'splitting the argument list',
                'type': 'invalid_argument',
                'solution': 'One or more command-line arguments are invalid. Check command and options.'
            },
            {
                'pattern': 'Option not found',
                'type': 'option_not_found',
                'solution': 'The specified option is not supported by this version of FFmpeg or the chosen encoder.'
            },
            {
                'pattern': 'Error initializing',
                'type': 'initialization_error',
                'solution': 'Failed to initialize encoder or decoder. Try a different codec or disable hardware acceleration.'
            }
        ]

        # Tìm kiếm mẫu lỗi
        for pattern in error_patterns:
            if pattern['pattern'] in stderr:
                analysis['error_type'] = pattern['type']
                analysis['solution'] = pattern['solution']

                # Tìm dòng có chứa thông báo lỗi
                for line in stderr.splitlines():
                    if pattern['pattern'] in line:
                        analysis['message'] = line.strip()
                        break

                return analysis

        # Nếu không tìm thấy mẫu cụ thể, lấy dòng cuối là thông báo lỗi
        lines = stderr.splitlines()
        if lines:
            analysis['message'] = lines[-1].strip()

        return analysis

    def safe_transcode_video(self,
                             input_path: str,
                             output_path: str,
                             width: int,
                             height: int,
                             codec: str = 'h264',
                             preset: str = 'medium',
                             crf: int = 23,
                             format: str = 'mp4',
                             audio_codec: str = 'aac',
                             audio_bitrate: str = '128k',
                             use_gpu: bool = True,
                             max_retries: int = 3) -> bool:
        """
        Chuyển đổi video với khả năng thử lại tự động và fallback.

        Nếu quá trình chuyển đổi ban đầu thất bại, hàm sẽ thử lại với các encoder khác.
        """
        logger.info(f"Starting safe transcoding of {input_path} to {output_path}")

        # Danh sách fallback codec và cài đặt
        fallbacks = [
            # Thử ban đầu với GPU nếu được bật
            {'use_gpu': use_gpu, 'codec': codec, 'preset': preset, 'crf': crf},
            # Fallback 1: Software encoding với cài đặt chất lượng cao
            {'use_gpu': False, 'codec': 'h264', 'preset': 'medium', 'crf': crf},
            # Fallback 2: Software encoding với cài đặt nhanh hơn
            {'use_gpu': False, 'codec': 'h264', 'preset': 'fast', 'crf': crf + 3},
            # Fallback 3: Chế độ tốc độ cao cho trường hợp cực kỳ khó khăn
            {'use_gpu': False, 'codec': 'h264', 'preset': 'ultrafast', 'crf': crf + 5}
        ]

        # Thử từng cấu hình cho đến khi thành công
        for i, config in enumerate(fallbacks):
            retry_count = 0
            while retry_count < max_retries:
                logger.info(f"Transcoding attempt {retry_count + 1} with config: {config}")

                try:
                    result = self.transcode_video(
                        input_path=input_path,
                        output_path=output_path,
                        width=width,
                        height=height,
                        codec=config['codec'],
                        preset=config['preset'],
                        crf=config['crf'],
                        format=format,
                        audio_codec=audio_codec,
                        audio_bitrate=audio_bitrate,
                        use_gpu=config['use_gpu']
                    )

                    if result:
                        logger.info(f"Successfully transcoded using fallback config {i + 1}: {config}")
                        return True

                    # Tăng retry count nếu thất bại
                    retry_count += 1
                    logger.warning(f"Transcode failed using config {i + 1}, retry {retry_count}/{max_retries}")

                    # Thêm delay trước khi thử lại để tránh hao resources
                    time.sleep(2)

                except Exception as e:
                    logger.error(f"Error during transcode attempt: {str(e)}")
                    retry_count += 1
                    time.sleep(2)

            # Nếu đã dùng hết retries với config hiện tại, chuyển đến config tiếp theo
            logger.warning(f"All retries failed with config {i + 1}, trying next fallback")

        logger.error("All transcoding attempts failed with all configs")
        return False

    def transcode_video_segment(self,
                                input_path: str,
                                output_path: str,
                                start_time: float,
                                end_time: float,
                                width: int,
                                height: int,
                                codec: str = 'h264',
                                preset: str = 'medium',
                                crf: int = 23,
                                format: str = 'mp4',
                                audio_codec: str = 'aac',
                                audio_bitrate: str = '128k',
                                use_gpu: bool = True) -> bool:
        """Chuyển đổi một đoạn cụ thể của video với tự động phát hiện và điều chỉnh theo nền tảng."""
        try:
            # Convert start and end time to string format (HH:MM:SS.mmm)
            start_str = self._format_timestamp(start_time)
            end_str = self._format_timestamp(end_time)

            # Calculate duration
            duration = end_time - start_time
            duration_str = self._format_timestamp(duration)

            # Kiểm tra file đầu vào
            if not os.path.exists(input_path):
                logger.error(f"Input file does not exist: {input_path}")
                return False

            # Tạo thư mục đầu ra nếu chưa tồn tại
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Xác định hardware acceleration và encoder
            hw_acceleration = self.hw_acceleration if self.gpu_enabled and use_gpu else 'none'

            # Lấy encoder tốt nhất
            video_encoder = self.config.get_best_encoder(codec, hw_acceleration)
            logger.info(
                f"Using video encoder: {video_encoder} for file segment {input_path} ({start_str} to {end_str})")

            # Lấy tùy chọn encoder phù hợp
            encoder_options = EncoderFactory.create_encoder_options(
                hw_acceleration=hw_acceleration,
                codec=codec,
                crf=crf,
                preset=preset
            )

            # Xây dựng lệnh ffmpeg cơ bản
            cmd = [self.ffmpeg_path, '-ss', start_str, '-t', duration_str, '-i', input_path]

            # Thêm tùy chọn video encoder
            cmd.extend(['-c:v', video_encoder])

            # Thêm tùy chọn scale
            cmd.extend(['-vf', f'scale={width}:{height}'])

            # Thêm các tùy chọn encoder
            for key, value in encoder_options.items():
                if value is not None:  # Bỏ qua giá trị None
                    cmd.extend([f'-{key}', str(value)])

            # Kiểm tra audio stream
            has_audio = True  # Giả định có audio
            try:
                probe = ffmpeg.probe(input_path, cmd=self.ffprobe_path)
                has_audio = any(s['codec_type'] == 'audio' for s in probe['streams'])
            except Exception as e:
                logger.warning(f"Error probing audio streams: {e}")

            # Thêm tùy chọn audio nếu có
            if has_audio:
                cmd.extend([
                    '-c:a', audio_codec,
                    '-b:a', audio_bitrate
                ])
            else:
                cmd.extend(['-an'])  # No audio

            # Format output
            cmd.extend(['-f', format])

            # Force overwrite
            cmd.extend(['-y'])

            # Output path
            cmd.append(output_path)

            # Log lệnh
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")

            # Chạy ffmpeg trong subprocess với timeout để tránh treo
            try:
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=3600  # 1 giờ timeout
                )
            except subprocess.TimeoutExpired:
                logger.error(f"FFmpeg process timed out after 1 hour for file segment: {input_path}")
                return False

            # Log stderr nếu có
            if process.stderr:
                if process.returncode != 0:
                    logger.error(f"FFmpeg error: {process.stderr}")
                else:
                    logger.debug(f"FFmpeg output: {process.stderr}")

            # Kiểm tra kết quả
            if process.returncode != 0:
                logger.error(f"FFmpeg process failed with return code {process.returncode}")
                error_analysis = self._analyze_ffmpeg_error(process.stderr)
                logger.error(f"Error analysis: {error_analysis}")
                return False

            # Kiểm tra file output
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error(f"Output file was not created properly: {output_path}")
                return False

            logger.info(f"Successfully transcoded video segment to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error transcoding video segment: {str(e)}", exc_info=True)
            return False

    def create_video_preview(self,
                             input_path: str,
                             output_path: str,
                             duration: int,
                             width: int,
                             height: int,
                             codec: str = 'h264',
                             preset: str = 'medium',
                             crf: int = 23,
                             format: str = 'mp4',
                             audio_codec: str = 'aac',
                             audio_bitrate: str = '128k',
                             use_gpu: bool = True) -> bool:
        """Tạo video preview với tự động phát hiện và điều chỉnh theo nền tảng."""
        try:
            # Kiểm tra file đầu vào
            if not os.path.exists(input_path):
                logger.error(f"Input file does not exist: {input_path}")
                return False

            # Tạo thư mục đầu ra nếu chưa tồn tại
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Xác định hardware acceleration và encoder
            hw_acceleration = self.hw_acceleration if self.gpu_enabled and use_gpu else 'none'

            # Lấy encoder tốt nhất
            video_encoder = self.config.get_best_encoder(codec, hw_acceleration)
            logger.info(f"Using video encoder: {video_encoder} for preview of {input_path}")

            # Lấy tùy chọn encoder phù hợp
            encoder_options = EncoderFactory.create_encoder_options(
                hw_acceleration=hw_acceleration,
                codec=codec,
                crf=crf,
                preset=preset
            )

            # Xây dựng lệnh ffmpeg cơ bản
            cmd = [self.ffmpeg_path, '-i', input_path, '-t', str(duration)]

            # Thêm tùy chọn video encoder
            cmd.extend(['-c:v', video_encoder])

            # Thêm tùy chọn scale
            cmd.extend(['-vf', f'scale={width}:{height}'])

            # Thêm các tùy chọn encoder
            for key, value in encoder_options.items():
                if value is not None:  # Bỏ qua giá trị None
                    cmd.extend([f'-{key}', str(value)])

            # Kiểm tra audio stream
            has_audio = True  # Giả định có audio
            try:
                probe = ffmpeg.probe(input_path, cmd=self.ffprobe_path)
                has_audio = any(s['codec_type'] == 'audio' for s in probe['streams'])
            except Exception as e:
                logger.warning(f"Error probing audio streams: {e}")

            # Thêm tùy chọn audio nếu có
            if has_audio:
                cmd.extend([
                    '-c:a', audio_codec,
                    '-b:a', audio_bitrate
                ])
            else:
                cmd.extend(['-an'])  # No audio

            # Format output
            cmd.extend(['-f', format])

            # Force overwrite
            cmd.extend(['-y'])

            # Output path
            cmd.append(output_path)

            # Log lệnh
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")

            # Chạy ffmpeg trong subprocess
            try:
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=1800  # 30 phút timeout (preview thường ngắn)
                )
            except subprocess.TimeoutExpired:
                logger.error(f"FFmpeg process timed out for preview: {input_path}")
                return False

            # Log stderr nếu có
            if process.stderr:
                if process.returncode != 0:
                    logger.error(f"FFmpeg error: {process.stderr}")
                else:
                    logger.debug(f"FFmpeg output: {process.stderr}")

            # Kiểm tra kết quả
            if process.returncode != 0:
                logger.error(f"FFmpeg process failed with return code {process.returncode}")
                error_analysis = self._analyze_ffmpeg_error(process.stderr)
                logger.error(f"Error analysis: {error_analysis}")
                return False

            # Kiểm tra file output
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error(f"Output file was not created properly: {output_path}")
                return False

            logger.info(f"Successfully created video preview to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error creating video preview: {str(e)}", exc_info=True)
            return False

    def extract_video_thumbnail(self,
                                input_path: str,
                                output_path: str,
                                timestamp: str,
                                width: Optional[int] = None,
                                height: Optional[int] = None,
                                format: str = 'jpg',
                                quality: int = 90) -> bool:
        """
        Trích xuất thumbnail từ video tại timestamp cụ thể, tự động giữ tỉ lệ khung hình.
        Tự động chọn tham số nào làm chuẩn (width hoặc height) dựa vào định dạng khổ ngang/dọc của video gốc.

        Args:
            input_path: Đường dẫn video đầu vào
            output_path: Đường dẫn thumbnail đầu ra
            timestamp: Thời điểm trích xuất (HH:MM:SS.MMM)
            width: Chiều rộng mong muốn
            height: Chiều cao mong muốn
            format: Định dạng thumbnail (jpg, png, webp)
            quality: Chất lượng thumbnail (0-100)

        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Kiểm tra file đầu vào
            if not os.path.exists(input_path):
                logger.error(f"Input file does not exist: {input_path}")
                return False

            # Tạo thư mục đầu ra nếu chưa tồn tại
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Lấy thông tin video gốc
            try:
                probe = ffmpeg.probe(input_path, cmd=self.ffprobe_path)
                video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)

                if video_stream:
                    # Lấy kích thước gốc của video
                    original_width = int(video_stream.get('width', 0))
                    original_height = int(video_stream.get('height', 0))

                    # Tính toán tỉ lệ khung hình
                    original_aspect_ratio = original_width / original_height if original_height > 0 else 1.0

                    # Xác định khổ ngang/dọc
                    is_portrait = original_height > original_width

                    logger.info(f"Original video dimensions: {original_width}x{original_height}, " +
                                f"aspect ratio: {original_aspect_ratio:.2f}, " +
                                f"orientation: {'portrait' if is_portrait else 'landscape'}")
                else:
                    logger.warning("Could not find video stream in the input file")
                    original_width = 0
                    original_height = 0
                    original_aspect_ratio = 1.0
                    is_portrait = False
            except Exception as e:
                logger.warning(f"Error probing video dimensions: {e}")
                original_width = 0
                original_height = 0
                original_aspect_ratio = 1.0
                is_portrait = False

            # Xác định kích thước đầu ra dựa trên tỉ lệ gốc và khổ ngang/dọc
            target_width = width
            target_height = height

            # Nếu cả width và height đều không được chỉ định, sử dụng kích thước gốc
            if target_width is None and target_height is None:
                target_width = original_width
                target_height = original_height
            # Nếu chỉ width được chỉ định, tính height để giữ tỉ lệ
            elif target_height is None and target_width is not None:
                target_height = int(target_width / original_aspect_ratio) if original_aspect_ratio > 0 else target_width
            # Nếu chỉ height được chỉ định, tính width để giữ tỉ lệ
            elif target_width is None and target_height is not None:
                target_width = int(target_height * original_aspect_ratio)
            # Nếu cả hai đều được chỉ định, chọn tham số làm chuẩn dựa vào định dạng khổ ngang/dọc
            else:
                if is_portrait:
                    # Khổ dọc: Lấy height làm chuẩn
                    target_width = int(target_height * original_aspect_ratio)
                else:
                    # Khổ ngang: Lấy width làm chuẩn
                    target_height = int(
                        target_width / original_aspect_ratio) if original_aspect_ratio > 0 else target_width

            logger.info(f"Target thumbnail dimensions: {target_width}x{target_height}")

            # Xây dựng lệnh ffmpeg cơ bản
            cmd = [self.ffmpeg_path, '-ss', timestamp, '-i', input_path]

            # Thêm filter scale và vframes
            cmd.extend(['-vf', f'scale={target_width}:{target_height}', '-vframes', '1'])

            # Quality options
            if format.lower() in ('jpg', 'jpeg'):
                cmd.extend(['-q:v', str(min(31, 31 - (quality // 3)))])  # JPEG quality (1-31, lower is better)
            elif format.lower() == 'webp':
                cmd.extend(['-quality', str(quality)])  # WebP quality
            elif format.lower() == 'png':
                cmd.extend(['-compression_level', str(min(9, (100 - quality) // 10))])  # PNG compression (0-9)

            # Force overwrite
            cmd.extend(['-y'])

            # Output path
            cmd.append(output_path)

            # Log lệnh
            logger.info(f"Running FFmpeg thumbnail command: {' '.join(cmd)}")

            # Chạy ffmpeg trong subprocess
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Log stderr nếu có
            if process.stderr:
                if process.returncode != 0:
                    logger.error(f"FFmpeg error: {process.stderr}")
                else:
                    logger.debug(f"FFmpeg output: {process.stderr}")

            # Kiểm tra kết quả
            if process.returncode != 0:
                logger.error(f"FFmpeg process failed with return code {process.returncode}")
                return False

            # Kiểm tra file output
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error(f"Output file was not created properly: {output_path}")
                return False

            logger.info(f"Successfully extracted thumbnail to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error extracting thumbnail: {str(e)}", exc_info=True)
            return False

    def create_gif_from_video(self,
                              input_path: str,
                              output_path: str,
                              start: float = 0,
                              end: float = 5,
                              fps: int = 10,
                              width: Optional[int] = None,
                              height: Optional[int] = None,
                              quality: int = 75) -> bool:
        """
        Create a GIF from a video segment, giữ tỉ lệ khung hình gốc.
        Tự động chọn tham số nào làm chuẩn (width hoặc height) dựa vào định dạng khổ ngang/dọc của video gốc.

        Args:
            input_path: Đường dẫn video đầu vào
            output_path: Đường dẫn GIF đầu ra
            start: Thời điểm bắt đầu (giây)
            end: Thời điểm kết thúc (giây)
            fps: Số khung hình mỗi giây cho GIF
            width: Chiều rộng mong muốn
            height: Chiều cao mong muốn
            quality: Chất lượng GIF (0-100)

        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Kiểm tra file đầu vào
            if not os.path.exists(input_path):
                logger.error(f"Input file does not exist: {input_path}")
                return False

            # Tạo thư mục đầu ra nếu chưa tồn tại
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Calculate duration
            duration = end - start

            # Convert start to string format (HH:MM:SS.mmm)
            start_str = self._format_timestamp(start)
            duration_str = self._format_timestamp(duration)

            # Lấy thông tin video gốc
            try:
                probe = ffmpeg.probe(input_path, cmd=self.ffprobe_path)
                video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)

                if video_stream:
                    # Lấy kích thước gốc của video
                    original_width = int(video_stream.get('width', 0))
                    original_height = int(video_stream.get('height', 0))

                    # Tính toán tỉ lệ khung hình
                    original_aspect_ratio = original_width / original_height if original_height > 0 else 1.0

                    # Xác định khổ ngang/dọc
                    is_portrait = original_height > original_width

                    logger.info(f"Original video dimensions: {original_width}x{original_height}, " +
                                f"aspect ratio: {original_aspect_ratio:.2f}, " +
                                f"orientation: {'portrait' if is_portrait else 'landscape'}")
                else:
                    logger.warning("Could not find video stream in the input file")
                    original_width = 0
                    original_height = 0
                    original_aspect_ratio = 1.0
                    is_portrait = False
            except Exception as e:
                logger.warning(f"Error probing video dimensions: {e}")
                original_width = 0
                original_height = 0
                original_aspect_ratio = 1.0
                is_portrait = False

            # Xác định kích thước đầu ra dựa trên tỉ lệ gốc và khổ ngang/dọc
            target_width = width
            target_height = height

            # Nếu cả width và height đều không được chỉ định, sử dụng kích thước gốc
            if target_width is None and target_height is None:
                target_width = original_width
                target_height = original_height
            # Nếu chỉ width được chỉ định, tính height để giữ tỉ lệ
            elif target_height is None and target_width is not None:
                target_height = int(target_width / original_aspect_ratio) if original_aspect_ratio > 0 else target_width
            # Nếu chỉ height được chỉ định, tính width để giữ tỉ lệ
            elif target_width is None and target_height is not None:
                target_width = int(target_height * original_aspect_ratio)
            # Nếu cả hai đều được chỉ định, chọn tham số làm chuẩn dựa vào định dạng khổ ngang/dọc
            else:
                if is_portrait:
                    # Khổ dọc: Lấy height làm chuẩn
                    target_width = int(target_height * original_aspect_ratio)
                else:
                    # Khổ ngang: Lấy width làm chuẩn
                    target_height = int(
                        target_width / original_aspect_ratio) if original_aspect_ratio > 0 else target_width

            logger.info(f"Target GIF dimensions: {target_width}x{target_height}")

            # Create temporary palette file for better quality
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as palette_file:
                palette_path = palette_file.name

            try:
                # Định nghĩa filter scale
                scale_filter = f'scale={target_width}:{target_height}:flags=lanczos'

                # Step 1: Generate palette
                palette_cmd = [
                    self.ffmpeg_path,
                    '-ss', start_str,
                    '-t', duration_str,
                    '-i', input_path,
                    '-vf', f'fps={fps},{scale_filter},palettegen=max_colors=256:stats_mode=diff',
                    '-y', palette_path
                ]

                logger.info(f"Running palette generation command: {' '.join(palette_cmd)}")

                palette_process = subprocess.run(
                    palette_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                if palette_process.returncode != 0:
                    logger.error(f"Error generating palette: {palette_process.stderr}")
                    return False

                # Step 2: Create GIF using the palette
                # Điều chỉnh dither method và diff mode dựa vào quality
                dither_method = "sierra2_4a"
                if quality < 50:
                    dither_method = "bayer:bayer_scale=3"  # Bayer dithering cho chất lượng thấp hơn, kích thước file nhỏ hơn

                diff_mode = "rectangle"
                if quality > 90:
                    diff_mode = "none"  # Không sử dụng chế độ diff cho chất lượng cao

                gif_cmd = [
                    self.ffmpeg_path,
                    '-ss', start_str,
                    '-t', duration_str,
                    '-i', input_path,
                    '-i', palette_path,
                    '-lavfi',
                    f'fps={fps},{scale_filter} [x]; [x][1:v] paletteuse=dither={dither_method}:diff_mode={diff_mode}',
                    '-y', output_path
                ]

                logger.info(f"Running GIF creation command: {' '.join(gif_cmd)}")

                gif_process = subprocess.run(
                    gif_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Log stderr nếu có
                if gif_process.stderr:
                    if gif_process.returncode != 0:
                        logger.error(f"FFmpeg error: {gif_process.stderr}")
                    else:
                        logger.debug(f"FFmpeg output: {gif_process.stderr}")

                # Kiểm tra kết quả
                if gif_process.returncode != 0:
                    logger.error(f"FFmpeg process failed with return code {gif_process.returncode}")
                    error_analysis = self._analyze_ffmpeg_error(gif_process.stderr)
                    logger.error(f"Error analysis: {error_analysis}")
                    return False

                # Kiểm tra file output
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    logger.error(f"Output file was not created properly: {output_path}")
                    return False

                logger.info(f"Successfully created GIF at {output_path}")
                return True

            finally:
                # Xóa file tạm thời
                if os.path.exists(palette_path):
                    os.unlink(palette_path)

        except Exception as e:
            logger.error(f"Error creating GIF from video: {str(e)}", exc_info=True)
            return False

    def transcode_image(self,
                        input_path: str,
                        output_path: str,
                        resize: bool = False,
                        width: Optional[int] = None,
                        height: Optional[int] = None,
                        format: str = 'webp',
                        quality: int = 85) -> bool:
        """
        Chuyển đổi hình ảnh, tự động giữ tỉ lệ khung hình dựa vào định dạng khổ ngang/dọc của hình gốc.

        Args:
            input_path: Đường dẫn hình ảnh đầu vào
            output_path: Đường dẫn hình ảnh đầu ra
            resize: Có thay đổi kích thước hay không
            width: Chiều rộng mong muốn
            height: Chiều cao mong muốn
            format: Định dạng đầu ra (webp, jpg, png, avif)
            quality: Chất lượng hình ảnh (0-100)

        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        try:
            # Kiểm tra file đầu vào
            if not os.path.exists(input_path):
                logger.error(f"Input file does not exist: {input_path}")
                return False

            # Tạo thư mục đầu ra nếu chưa tồn tại
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # Lấy thông tin hình ảnh gốc nếu resize được yêu cầu
            target_width = width
            target_height = height

            if resize and (width is not None or height is not None):
                try:
                    probe = ffmpeg.probe(input_path, cmd=self.ffprobe_path)
                    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                                        None)

                    if video_stream:
                        # Lấy kích thước gốc của hình ảnh
                        original_width = int(video_stream.get('width', 0))
                        original_height = int(video_stream.get('height', 0))

                        # Tính toán tỉ lệ khung hình
                        original_aspect_ratio = original_width / original_height if original_height > 0 else 1.0

                        # Xác định khổ ngang/dọc
                        is_portrait = original_height > original_width

                        logger.info(f"Original image dimensions: {original_width}x{original_height}, " +
                                    f"aspect ratio: {original_aspect_ratio:.2f}, " +
                                    f"orientation: {'portrait' if is_portrait else 'landscape'}")

                        # Xác định kích thước đầu ra dựa trên tỉ lệ gốc và khổ ngang/dọc
                        if target_width is None and target_height is None:
                            target_width = original_width
                            target_height = original_height
                        elif target_height is None and target_width is not None:
                            target_height = int(
                                target_width / original_aspect_ratio) if original_aspect_ratio > 0 else target_width
                        elif target_width is None and target_height is not None:
                            target_width = int(target_height * original_aspect_ratio)
                        else:
                            if is_portrait:
                                # Khổ dọc: Lấy height làm chuẩn
                                target_width = int(target_height * original_aspect_ratio)
                            else:
                                # Khổ ngang: Lấy width làm chuẩn
                                target_height = int(
                                    target_width / original_aspect_ratio) if original_aspect_ratio > 0 else target_width
                    else:
                        logger.warning("Could not find video stream in the input file")
                except Exception as e:
                    logger.warning(f"Error probing image dimensions: {e}")

                logger.info(f"Target image dimensions: {target_width}x{target_height}")

            # Xây dựng lệnh ffmpeg cơ bản
            cmd = [self.ffmpeg_path, '-i', input_path]

            # Thêm tùy chọn scale nếu cần resize
            if resize and target_width is not None and target_height is not None:
                cmd.extend(['-vf', f'scale={target_width}:{target_height}'])

            # Chuẩn hóa format
            format = format.lower().strip()

            # Đơn giản hóa việc xử lý tùy chọn định dạng
            if format == 'webp':
                # WebP - Chỉ sử dụng quality
                cmd.extend(['-quality', str(quality)])
            elif format in ('jpg', 'jpeg'):
                # JPEG - Sử dụng q:v
                jpeg_quality = max(1, min(31, int(31 - quality / 3.33)))
                cmd.extend(['-q:v', str(jpeg_quality)])
            elif format == 'png':
                # PNG - KHÔNG sử dụng quality hoặc compression_level
                # PNG trong FFmpeg thường không có tùy chọn chất lượng trực tiếp
                pass
            elif format == 'avif':
                # AVIF - Sử dụng crf cho chất lượng nếu được hỗ trợ
                cmd.extend(['-crf', str(max(0, min(63, int(63 - quality / 1.58))))])

            # Force overwrite
            cmd.extend(['-y'])

            # Output path - KHÔNG sử dụng -f option để tránh lỗi
            cmd.append(output_path)

            # Log lệnh
            logger.info(f"Running FFmpeg image transcode command: {' '.join(cmd)}")

            # Chạy ffmpeg trong subprocess
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300  # 5 phút timeout cho việc chuyển đổi hình ảnh
            )

            # Log stderr nếu có
            if process.stderr:
                if process.returncode != 0:
                    logger.error(f"FFmpeg error: {process.stderr}")
                else:
                    logger.debug(f"FFmpeg output: {process.stderr}")

            # Kiểm tra kết quả
            if process.returncode != 0:
                # Nếu lỗi 'not known format', thử lại với -f
                if "Requested output format" in process.stderr and "is not known" in process.stderr:
                    format_map = {
                        'jpg': 'mjpeg',
                        'jpeg': 'mjpeg',
                        'png': 'png',
                        'webp': 'webp',
                        'avif': 'avif'
                    }
                    if format in format_map:
                        # Thêm -f option với format đúng
                        retry_cmd = cmd[:-1]  # Loại bỏ output_path
                        retry_cmd.extend(['-f', format_map[format], output_path])

                        logger.info(f"Retrying with format option: {' '.join(retry_cmd)}")

                        retry_process = subprocess.run(
                            retry_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            timeout=300
                        )

                        if retry_process.returncode == 0:
                            logger.info("Successfully transcoded image using explicit format option")
                            return True
                        else:
                            logger.error(f"Retry with format option failed: {retry_process.stderr}")

                logger.error(f"FFmpeg process failed with return code {process.returncode}")
                try:
                    error_analysis = self._analyze_ffmpeg_error(process.stderr)
                    logger.error(f"Error analysis: {error_analysis}")
                except Exception as e:
                    logger.error(f"Error analyzing FFmpeg error: {e}")
                return False

            # Kiểm tra file output
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                logger.error(f"Output file was not created properly: {output_path}")
                return False

            logger.info(f"Successfully transcoded image to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error transcoding image: {str(e)}", exc_info=True)
            return False

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to ffmpeg timestamp format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"


def get_ffmpeg_service():
    """
    Lấy singleton instance của FFmpegService.
    Đảm bảo chỉ có một instance được tạo trong mỗi process.
    """
    global _ffmpeg_service_instance
    global _ffmpeg_service_lock

    if _ffmpeg_service_instance is None:
        with _ffmpeg_service_lock:
            if _ffmpeg_service_instance is None:
                _ffmpeg_service_instance = FFmpegService()

    return _ffmpeg_service_instance
