import os
import requests
import hashlib
import logging
from typing import Dict, Optional
from pathlib import Path
from tqdm import tqdm

logger = logging.getLogger(__name__)

# Model URLs and their corresponding file names
FACE_DETECTION_MODELS = {
    'yoloface.onnx': 'https://static-vnw.skylink.vn/facefusion-media/faceswap_models/yoloface_8n.onnx',
    'arcface_w600k_r50.onnx': 'https://static-vnw.skylink.vn/facefusion-media/faceswap_models/arcface_w600k_r50.onnx',
    'face_landmarker_68.onnx': 'https://static-vnw.skylink.vn/facefusion-media/faceswap_models/2dfan4.onnx',
    'face_landmarker_68_5.onnx': 'https://static-vnw.skylink.vn/facefusion-media/faceswap_models/face_landmarker_68_5.onnx',
    'gender_age.onnx': 'https://static-vnw.skylink.vn/facefusion-media/faceswap_models/gender_age.onnx',
    'gfpgan_1.4.onnx': 'https://static-vnw.skylink.vn/facefusion-media/faceswap_models/gfpgan_1.4.onnx'
}

# Expected file sizes (in bytes) for validation
EXPECTED_FILE_SIZES = {
    'yoloface.onnx': 6 * 1024 * 1024,  # ~6MB
    'arcface_w600k_r50.onnx': 92 * 1024 * 1024,  # ~92MB
    'face_landmarker_68.onnx': 2 * 1024 * 1024,  # ~2MB
    'face_landmarker_68_5.onnx': 1 * 1024 * 1024,  # ~1MB
    'gender_age.onnx': 1 * 1024 * 1024,  # ~1MB
    'gfpgan_1.4.onnx': 10 * 1024 * 1024  # ~10MB
}

class ModelDownloader:
    def __init__(self, models_dir: str = "models_faces"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        
    def download_file(self, url: str, filepath: Path, expected_size: Optional[int] = None) -> bool:
        """
        Download a file from URL with progress bar and validation
        
        Args:
            url: URL to download from
            filepath: Local filepath to save to
            expected_size: Expected file size for validation
            
        Returns:
            bool: True if download successful, False otherwise
        """
        try:
            logger.info(f"Downloading {filepath.name} from {url}")
            
            # Create directory if it doesn't exist
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Download with progress bar
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(filepath, 'wb') as f, tqdm(
                desc=filepath.name,
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            # Only check if file exists and size > 0
            actual_size = filepath.stat().st_size
            if actual_size == 0:
                logger.warning(f"Downloaded file is empty: {filepath.name}")
                return False
            
            logger.info(f"Successfully downloaded {filepath.name} ({filepath.stat().st_size} bytes)")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {filepath.name}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading {filepath.name}: {str(e)}")
            return False
    
    def is_model_valid(self, filepath: Path, expected_size: Optional[int] = None) -> bool:
        """
        Check if a model file exists and is valid
        
        Args:
            filepath: Path to the model file
            expected_size: Expected file size for validation (ignored)
            
        Returns:
            bool: True if file exists and size > 0, False otherwise
        """
        if not filepath.exists():
            return False
        
        # Check if file is not empty
        if filepath.stat().st_size == 0:
            logger.warning(f"Empty file: {filepath.name}")
            return False
            
        return True
    
    def download_model(self, model_name: str, force_download: bool = False) -> bool:
        """
        Download a specific model if it doesn't exist or is invalid
        
        Args:
            model_name: Name of the model to download
            force_download: Force download even if file exists
            
        Returns:
            bool: True if model is available (exists or downloaded), False otherwise
        """
        if model_name not in FACE_DETECTION_MODELS:
            logger.error(f"Unknown model: {model_name}")
            return False
            
        filepath = self.models_dir / model_name
        url = FACE_DETECTION_MODELS[model_name]
        expected_size = EXPECTED_FILE_SIZES.get(model_name)
        
        # Check if model already exists and is valid
        if not force_download and self.is_model_valid(filepath):
            logger.info(f"Model {model_name} already exists and is valid")
            return True
        
        # Download the model
        if force_download and filepath.exists():
            logger.info(f"Force downloading {model_name} (overwriting existing file)")
            
        return self.download_file(url, filepath, expected_size)
    
    def download_all_models(self, force_download: bool = False) -> Dict[str, bool]:
        """
        Download all required face detection models
        
        Args:
            force_download: Force download even if files exist
            
        Returns:
            Dict[str, bool]: Dictionary mapping model names to download success status
        """
        results = {}
        
        logger.info("Checking and downloading face detection models...")
        
        for model_name in FACE_DETECTION_MODELS.keys():
            results[model_name] = self.download_model(model_name, force_download)
            
        # Summary
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        logger.info(f"Model download summary: {successful}/{total} models available")
        
        if successful == total:
            logger.info("All face detection models are ready!")
        else:
            failed_models = [name for name, success in results.items() if not success]
            logger.warning(f"Failed to download models: {failed_models}")
            
        return results
    
    def get_model_path(self, model_name: str) -> Optional[Path]:
        """
        Get the path to a model file
        
        Args:
            model_name: Name of the model
            
        Returns:
            Path to the model file if it exists, None otherwise
        """
        if model_name not in FACE_DETECTION_MODELS:
            return None
            
        filepath = self.models_dir / model_name
        return filepath if filepath.exists() else None
    
    def ensure_models_available(self) -> bool:
        """
        Ensure all required models are available, download if necessary
        
        Returns:
            bool: True if all models are available, False otherwise
        """
        results = self.download_all_models(force_download=False)
        return all(results.values())


# Singleton instance
_model_downloader = None

def get_model_downloader(models_dir: str = "models_faces") -> ModelDownloader:
    """Get singleton instance of ModelDownloader"""
    global _model_downloader
    if _model_downloader is None:
        _model_downloader = ModelDownloader(models_dir)
    return _model_downloader


def ensure_face_detection_models(models_dir: str = "models_faces") -> bool:
    """
    Convenience function to ensure all face detection models are available
    
    Args:
        models_dir: Directory to store models
        
    Returns:
        bool: True if all models are available, False otherwise
    """
    downloader = get_model_downloader(models_dir)
    return downloader.ensure_models_available()


if __name__ == "__main__":
    # Test the downloader
    logging.basicConfig(level=logging.INFO)
    
    downloader = ModelDownloader()
    results = downloader.download_all_models()
    
    print("\nDownload Results:")
    for model_name, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {model_name}")