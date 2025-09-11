"""
GPU Detection Service for optimal codec selection
"""

import subprocess
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GPUDetectionService:
    def __init__(self):
        self._gpu_info: Optional[Dict] = None
        self._nvenc_support: Optional[bool] = None
        self._available_codecs: Optional[List[str]] = None
    
    def detect_gpu_capabilities(self) -> Dict:
        """Detect GPU capabilities and available codecs"""
        if self._gpu_info is not None:
            return self._gpu_info
        
        self._gpu_info = {
            "has_nvidia_gpu": False,
            "nvenc_h264_available": False,
            "nvenc_h265_available": False,
            "cuda_available": False,
            "gpu_memory": None,
            "gpu_name": None,
            "ffmpeg_codecs": []
        }
        
        # Check NVIDIA GPU
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if lines and lines[0]:
                    gpu_info = lines[0].split(', ')
                    if len(gpu_info) >= 2:
                        self._gpu_info["has_nvidia_gpu"] = True
                        self._gpu_info["gpu_name"] = gpu_info[0]
                        self._gpu_info["gpu_memory"] = f"{gpu_info[1]}MB"
                        logger.info(f"NVIDIA GPU detected: {gpu_info[0]} with {gpu_info[1]}MB memory")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.info("NVIDIA GPU not detected or nvidia-smi not available")
        
        # Check CUDA availability
        try:
            result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self._gpu_info["cuda_available"] = True
                logger.info("CUDA toolkit detected")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.info("CUDA toolkit not detected")
        
        # Check FFmpeg NVENC support
        self._check_ffmpeg_nvenc_support()
        
        return self._gpu_info
    
    def _check_ffmpeg_nvenc_support(self):
        """Check if FFmpeg supports NVENC codecs"""
        try:
            # Check available encoders
            result = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                encoders = result.stdout.lower()
                
                # Check for NVENC codecs
                if 'h264_nvenc' in encoders:
                    self._gpu_info["nvenc_h264_available"] = True
                    self._gpu_info["ffmpeg_codecs"].append("h264_nvenc")
                    logger.info("FFmpeg H.264 NVENC encoder available")
                
                if 'hevc_nvenc' in encoders or 'h265_nvenc' in encoders:
                    self._gpu_info["nvenc_h265_available"] = True
                    self._gpu_info["ffmpeg_codecs"].append("h265_nvenc")
                    logger.info("FFmpeg H.265 NVENC encoder available")
                
                # Check for other GPU codecs
                gpu_codecs = ['h264_qsv', 'hevc_qsv', 'h264_amf', 'hevc_amf', 'h264_videotoolbox', 'hevc_videotoolbox']
                for codec in gpu_codecs:
                    if codec in encoders:
                        self._gpu_info["ffmpeg_codecs"].append(codec)
                        logger.info(f"FFmpeg {codec} encoder available")
        
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Could not check FFmpeg encoder support")
    
    def is_nvenc_available(self) -> bool:
        """Check if NVENC is available"""
        if self._nvenc_support is not None:
            return self._nvenc_support
        
        gpu_info = self.detect_gpu_capabilities()
        self._nvenc_support = (
            gpu_info["has_nvidia_gpu"] and 
            (gpu_info["nvenc_h264_available"] or gpu_info["nvenc_h265_available"])
        )
        return self._nvenc_support
    
    def get_recommended_codec(self, target_codec: str = "h264") -> str:
        """Get recommended codec based on GPU availability"""
        gpu_info = self.detect_gpu_capabilities()
        
        if target_codec.lower() in ["h264", "libx264"]:
            if gpu_info["nvenc_h264_available"]:
                return "h264_nvenc"
            else:
                return "libx264"
        
        elif target_codec.lower() in ["h265", "hevc", "libx265"]:
            if gpu_info["nvenc_h265_available"]:
                return "h265_nvenc"
            else:
                return "libx265"
        
        return target_codec
    
    def get_performance_estimate(self, codec: str, resolution: str = "720p") -> Dict:
        """Get performance estimate for codec"""
        gpu_info = self.detect_gpu_capabilities()
        
        # Base performance estimates (relative to libx264 = 1.0)
        performance_multipliers = {
            "libx264": 1.0,
            "libx265": 0.3,  # Much slower
            "h264_nvenc": 3.0,  # Much faster
            "h265_nvenc": 2.5,  # Faster than CPU
        }
        
        # Resolution multipliers
        resolution_multipliers = {
            "240p": 0.2,
            "360p": 0.4,
            "480p": 0.6,
            "720p": 1.0,
            "1080p": 2.2,
            "1440p": 4.0,
            "4k": 8.0
        }
        
        base_speed = performance_multipliers.get(codec, 1.0)
        resolution_factor = resolution_multipliers.get(resolution, 1.0)
        
        return {
            "codec": codec,
            "resolution": resolution,
            "relative_speed": base_speed / resolution_factor,
            "gpu_accelerated": codec.endswith("_nvenc"),
            "recommended": gpu_info.get("nvenc_h264_available", False) if "_nvenc" in codec else True
        }


# Global instance
gpu_detection_service = GPUDetectionService()


if __name__ == "__main__":
    # Test the service
    service = GPUDetectionService()
    
    print("=== GPU Detection Test ===")
    capabilities = service.detect_gpu_capabilities()
    
    for key, value in capabilities.items():
        print(f"{key}: {value}")
    
    print(f"\nNVENC Available: {service.is_nvenc_available()}")
    
    print(f"\nRecommended H.264 codec: {service.get_recommended_codec('h264')}")
    print(f"Recommended H.265 codec: {service.get_recommended_codec('h265')}")
    
    # Performance estimates
    codecs = ["libx264", "h264_nvenc", "libx265", "h265_nvenc"]
    print(f"\nPerformance estimates for 720p:")
    for codec in codecs:
        perf = service.get_performance_estimate(codec, "720p")
        print(f"  {codec}: {perf['relative_speed']:.1f}x speed, GPU: {perf['gpu_accelerated']}")