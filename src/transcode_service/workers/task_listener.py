import asyncio
import json
import logging
import os
import signal
import sys
from typing import Dict, Optional

from ..core.config import settings
from ..core.db import init_db, get_db, TaskCRUD
from ..core.logging_config import setup_logging
from ..models.schemas import TranscodeConfig, TranscodeMessage, TaskStatus, CallbackAuth
from ..services import pubsub_service
from ..services.media_detection_service import media_detection_service

logger = logging.getLogger(__name__)


class PubSubTaskListener:
    def __init__(self):
        self.running = False
        self.tasks = []

    async def initialize(self):
        """Initialize database and services"""
        logger.info("Initializing PubSub Task Listener...")
        await init_db()
        logger.info("Database initialized successfully")

    async def handle_task_message(self, message_data: Dict):
        """Handle incoming task creation message from PubSub"""
        try:
            logger.info(f"Received task creation message: {message_data}")

            # Create task from message
            task_id = await self._create_task_from_message(message_data)

            if task_id:
                logger.info(f"✅ Successfully created task {task_id} from PubSub message")
            else:
                logger.error("❌ Failed to create task from PubSub message")

        except Exception as e:
            logger.error(f"❌ Error handling task message: {e}")

    async def _create_task_from_message(self, message_data: Dict) -> Optional[str]:
        """Create task from PubSub message data - identical logic to API endpoint"""
        try:
            # Extract required fields - support both old and new format
            task_id = message_data.get("task_id")
            media_url = message_data.get("media_url") or message_data.get("source_url")
            profiles = message_data.get("profiles")
            # Handle single profile format
            if not profiles and message_data.get("profile"):
                profiles = [message_data.get("profile")]
            s3_output_config = message_data.get("s3_output_config")
            face_detection_config = message_data.get("face_detection_config")
            
            # 📊 S3 CONFIG LOGGING: Show received S3 config from message
            logger.info(f"📥 S3 CONFIG RECEIVED from message for task {task_id}:")
            if s3_output_config:
                logger.info(f"   ✅ Message contains s3_output_config with {len(s3_output_config)} fields:")
                for key, value in s3_output_config.items():
                    # Hide sensitive info
                    if 'secret' in key.lower() or 'key' in key.lower():
                        logger.info(f"   - {key}: ***HIDDEN***")
                    else:
                        logger.info(f"   - {key}: {value}")
            else:
                logger.info(f"   ⚠️  Message contains NO s3_output_config - will use all defaults")
            callback_url = message_data.get("callback_url")
            callback_auth = message_data.get("callback_auth")
            pubsub_topic = message_data.get("pubsub_topic")

            # Validate required fields
            missing_fields = []
            if not task_id:
                missing_fields.append('task_id')
            if not media_url:
                missing_fields.append('media_url/source_url')
            if not profiles:
                missing_fields.append('profiles/profile')
            if not s3_output_config:
                missing_fields.append('s3_output_config')
            
            if missing_fields:
                logger.error(f"Missing required fields in task message: {missing_fields}")
                logger.error(f"Full message content: {json.dumps(message_data, indent=2)}")
                return None

            # Validate media URL
            if not self._validate_media_url(media_url):
                logger.error(f"Invalid media URL: {media_url}")
                return None

            # Parse callback auth if provided
            callback_auth_obj = None
            if callback_auth:
                try:
                    callback_auth_obj = CallbackAuth(**callback_auth)
                except Exception as e:
                    logger.error(f"Invalid callback_auth format: {e}")
                    return None

            # Detect media type
            detected_media_type = media_detection_service.detect_media_type(url=media_url)
            logger.info(f"Detected media type: {detected_media_type}")

            # Create enhanced S3 config with fallbacks
            from ..models.schemas import S3OutputConfig
            enhanced_s3_config = S3OutputConfig.with_defaults(s3_output_config or {}, settings)
            
            # 🔧 S3 CONFIG LOGGING: Show final enhanced config being used
            logger.info(f"🔧 S3 CONFIG ENHANCED for task {task_id}:")
            logger.info(f"   📦 Bucket: {enhanced_s3_config.bucket}")
            logger.info(f"   📁 Base path: {enhanced_s3_config.base_path}")
            logger.info(f"   🗂️  Folder structure: {enhanced_s3_config.folder_structure}")
            logger.info(f"   🌐 Endpoint URL: {enhanced_s3_config.aws_endpoint_url}")
            logger.info(f"   🌍 Public URL: {enhanced_s3_config.aws_endpoint_public_url}")
            logger.info(f"   🧹 Cleanup on reset: {enhanced_s3_config.cleanup_on_task_reset}")
            logger.info(f"   🗑️  Cleanup temp files: {enhanced_s3_config.cleanup_temp_files}")
            logger.info(f"   ⏱️  Upload timeout: {enhanced_s3_config.upload_timeout}s")
            logger.info(f"   🔄 Max retries: {enhanced_s3_config.max_retries}")
            if enhanced_s3_config.aws_access_key_id:
                key_preview = enhanced_s3_config.aws_access_key_id[:8] + "***" if len(enhanced_s3_config.aws_access_key_id) > 8 else "***"
                logger.info(f"   🔑 Access key: {key_preview}")
            else:
                logger.info(f"   🔑 Access key: (from settings)")
            
            # Create initial config
            initial_config_data = {
                "profiles": profiles,
                "s3_output_config": enhanced_s3_config
            }
            if face_detection_config:
                initial_config_data["face_detection_config"] = face_detection_config
            initial_transcode_config = TranscodeConfig(**initial_config_data)

            # Filter profiles based on detected media type
            filtered_profiles, skipped_profiles = media_detection_service.filter_profiles_by_input_type(
                profiles=initial_transcode_config.profiles,
                media_type=detected_media_type
            )

            # Get filtering summary
            filter_summary = media_detection_service.get_profile_summary(
                original_count=len(initial_transcode_config.profiles),
                filtered_count=len(filtered_profiles),
                skipped_profiles=skipped_profiles,
                media_type=detected_media_type
            )

            logger.info(f"Profile filtering summary: {filter_summary}")

            # Create final config with filtered profiles
            config_data = {
                "profiles": [profile.model_dump() for profile in filtered_profiles],
                "s3_output_config": enhanced_s3_config  # Use the enhanced config from above
            }
            if face_detection_config:
                config_data["face_detection_config"] = face_detection_config
            transcode_config = TranscodeConfig(**config_data)

            # Check if we have any profiles left after filtering
            if not transcode_config.profiles:
                logger.error(
                    f"No profiles match the detected media type '{detected_media_type}'. Skipped profiles: {skipped_profiles}")
                return None

            # Create task in database
            async for db in get_db():
                # Check if task already exists first
                existing_task = await TaskCRUD.get_task(db, task_id)
                
                if existing_task:
                    logger.info(f"Task {task_id} already exists with status: {existing_task.status}")
                    logger.info(f"Resetting task {task_id} regardless of status...")
                    
                    # Clean up ALL S3 files for this task (profiles + faces)
                    if existing_task.outputs or existing_task.face_detection_results:
                        logger.info(f"Cleaning up all S3 files for task {task_id}")
                        try:
                            from ..services.s3_service import S3Service
                            s3_service = S3Service()
                            
                            # Get S3 config to determine correct base_path for cleanup
                            task_s3_config = existing_task.config.get('s3_output_config', {}) if existing_task.config else {}
                            base_path = task_s3_config.get('base_path', 'transcode-outputs')  # fallback to default
                            
                            # Clean up entire task folder: base_path/task_id/*
                            cleanup_success = s3_service.cleanup_task_folder_with_base_path(task_id, base_path)
                            
                            if cleanup_success:
                                logger.info(f"✅ Cleaned up all S3 files for task {task_id} in {base_path}/{task_id}/")
                            else:
                                logger.warning(f"⚠️ Some files may not have been cleaned up for task {task_id}")
                                
                        except Exception as e:
                            logger.error(f"❌ Error cleaning up S3 files for task {task_id}: {e}")
                    else:
                        logger.info(f"No S3 files to clean up for task {task_id}")
                    
                    # Reset all task fields to initial state
                    from sqlalchemy import update
                    from ..database.models import TranscodeTaskDB
                    from datetime import datetime
                    
                    # Prepare update data
                    update_data = {
                        "status": TaskStatus.PENDING,
                        "source_url": media_url,  # Update source URL for retry
                        "source_key": None,  # Reset source key
                        "config": transcode_config.model_dump(),  # Update config
                        "outputs": None,
                        "failed_profiles": None,
                        "error_message": None,
                        "face_detection_status": None,
                        "face_detection_error": None,
                        "face_detection_results": None,
                        "updated_at": datetime.utcnow()
                    }
                    
                    # Add callback data if provided
                    if callback_url:
                        update_data["callback_url"] = callback_url
                    if callback_auth_obj:
                        update_data["callback_auth"] = callback_auth_obj.model_dump()
                    if pubsub_topic:
                        update_data["pubsub_topic"] = pubsub_topic
                    
                    # Update task in database
                    stmt = (
                        update(TranscodeTaskDB)
                        .where(TranscodeTaskDB.task_id == task_id)
                        .values(**update_data)
                    )
                    await db.execute(stmt)
                    await db.commit()
                    
                    logger.info(f"✅ Reset task {task_id} to initial state")
                    
                    # Continue with publishing logic below
                    
                else:
                    # Task doesn't exist, create it
                    logger.info(f"Creating new task {task_id}")
                    task = await TaskCRUD.create_task(
                        db=db,
                        task_id=task_id,
                        source_url=media_url,
                        source_key=None,  # No source key for URL inputs
                        config=transcode_config,
                        callback_url=callback_url,
                        callback_auth=callback_auth_obj.model_dump() if callback_auth_obj else None,
                        pubsub_topic=pubsub_topic
                    )

                # Publish transcode messages for each profile
                published_count = 0
                failed_profiles = []

                logger.info(
                    f"=== PUBSUB PUBLISHING START: task {task_id} with {len(transcode_config.profiles)} profiles ===")

                for i, profile in enumerate(transcode_config.profiles, 1):
                    try:
                        logger.info(
                            f"Publishing {i}/{len(transcode_config.profiles)}: profile {profile.id_profile} for task {task_id}")
                        message = TranscodeMessage(
                            task_id=task_id,
                            source_url=media_url,
                            profile=profile,
                            s3_output_config=transcode_config.s3_output_config,
                            source_key=None
                        )
                        message_id = pubsub_service.publish_transcode_task(message)
                        published_count += 1
                        logger.info(
                            f"✅ Published {i}/{len(transcode_config.profiles)}: profile {profile.id_profile}, message_id: {message_id}")
                    except Exception as e:
                        logger.error(
                            f"❌ Failed to publish {i}/{len(transcode_config.profiles)}: profile {profile.id_profile}, error: {e}")
                        failed_profiles.append(profile.id_profile)

                logger.info(
                    f"=== PUBSUB PUBLISHING COMPLETE: {published_count}/{len(transcode_config.profiles)} messages for task {task_id} ===")

                # Publish face detection task if enabled
                face_detection_published = False
                if transcode_config.face_detection_config and transcode_config.face_detection_config.enabled:
                    try:
                        from ..models.schemas import FaceDetectionMessage
                        logger.info(f"Publishing face detection task for {task_id}")

                        await TaskCRUD.update_face_detection_status(db, task_id, TaskStatus.PROCESSING)

                        # Combine face detection config with s3 output config
                        face_config = transcode_config.face_detection_config.model_dump()
                        face_config["s3_output_config"] = transcode_config.s3_output_config.model_dump()
                        
                        face_message = FaceDetectionMessage(
                            task_id=task_id,
                            source_url=media_url,
                            config=face_config
                        )

                        face_message_id = pubsub_service.publish_face_detection_task(face_message)
                        face_detection_published = True
                        logger.info(f"✅ Published face detection task, message_id: {face_message_id}")

                    except Exception as e:
                        logger.error(f"❌ Failed to publish face detection task: {e}")
                        await TaskCRUD.update_face_detection_status(
                            db, task_id, TaskStatus.FAILED,
                            error_message=f"Failed to publish face detection task: {str(e)}"
                        )

                # If no messages were published, fail the task
                if published_count == 0:
                    await TaskCRUD.update_task_status(db, task_id, TaskStatus.FAILED,
                                                      f"Failed to publish any transcode messages: {failed_profiles}")
                    return None

                # Update task status to processing
                await TaskCRUD.update_task_status(db, task_id, TaskStatus.PROCESSING)

                await db.commit()

                return task_id

        except Exception as e:
            logger.error(f"Error creating task from message: {e}")
            return None

    def _validate_media_url(self, url: str) -> bool:
        """Validate if URL is accessible and points to media file"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False

            # Check if URL has media file extension
            allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.jpg', '.jpeg', '.png', '.gif']
            path = parsed.path.lower()
            return any(path.endswith(ext) for ext in allowed_extensions)
        except:
            return False

    async def _cleanup_s3_outputs(self, outputs: dict):
        """Clean up S3 outputs from previous task execution"""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            s3_client = boto3.client('s3')
            deleted_count = 0
            
            logger.info(f"Cleaning up S3 outputs for task retry...")
            
            for profile_id, profile_outputs in outputs.items():
                if not profile_outputs:
                    continue
                    
                for output in profile_outputs:
                    try:
                        # Handle both URL format and metadata format
                        if isinstance(output, dict) and 'url' in output:
                            url = output['url']
                        elif isinstance(output, str):
                            url = output
                        else:
                            continue
                            
                        # Extract bucket and key from S3 URL
                        if url.startswith('s3://'):
                            # s3://bucket/key format
                            parts = url[5:].split('/', 1)
                            if len(parts) == 2:
                                bucket, key = parts
                                s3_client.delete_object(Bucket=bucket, Key=key)
                                deleted_count += 1
                                logger.debug(f"Deleted S3 object: s3://{bucket}/{key}")
                        elif 'amazonaws.com' in url:
                            # https://bucket.s3.region.amazonaws.com/key format
                            import re
                            match = re.search(r'https://([^.]+)\.s3\..*\.amazonaws\.com/(.+)', url)
                            if match:
                                bucket, key = match.groups()
                                s3_client.delete_object(Bucket=bucket, Key=key)
                                deleted_count += 1
                                logger.debug(f"Deleted S3 object: s3://{bucket}/{key}")
                                
                    except ClientError as e:
                        if e.response['Error']['Code'] != 'NoSuchKey':
                            logger.warning(f"Failed to delete S3 object {url}: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to parse S3 URL {url}: {e}")
            
            logger.info(f"Cleaned up {deleted_count} S3 objects for task retry")
            
        except Exception as e:
            logger.error(f"Error cleaning up S3 outputs: {e}")

    def pubsub_message_callback(self, message):
        """Callback for PubSub messages"""
        try:
            data = json.loads(message.data.decode('utf-8'))
            logger.info(f"Received PubSub message: {data}")

            # Schedule the async handler in the main event loop
            if hasattr(self, '_main_loop') and self._main_loop and not self._main_loop.is_closed():
                # Use the main event loop
                future = asyncio.run_coroutine_threadsafe(
                    self.handle_task_message(data), self._main_loop
                )
                # Wait for completion
                future.result(timeout=30)  # 30 second timeout
                message.ack()
                logger.info("Message processed and acknowledged")
            else:
                logger.error("Main event loop not available")
                message.nack()

        except Exception as e:
            logger.error(f"Error processing PubSub message: {e}")
            message.nack()

    async def start_listening(self, subscription_name: str):
        """Start listening to PubSub messages"""
        try:
            logger.info(f"Starting PubSub listener for subscription: {subscription_name}")

            # Store the main event loop for use in callbacks
            self._main_loop = asyncio.get_running_loop()

            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, shutting down...")
                self.running = False

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            self.running = True

            # Start listening in a separate thread
            import threading

            def run_subscriber():
                try:
                    from google.cloud import pubsub_v1
                    
                    # Create proper flow control settings
                    max_messages = int(os.getenv("PUBSUB_MAX_MESSAGES", "10"))
                    flow_control = pubsub_v1.types.FlowControl(max_messages=max_messages)
                    
                    # Get the subscription path
                    subscription_path = pubsub_service.subscriber_client.subscription_path(
                        pubsub_service.project_id, subscription_name
                    )
                    
                    # Start streaming pull
                    streaming_pull_future = pubsub_service.subscriber_client.subscribe(
                        subscription_path,
                        callback=self.pubsub_message_callback,
                        flow_control=flow_control
                    )
                    
                    logger.info(f"Listening for task messages on {subscription_path}")
                    
                    # Keep the subscriber running
                    with pubsub_service.subscriber_client:
                        try:
                            streaming_pull_future.result()
                        except Exception as e:
                            logger.error(f"Streaming pull error: {e}")
                            streaming_pull_future.cancel()
                            streaming_pull_future.result()
                            
                except Exception as e:
                    logger.error(f"Subscriber error: {e}")
                    self.running = False

            subscriber_thread = threading.Thread(target=run_subscriber)
            subscriber_thread.daemon = True
            subscriber_thread.start()

            # Keep the main loop running
            while self.running:
                # Clean up completed tasks
                self.tasks = [task for task in self.tasks if not task.done()]
                await asyncio.sleep(1)

            logger.info("PubSub listener stopped")

        except Exception as e:
            logger.error(f"Error in PubSub listener: {e}")
            raise


async def main():
    """Main function to run the PubSub task listener"""
    # Setup logging
    setup_logging()

    # Get subscription name from settings
    subscription_name = settings.tasks_subscription or "transcode-utils-tasks-sub"

    # Create and initialize listener
    listener = PubSubTaskListener()
    await listener.initialize()

    # Start listening
    try:
        await listener.start_listening(subscription_name)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Listener error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
