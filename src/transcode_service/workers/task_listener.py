#!/usr/bin/env python3
"""
Task Listener v2 - For UniversalMediaConverter
Handles UniversalTranscodeMessage format instead of old TranscodeMessage
Simplified logic without GIF support - only WebP, JPG, MP4
"""

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Dict, Optional
from urllib.parse import urlparse

from google.cloud import pubsub_v1

from ..core.config import settings
from ..core.db.crud import TaskCRUD
from ..core.db.database import get_db, init_db
from ..core.logging_config import setup_logging
from ..models.schemas_v2 import (
    CallbackAuth,
    FaceDetectionMessage,
    S3OutputConfig,
    TaskStatus,
    UniversalConverterConfig,
    UniversalTranscodeConfig,
    UniversalTranscodeMessage,
    UniversalTranscodeProfile,
)
from ..services.media_detection_service import media_detection_service
from ..services.pubsub_service import pubsub_service
from ..services.s3_service import s3_service

logger = logging.getLogger(__name__)


class PubSubTaskListenerV2:
    """PubSub task listener for v2 UniversalMediaConverter system"""

    def __init__(self):
        self.running = False
        self.tasks = []

    @staticmethod
    async def initialize():
        """Initialize database and services"""
        logger.info("Initializing PubSub Task Listener v2...")
        await init_db()
        logger.info("Database initialized successfully")

    async def handle_task_message(self, message_data: Dict):
        """Handle incoming task creation message from PubSub"""
        try:
            logger.info(f"Received task creation message v2: {message_data}")

            # Create task from message
            task_id = await self._create_task_from_message(message_data)

            if task_id:
                logger.info(f"✅ Successfully created task v2 {task_id} from PubSub message")
            else:
                logger.error("❌ Failed to create task v2 from PubSub message")

        except Exception as e:
            logger.error(f"❌ Error handling task message v2: {e}")

    async def _create_task_from_message(self, message_data: Dict) -> Optional[str]:
        """Create task from PubSub message data for UniversalMediaConverter"""
        try:
            # Extract required fields
            task_id = message_data.get("task_id")
            media_url = message_data.get("media_url") or message_data.get("source_url")
            profile = message_data.get("profile")  # Single profile, not profiles
            s3_output_config = message_data.get("s3_output_config")
            face_detection_config = message_data.get("face_detection_config")

            callback_url = message_data.get("callback_url")
            callback_auth = message_data.get("callback_auth")
            pubsub_topic = message_data.get("pubsub_topic")

            # Validate required fields
            missing_fields = []
            if not task_id:
                missing_fields.append("task_id")
            if not media_url:
                missing_fields.append("media_url/source_url")
            if not profile:
                missing_fields.append("profile")
            if not s3_output_config:
                missing_fields.append("s3_output_config")

            if missing_fields:
                logger.error(f"Missing required fields in task message v2: {missing_fields}")
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

            # Create enhanced S3 config
            enhanced_s3_config = S3OutputConfig.with_defaults(s3_output_config or {}, settings)

            # Parse the single profile from UniversalTranscodeMessage
            try:
                # Only support v2 format with 'config' field
                if "config" not in profile:
                    profile_id = profile.get("id_profile", "unknown")
                    logger.error(
                        f"❌ Profile {profile_id} missing 'config' field - v1 format not supported in v2 system"
                    )
                    return None

                # Parse v2 format
                universal_config = UniversalConverterConfig(**profile["config"])

                universal_profile = UniversalTranscodeProfile(
                    id_profile=profile["id_profile"],
                    input_type=profile.get("input_type"),
                    output_filename=profile.get("output_filename"),
                    config=universal_config,
                )
                logger.info(
                    f"✅ Created universal profile: {universal_profile.id_profile}"
                )

            except Exception as e:
                profile_id = profile.get("id_profile", "unknown")
                logger.error(f"❌ Failed to parse v2 profile {profile_id}: {e}")
                return None
            # Check if the single profile matches the detected media type
            if universal_profile.input_type and universal_profile.input_type != detected_media_type:
                logger.info(f"Skipping profile {universal_profile.id_profile} (media type mismatch: expected {universal_profile.input_type}, detected {detected_media_type})")
                return None
            else:
                logger.info(f"Profile {universal_profile.id_profile} matches detected media type: {detected_media_type}")
                filtered_profiles = [universal_profile]

            # Create final config
            transcode_config = UniversalTranscodeConfig(
                profiles=filtered_profiles,
                s3_output_config=enhanced_s3_config,
                face_detection_config=face_detection_config,
            )

            # Create/update task in database (reuse existing database logic)
            async for db in get_db():
                # Check if task already exists
                existing_task = await TaskCRUD.get_task(db, task_id)

                if existing_task:
                    logger.info(f"Task v2 {task_id} already exists, resetting...")
                    # Reset task logic (simplified - just update status)
                    await TaskCRUD.update_task_status(db, task_id, TaskStatus.PENDING)
                else:
                    # Create new task with v2 config directly
                    logger.info(f"Creating new task v2 {task_id}")
                    # Store v2 config directly as dict
                    v2_config_dict = transcode_config.model_dump()

                    await TaskCRUD.create_task(
                        db=db,
                        task_id=task_id,
                        source_url=media_url,
                        source_key=None,
                        config=v2_config_dict,
                        callback_url=callback_url,
                        callback_auth=callback_auth_obj.model_dump() if callback_auth_obj else None,
                        pubsub_topic=pubsub_topic,
                    )

                # Download source file to shared volume ONCE
                shared_file_path = None
                try:
                    # Create shared volume path from settings
                    shared_volume_dir = settings.shared_volume_path
                    os.makedirs(shared_volume_dir, exist_ok=True)

                    # Generate filename from URL
                    parsed_url = urlparse(media_url)
                    file_extension = Path(parsed_url.path).suffix or ""
                    if not file_extension:
                        # Try to detect from content-type or default to .tmp
                        file_extension = ".tmp"

                    shared_filename = f"{task_id}_{detected_media_type}{file_extension}"
                    shared_file_path = os.path.join(shared_volume_dir, shared_filename)

                    logger.info(f"📥 Downloading source file to shared volume: {shared_file_path}")

                    # Download to shared volume
                    if not s3_service.download_file_from_url(media_url, shared_file_path):
                        raise Exception(f"Failed to download source file to shared volume: {media_url}")

                    logger.info(f"✅ Downloaded to shared volume: {shared_file_path}")

                except Exception as e:
                    logger.error(f"❌ Failed to download to shared volume: {e}")
                    # Fallback: use URL directly in messages
                    shared_file_path = None

                # Publish UniversalTranscodeMessage for each profile
                published_count = 0
                failed_profiles = []

                logger.info(
                    f"=== PUBSUB PUBLISHING V2 START: task {task_id} with {len(filtered_profiles)} profiles ==="
                )

                for i, profile in enumerate(filtered_profiles, 1):
                    try:
                        profile_info = f"{i}/{len(filtered_profiles)}: profile {profile.id_profile}"
                        logger.info(f"Publishing v2 {profile_info} for task {task_id}")

                        # Use shared file path if available, otherwise fallback to URL
                        if shared_file_path:
                            message = UniversalTranscodeMessage(
                                task_id=task_id,
                                source_url=None,
                                source_path=shared_file_path,
                                profile=profile,
                                s3_output_config=enhanced_s3_config,
                                source_key=None,
                            )
                            logger.info(f"📁 Using shared file path: {shared_file_path}")
                        else:
                            message = UniversalTranscodeMessage(
                                task_id=task_id,
                                source_url=media_url,
                                source_path=None,
                                profile=profile,
                                s3_output_config=enhanced_s3_config,
                                source_key=None,
                            )
                            logger.info(f"🔗 Using source URL: {media_url}")

                        # Publish to v2 topic (need to implement this in
                        # pubsub_service)
                        message_id = pubsub_service.publish_universal_transcode_task(message)
                        published_count += 1
                        success_info = f"{i}/{len(filtered_profiles)}: profile {profile.id_profile}"
                        logger.info(f"✅ Published v2 {success_info}, message_id: {message_id}")

                    except Exception as e:
                        error_info = f"{i}/{len(filtered_profiles)}: profile {profile.id_profile}"
                        logger.error(f"❌ Failed to publish v2 {error_info}, error: {e}")
                        failed_profiles.append(profile.id_profile)

                complete_info = (
                    f"{published_count}/{len(filtered_profiles)} messages for task {task_id}"
                )
                logger.info(f"=== PUBSUB PUBLISHING V2 COMPLETE: {complete_info} ===")

                # Publish face detection task if enabled
                face_config = transcode_config.face_detection_config
                if face_config and getattr(face_config, "enabled", False):
                    try:
                        logger.info(f"Publishing face detection task for {task_id}")

                        await TaskCRUD.update_face_detection_status(
                            db, task_id, TaskStatus.PROCESSING
                        )

                        # Combine face detection config with s3 output config
                        face_detection_config_copy = dict(face_config)
                        face_detection_config_copy["s3_output_config"] = enhanced_s3_config

                        # Use shared file path if available, otherwise URL
                        if shared_file_path:
                            face_message = FaceDetectionMessage(
                                task_id=task_id,
                                source_path=shared_file_path,
                                source_url=None,
                                config=face_detection_config_copy
                            )
                            logger.info(f"📁 Face detection using shared file: {shared_file_path}")
                        else:
                            face_message = FaceDetectionMessage(
                                task_id=task_id,
                                source_url=media_url,
                                source_path=None,
                                config=face_detection_config_copy
                            )
                            logger.info(f"🔗 Face detection using URL: {media_url}")

                        face_message_id = pubsub_service.publish_face_detection_task(face_message)
                        logger.info(
                            f"✅ Published face detection task, message_id: {face_message_id}"
                        )

                    except Exception as e:
                        logger.error(f"❌ Failed to publish face detection task: {e}")
                        await TaskCRUD.update_face_detection_status(
                            db,
                            task_id,
                            TaskStatus.FAILED,
                            error_message=f"Failed to publish face detection task: {str(e)}",
                        )

                # If no messages were published, fail the task
                if published_count == 0:
                    error_msg = f"Failed to publish any v2 transcode messages: {failed_profiles}"
                    await TaskCRUD.update_task_status(db, task_id, TaskStatus.FAILED, error_msg)
                    return None

                # Update task status to processing
                await TaskCRUD.update_task_status(db, task_id, TaskStatus.PROCESSING)
                await db.commit()

                return task_id
            return None

        except Exception as e:
            logger.error(f"Error creating task v2 from message: {e}")
            return None

    @staticmethod
    def _validate_media_url(url: str) -> bool:
        """Validate if URL is accessible and points to media file"""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False

            # Check if URL has media file extension
            allowed_extensions = [
                ".mp4",
                ".avi",
                ".mov",
                ".mkv",
                ".webm",
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".webp",
            ]
            path = parsed.path.lower()
            return any(path.endswith(ext) for ext in allowed_extensions)
        except BaseException:
            return False

    def pubsub_message_callback(self, message):
        """Callback for PubSub messages"""
        try:
            data = json.loads(message.data.decode("utf-8"))
            logger.info(f"Received PubSub message v2: {data}")

            # Schedule the async handler in the main event loop
            if hasattr(self, "_main_loop") and self._main_loop and not self._main_loop.is_closed():
                future = asyncio.run_coroutine_threadsafe(
                    self.handle_task_message(data), self._main_loop
                )
                future.result(timeout=30)
                message.ack()
                logger.info("Message v2 processed and acknowledged")
            else:
                logger.error("Main event loop not available")
                message.nack()

        except Exception as e:
            logger.error(f"Error processing PubSub message v2: {e}")
            message.nack()

    async def start_listening(self, subscription_name: str):
        """Start listening to PubSub messages"""
        try:
            logger.info(f"Starting PubSub listener v2 for subscription: {subscription_name}")

            self._main_loop = asyncio.get_running_loop()

            def signal_handler(signum, frame):
                logger.info(f"Received signal {signum}, shutting down v2...")
                self.running = False

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            self.running = True

            import threading

            def run_subscriber():
                try:
                    max_messages = int(os.getenv("PUBSUB_MAX_MESSAGES", "10"))
                    flow_control = pubsub_v1.types.FlowControl(max_messages=max_messages)

                    subscription_path = pubsub_service.subscriber_client.subscription_path(
                        pubsub_service.project_id, subscription_name
                    )

                    streaming_pull_future = pubsub_service.subscriber_client.subscribe(
                        subscription_path,
                        callback=self.pubsub_message_callback,
                        flow_control=flow_control,
                    )

                    logger.info(f"Listening for v2 task messages on {subscription_path}")

                    with pubsub_service.subscriber_client:
                        try:
                            streaming_pull_future.result()
                        except Exception as e:
                            logger.error(f"Streaming pull error v2: {e}")
                            streaming_pull_future.cancel()
                            streaming_pull_future.result()

                except Exception as e:
                    logger.error(f"Subscriber error v2: {e}")
                    self.running = False

            subscriber_thread = threading.Thread(target=run_subscriber)
            subscriber_thread.daemon = True
            subscriber_thread.start()

            # Keep the main loop running
            while self.running:
                self.tasks = [task for task in self.tasks if not task.done()]
                await asyncio.sleep(1)

            logger.info("PubSub listener v2 stopped")

        except Exception as e:
            logger.error(f"Error in PubSub listener v2: {e}")
            raise


async def main():
    """Main function to run the PubSub task listener v2"""
    setup_logging()

    subscription_name = settings.tasks_subscription

    listener = PubSubTaskListenerV2()
    await listener.initialize()

    try:
        await listener.start_listening(subscription_name)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down v2...")
    except Exception as e:
        logger.error(f"Listener v2 error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
