import json
import logging.handlers
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ..models.schemas_v2 import FaceDetectionMessage, FaceDetectionResult
from ..services.face_detect_service import FaceProcessor
from ..services.model_downloader import ensure_face_detection_models
from ..services.pubsub_service import pubsub_service
from ..services.s3_service import s3_service

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging for consumer
os.makedirs("logs", exist_ok=True)

# Setup logging handlers
handlers = [logging.StreamHandler()]

# Add file handler only if logs directory is writable
try:
    handlers.append(
        logging.handlers.RotatingFileHandler(
            "logs/face_detect_consumer.log", maxBytes=5 * 1024 * 1024, backupCount=3
        )
    )
except (OSError, PermissionError):
    print("Warning: Cannot write to logs directory, using console output only")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers,
)

logger = logging.getLogger("face_detect_consumer")


class FaceDetectionWorker:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="face_detect_")
        logger.info(
            f"Initialized FaceDetectionWorker with temp dir: {self.temp_dir}"
        )

        # Auto check and download models on startup
        self._ensure_models_ready()

    def _ensure_models_ready(self):
        """Ensure all required models are available before starting worker"""
        try:

            # Get project root and models directory
            project_root = Path(__file__).parent.parent.absolute()
            models_dir = project_root / "models_faces"

            logger.info("🔍 Checking face detection models...")

            # Ensure models directory exists
            models_dir.mkdir(exist_ok=True)

            # Check and download models
            models_ready = ensure_face_detection_models(str(models_dir))

            if models_ready:
                logger.info("✅ All face detection models are ready!")
            else:
                logger.warning(
                    "⚠️  Some models may not be available. Worker will continue with limited functionality."
                )

        except Exception as e:
            logger.error(f"❌ Error ensuring models ready: {e}")
            logger.info("Worker will continue with mock models for development/testing")

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the worker and its dependencies"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "temp_dir": self.temp_dir,
            "models": {},
            "dependencies": {},
        }

        try:
            # Check models availability
            from pathlib import Path

            from ..services.model_downloader import get_model_downloader

            project_root = Path(__file__).parent.parent.absolute()
            models_dir = project_root / "models_faces"
            downloader = get_model_downloader(str(models_dir))

            required_models = [
                "yoloface.onnx",
                "arcface_w600k_r50.onnx",
                "face_landmarker_68.onnx",
                "face_landmarker_68_5.onnx",
                "gender_age.onnx",
            ]

            for model_name in required_models:
                model_path = downloader.get_model_path(model_name)
                is_valid = downloader.is_model_valid(model_path) if model_path else False

                health_status["models"][model_name] = {
                    "available": model_path is not None,
                    "valid": is_valid,
                    "path": str(model_path) if model_path else None,
                }

            # Check dependencies
            try:
                import cv2

                health_status["dependencies"]["opencv"] = {
                    "available": True,
                    "version": cv2.__version__,
                }
            except ImportError:
                health_status["dependencies"]["opencv"] = {"available": False, "version": None}

            try:
                import onnxruntime

                health_status["dependencies"]["onnxruntime"] = {
                    "available": True,
                    "version": onnxruntime.__version__,
                }
            except ImportError:
                health_status["dependencies"]["onnxruntime"] = {"available": False, "version": None}

            try:
                import numpy as np

                health_status["dependencies"]["numpy"] = {
                    "available": True,
                    "version": np.__version__,
                }
            except ImportError:
                health_status["dependencies"]["numpy"] = {"available": False, "version": None}

            # Check temp directory
            health_status["temp_dir_exists"] = os.path.exists(self.temp_dir)
            health_status["temp_dir_writable"] = os.access(self.temp_dir, os.W_OK)

            # Overall health assessment
            models_healthy = all(
                model["available"] and model["valid"] for model in health_status["models"].values()
            )
            deps_healthy = all(dep["available"] for dep in health_status["dependencies"].values())
            temp_healthy = health_status["temp_dir_exists"] and health_status["temp_dir_writable"]

            if not (models_healthy and deps_healthy and temp_healthy):
                health_status["status"] = "degraded"

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)

        return health_status

    def __del__(self):
        """Cleanup temp directory and GPU resources on destruction"""
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Cleanup GPU resources
        self._cleanup_gpu_resources()
    
    def _cleanup_gpu_resources(self):
        """Explicit cleanup of GPU/VRAM resources"""
        try:
            import gc
            
            # Force cleanup of face processor global instance
            from ..services.face_detect_service import cleanup_face_analyser
            cleanup_face_analyser()
            
            # Force garbage collection
            gc.collect()
            
            # Try CUDA cleanup if available
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    logger.info("🧹 Cleared CUDA cache")
            except ImportError:
                pass
                
            logger.info("🧹 GPU resources cleanup completed")
            
        except Exception as e:
            logger.warning(f"Error during GPU cleanup: {e}")
    
    def cleanup_and_exit(self):
        """Explicit cleanup method to be called before worker shutdown"""
        logger.info("🧹 Starting explicit worker cleanup...")
        self._cleanup_gpu_resources()

    def process_task(self, message: FaceDetectionMessage):
        """Process face detection task"""
        logger.info(f"Processing face detection task: {message.task_id}")
        logger.info(f"Source URL: {message.source_url}")
        logger.info(f"Config: {message.config}")

        temp_input = None
        result = None
        task_temp_dir = None

        try:
            # Create task-specific temp directory to avoid cross-contamination
            task_temp_dir = os.path.join(
                self.temp_dir,
                f"task_{message.task_id}",
            )
            os.makedirs(task_temp_dir, exist_ok=True)
            logger.info(f"Created task-specific temp directory: {task_temp_dir}")
            # Handle input media - use shared path or download
            if message.source_path:
                # Use shared volume file directly
                temp_input = message.source_path
                logger.info(f"📁 Using shared file: {temp_input}")

                # Verify shared file exists
                if not os.path.exists(temp_input):
                    raise Exception(f"Shared file not found: {temp_input}")

            elif message.source_url:
                # Fallback: download from URL
                logger.info(f"🔗 Downloading input media from {message.source_url}")
                temp_input = self._download_media(message.source_url, message.task_id, task_temp_dir)

                if not temp_input or not os.path.exists(temp_input):
                    raise Exception(f"Failed to download input media from {message.source_url}")
            else:
                raise Exception("No source URL or source path provided")

            # Determine media type
            media_type = self._detect_media_type(temp_input)
            logger.info(f"Detected media type: {media_type}")

            # Process based on media type (pass task_temp_dir for output)
            if media_type == "video":
                detection_result = self._process_video(temp_input, message.config, task_temp_dir)
            elif media_type == "image":
                detection_result = self._process_image(temp_input, message.config, task_temp_dir)
            else:
                raise Exception(f"Unsupported media type: {media_type}")

            # Get S3 configuration from message config
            s3_config = message.config.get(
                "s3_output_config",
                {
                    "base_path": "transcode-outputs",
                    "face_avatar_path": "{task_id}/faces/avatars",
                    "face_image_path": "{task_id}/faces/images",
                },
            )

            # Upload face avatars to S3 (only representative face per group)
            output_data = self._upload_face_avatars(
                detection_result, message.task_id, s3_config, task_temp_dir
            )

            # Create success result
            result = FaceDetectionResult(
                task_id=message.task_id,
                status="completed",
                faces=detection_result.get("faces", []),
                is_change_index=detection_result.get("is_change_index", False),
                output_urls=output_data.get("output_urls", []),
                completed_at=datetime.now(timezone.utc),
            )

            logger.info(f"Face detection completed for task {message.task_id}")
            logger.info(f"Detected {len(detection_result.get('faces', []))} face groups")

        except Exception as e:
            logger.error(
                f"Error processing face detection task {message.task_id}: {e}"
            )

            # Create failure result
            result = FaceDetectionResult(
                task_id=message.task_id,
                status="failed",
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )

        finally:
            # Publish result
            try:
                logger.info(
                    f"Publishing face detection result for task {message.task_id}"
                )
                message_id = pubsub_service.publish_face_detection_result(result)
                logger.info(f"✅ Face detection result published with message_id: {message_id}")
            except Exception as result_error:
                logger.error(f"Failed to publish face detection result: {result_error}")

            # Clean up task-specific temp directory and files
            if task_temp_dir and os.path.exists(task_temp_dir):
                try:
                    shutil.rmtree(task_temp_dir)
                    logger.info(f"Cleaned up task temp directory: {task_temp_dir}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup task temp directory: {cleanup_error}")
            elif temp_input and temp_input != message.source_url and os.path.exists(temp_input):
                # Fallback cleanup for individual input file
                os.remove(temp_input)
            
            # Force garbage collection after each task to free GPU memory
            import gc
            gc.collect()
            logger.info(f"🧹 Completed memory cleanup for task {message.task_id}")

    def _download_media(self, source_url: str, task_id: str, task_temp_dir: str = None) -> str:
        """Download media from URL or S3"""
        try:
            if source_url.startswith(("http://", "https://")):
                # Download from HTTP URL
                import requests

                response = requests.get(source_url, stream=True, timeout=300)
                response.raise_for_status()

                # Determine file extension from content type or URL
                content_type = response.headers.get("content-type", "")
                if "video" in content_type:
                    ext = ".mp4"
                elif "image" in content_type:
                    ext = ".jpg"
                else:
                    # Try to get extension from URL
                    ext = os.path.splitext(source_url)[1] or ".mp4"

                download_dir = task_temp_dir if task_temp_dir else self.temp_dir
                temp_path = os.path.join(download_dir, f"{task_id}_input{ext}")

                with open(temp_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                return temp_path

            elif source_url.startswith("s3://"):
                # Download from S3
                bucket_name, key = s3_service.parse_s3_url(source_url)
                ext = os.path.splitext(key)[1] or ".mp4"
                download_dir = task_temp_dir if task_temp_dir else self.temp_dir
                temp_path = os.path.join(download_dir, f"{task_id}_input{ext}")

                s3_service.download_file(bucket_name, key, temp_path)
                return temp_path

            else:
                # Assume it's a local file path
                if os.path.exists(source_url):
                    return source_url
                else:
                    raise Exception(f"Local file not found: {source_url}")

        except Exception as e:
            logger.error(f"Error downloading media from {source_url}: {e}")
            raise

    def _detect_media_type(self, file_path: str) -> str:
        """Detect if file is video or image using ffprobe"""
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", file_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                # Fallback to file extension
                ext = os.path.splitext(file_path)[1].lower()
                if ext in [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"]:
                    return "video"
                elif ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
                    return "image"
                else:
                    return "unknown"

            # Parse ffprobe output
            probe_data = json.loads(result.stdout)

            # Check for video streams
            for stream in probe_data.get("streams", []):
                if stream.get("codec_type") == "video":
                    return "video"

            # If no video streams found, assume it's an image
            return "image"

        except Exception as e:
            logger.warning(f"Error detecting media type for {file_path}: {e}")
            # Fallback to file extension
            ext = os.path.splitext(file_path)[1].lower()
            if ext in [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"]:
                return "video"
            elif ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
                return "image"
            else:
                return "unknown"

    def _process_video(self, video_path: str, config: dict, task_temp_dir: str = None) -> dict:
        """Process video for face detection"""
        try:
            # Create face processor with config
            processor_config = {
                "similarity_threshold": config.get("similarity_threshold", 0.6),
                "min_faces_in_group": config.get("min_faces_in_group", 3),
                "sample_interval": config.get("sample_interval", 5),
                "ignore_frames": config.get("ignore_frames", []),
                "ignore_ranges": config.get("ignore_ranges", []),
                "start_frame": config.get("start_frame", 0),
                "end_frame": config.get("end_frame", None),
                "face_detector_size": config.get("face_detector_size", "640x640"),
                "face_detector_score_threshold": config.get("face_detector_score_threshold", 0.5),
                "face_landmarker_score_threshold": config.get(
                    "face_landmarker_score_threshold", 0.85
                ),
                "iou_threshold": config.get("iou_threshold", 0.4),
                "min_appearance_ratio": config.get("min_appearance_ratio", 0.25),
                "min_frontality": config.get("min_frontality", 0.2),
                "avatar_size": config.get("avatar_size", 112),
                "avatar_padding": config.get("avatar_padding", 0.07),
                "avatar_quality": config.get("avatar_quality", 85),
                "output_path": os.path.join(task_temp_dir or self.temp_dir, "faces"),
                "max_workers": config.get("max_workers", min(4, os.cpu_count() or 2)),
            }

            processor = FaceProcessor(processor_config)
            result = processor.process_video(video_path)
            
            # Cleanup processor after use
            del processor
            import gc
            gc.collect()

            return result

        except Exception as e:
            logger.error(f"Error processing video {video_path}: {e}")
            raise

    def _process_image(self, image_path: str, config: dict, task_temp_dir: str = None) -> dict:
        """Process image for face detection"""
        try:
            # Create face processor with config
            processor_config = {
                "face_detector_size": config.get("face_detector_size", "640x640"),
                "face_detector_score_threshold": config.get("face_detector_score_threshold", 0.5),
                "face_landmarker_score_threshold": config.get(
                    "face_landmarker_score_threshold", 0.85
                ),
                "iou_threshold": config.get("iou_threshold", 0.4),
                "avatar_size": config.get("avatar_size", 112),
                "avatar_padding": config.get("avatar_padding", 0.07),
                "avatar_quality": config.get("avatar_quality", 85),
                "output_path": os.path.join(task_temp_dir or self.temp_dir, "faces"),
            }

            processor = FaceProcessor(processor_config)
            result = processor.process_image(image_path)
            
            # Cleanup processor after use
            del processor
            import gc
            gc.collect()

            return result

        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            raise

    def _upload_face_avatars(
            self,
            detection_result: dict,
            task_id: str,
            s3_config: dict = None,
            task_temp_dir: str = None,
    ) -> Dict[str, List[str]]:
        """Upload face avatars and images to S3 and return URLs"""
        output_data = {
            "avatar_urls": [],
            "face_image_urls": [],
            "output_urls": [],  # For backward compatibility
        }

        try:
            base_dir = task_temp_dir if task_temp_dir else self.temp_dir
            faces_dir = os.path.join(base_dir, "faces")

            if not os.path.exists(faces_dir):
                logger.info("No face avatars directory found, skipping upload")
                return output_data

            # Map to store URLs for each face
            face_url_map = {}

            # Upload each file
            for filename in os.listdir(faces_dir):
                if filename.endswith(".jpg"):
                    local_path = os.path.join(faces_dir, filename)

                    # Use provided S3 configuration or defaults
                    if s3_config is None:
                        s3_config = {
                            "base_path": "transcode-outputs",
                            "face_avatar_path": "{task_id}/faces/avatars",
                            "face_image_path": "{task_id}/faces/images",
                        }

                    # Determine file type and generate S3 key
                    if "_avatar.jpg" in filename:
                        s3_key = s3_service.generate_output_key(
                            task_id,
                            "face_detection",
                            filename,
                            s3_config=s3_config,
                            face_type="avatar",
                        )
                        face_name = filename.replace("_avatar.jpg", "")
                    elif "_face.jpg" in filename:
                        s3_key = s3_service.generate_output_key(
                            task_id,
                            "face_detection",
                            filename,
                            s3_config=s3_config,
                            face_type="image",
                        )
                        face_name = filename.replace("_face.jpg", "")
                    else:
                        # Unknown file type, skip
                        continue

                    # Upload to S3 (key already includes base_path from
                    # generate_output_key)
                    s3_url = s3_service.upload_file_from_path(
                        local_path, s3_key, skip_base_folder=True
                    )

                    # Store URL in map
                    if face_name not in face_url_map:
                        face_url_map[face_name] = {}

                    if "_avatar.jpg" in filename:
                        face_url_map[face_name]["avatar_url"] = s3_url
                        output_data["avatar_urls"].append(s3_url)
                    else:
                        face_url_map[face_name]["face_image_url"] = s3_url
                        output_data["face_image_urls"].append(s3_url)

                    output_data["output_urls"].append(s3_url)
                    logger.info(f"Uploaded {filename}: {s3_url}")

            # Update detection result with URLs
            if "faces" in detection_result:
                for face in detection_result["faces"]:
                    face_name = face.get("name")
                    if face_name and face_name in face_url_map:
                        face.update(face_url_map[face_name])

        except Exception as e:
            logger.error(f"Error uploading face avatars: {e}")
            # Don't fail the entire task if avatar upload fails

        return output_data


def main():
    """Main worker loop"""
    logger.info("Starting Face Detection Worker")

    worker = FaceDetectionWorker()

    # Perform initial health check
    health_status = worker.health_check()
    logger.info(f"Initial health check: {health_status['status']}")

    if health_status["status"] == "unhealthy":
        logger.error("Worker is unhealthy, cannot start")
        logger.error(
            f"Health check error: {health_status.get('error', 'Unknown error')}"
        )
        return
    elif health_status["status"] == "degraded":
        logger.warning("Worker is in degraded state but will continue")
        # Log specific issues
        for model_name, model_info in health_status["models"].items():
            if not model_info["available"] or not model_info["valid"]:
                logger.warning(
                    f"Model {model_name}: available={model_info['available']}, valid={model_info['valid']}"
                )

    def message_handler(message_data):
        """Handle incoming face detection messages"""
        try:
            # Parse message
            message = FaceDetectionMessage.model_validate(message_data)
            logger.info(f"Received face detection task: {message.task_id}")

            # Process task
            worker.process_task(message)

        except Exception as e:
            logger.error(f"Error in message handler: {e}")

    # Subscribe to face detection messages
    subscription_name = os.getenv("FACE_DETECTION_SUBSCRIPTION", "face-detection-worker-tasks-sub")
    logger.info(f"Subscribing to {subscription_name}")

    try:
        pubsub_service.listen_for_face_detection_messages(
            subscription_name=subscription_name, callback=message_handler
        )
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker error: {e}")
        raise
    finally:
        # Explicit cleanup on worker shutdown
        logger.info("🧹 Shutting down worker, cleaning up resources...")
        worker.cleanup_and_exit()


if __name__ == "__main__":
    main()
