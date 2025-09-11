import httpx
import logging
from typing import Optional
from models.schemas import CallbackData, CallbackAuth
from db.models import TranscodeTaskDB
import base64
from datetime import datetime

logger = logging.getLogger(__name__)


class CallbackService:
    @staticmethod
    def _prepare_callback_data(task: TranscodeTaskDB) -> dict:
        """Prepare callback data in the new format"""
        from models.schemas import TranscodeConfig
        
        # Parse config
        config = TranscodeConfig(**task.config) if task.config else None
        
        # Calculate profile counts
        expected_profiles = len(config.profiles) if config and config.profiles else 0
        completed_profiles = len(task.outputs) if task.outputs else 0
        failed_profiles = len(task.failed_profiles) if task.failed_profiles else 0
        
        # Face detection info
        face_detection_enabled = bool(
            config and 
            config.face_detection_config and 
            config.face_detection_config.enabled
        )
        
        # Format outputs
        outputs = []
        if task.outputs:
            for profile_name, profile_outputs in task.outputs.items():
                if isinstance(profile_outputs, list):
                    for output in profile_outputs:
                        if isinstance(output, dict) and output.get('url'):
                            outputs.append({
                                "profile": profile_name,
                                "url": output['url'],
                                "metadata": output.get('metadata', {}),
                                "size": output.get('size')
                            })
                        elif isinstance(output, str):
                            outputs.append({
                                "profile": profile_name,
                                "url": output,
                                "metadata": {},
                                "size": None
                            })
        
        # Format face detection results
        face_detection_results = None
        if task.face_detection_results:
            # Process faces to exclude avatar base64 and normed_embedding, but keep URLs
            faces = []
            for face in task.face_detection_results.get("faces", []):
                # Create a copy without sensitive/large data but keep URLs
                face_data = {
                    "name": face.get("name"),
                    "index": face.get("index"),
                    "bounding_box": face.get("bounding_box"),
                    "detector": face.get("detector"),
                    "landmarker": face.get("landmarker"),
                    "gender": face.get("gender"),
                    "age": face.get("age"),
                    "group_size": face.get("group_size"),
                    "avatar_url": face.get("avatar_url"),  # Keep avatar URL
                    "face_image_url": face.get("face_image_url"),  # Keep face image URL
                    "metrics": face.get("metrics")
                }
                # Only include non-null values
                face_data = {k: v for k, v in face_data.items() if v is not None}
                faces.append(face_data)
            
            face_detection_results = {
                "faces": faces,
                "is_change_index": task.face_detection_results.get("is_change_index", False)
            }
        
        # Build callback data
        return {
            "task_id": task.task_id,
            "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
            "source_url": task.source_url,
            "expected_profiles": expected_profiles,
            "completed_profiles": completed_profiles,
            "failed_profiles": failed_profiles,
            "face_detection_enabled": face_detection_enabled,
            "face_detection_status": task.face_detection_status.value if hasattr(task.face_detection_status, 'value') else str(task.face_detection_status) if task.face_detection_status else None,
            "face_detection_results": face_detection_results,
            "outputs": outputs,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "error_message": task.error_message
        }

    @staticmethod
    async def send_callback(task: TranscodeTaskDB) -> bool:
        """Send callback when task is completed or failed"""
        if not task.callback_url and not task.pubsub_topic:
            return True  # No callback or pubsub configured, consider success
        
        try:
            # Prepare callback data using new format
            callback_dict = CallbackService._prepare_callback_data(task)
            
            success = True
            
            # Send webhook if configured
            if task.callback_url:
                success = await CallbackService._send_webhook(task, callback_dict)
            
            # Send PubSub if configured
            if task.pubsub_topic:
                pubsub_success = await CallbackService._send_pubsub(task, callback_dict)
                success = success and pubsub_success
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending callback for task {task.task_id}: {e}")
            return False
    
    @staticmethod
    async def _send_webhook(task: TranscodeTaskDB, callback_dict: dict) -> bool:
        """Send webhook callback"""
        try:
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "TranscodeService/1.0"
            }
            
            # Add authentication if provided
            if task.callback_auth:
                auth_config = task.callback_auth
                auth_type = auth_config.get("type", "").lower()
                
                if auth_type == "bearer" and auth_config.get("token"):
                    headers["Authorization"] = f"Bearer {auth_config['token']}"
                
                elif auth_type == "basic" and auth_config.get("username") and auth_config.get("password"):
                    credentials = f"{auth_config['username']}:{auth_config['password']}"
                    encoded = base64.b64encode(credentials.encode()).decode()
                    headers["Authorization"] = f"Basic {encoded}"
                
                elif auth_type == "header" and auth_config.get("headers"):
                    headers.update(auth_config["headers"])
            
            # Send callback
            timeout = httpx.Timeout(30.0)  # 30 second timeout
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    task.callback_url,
                    json=callback_dict,
                    headers=headers
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"Callback sent successfully for task {task.task_id} to {task.callback_url}")
                    return True
                else:
                    logger.error(f"Callback failed for task {task.task_id}. Status: {response.status_code}, Response: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending webhook for task {task.task_id}: {e}")
            return False
    
    @staticmethod
    async def _send_pubsub(task: TranscodeTaskDB, callback_dict: dict) -> bool:
        """Send PubSub notification"""
        try:
            from services import pubsub_service
            
            # Publish to PubSub topic
            message_data = callback_dict
            success = await pubsub_service.publish_message(
                topic=task.pubsub_topic,
                message=message_data
            )
            
            if success:
                logger.info(f"PubSub notification sent successfully for task {task.task_id} to topic {task.pubsub_topic}")
                return True
            else:
                logger.error(f"Failed to send PubSub notification for task {task.task_id} to topic {task.pubsub_topic}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending PubSub notification for task {task.task_id}: {e}")
            return False
    
    @staticmethod
    async def retry_callback(task: TranscodeTaskDB, max_retries: int = 3) -> bool:
        """Retry callback with exponential backoff"""
        import asyncio
        
        for attempt in range(max_retries):
            if await CallbackService.send_callback(task):
                return True
            
            if attempt < max_retries - 1:  # Don't wait after last attempt
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.info(f"Callback failed for task {task.task_id}, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
        
        logger.error(f"All callback attempts failed for task {task.task_id}")
        return False


# Export singleton instance
callback_service = CallbackService()