import asyncio
import json
import logging
import os
import time
import uuid
from typing import Dict, Optional
from urllib.parse import urlparse

import httpx
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .background_tasks import result_subscriber
from ..core.config import settings
from ..core.db.crud import TaskCRUD, ConfigTemplateCRUD
from ..core.db.database import get_db, init_db
from ..core.db.models import TranscodeTaskDB
from ..models.schemas import CallbackAuth, ConfigTemplateRequest, FaceDetectionMessage, TaskStatus
from ..models.schemas_v2 import (
    S3OutputConfig,
    UniversalConverterConfig,
    UniversalTranscodeConfig,
    UniversalTranscodeMessage,
    UniversalTranscodeProfile,
)
from ..services.callback_service import callback_service
from ..services.media_detection_service import media_detection_service
from ..services.pubsub_service import pubsub_service
from ..services.s3_service import s3_service

logger = logging.getLogger("api")

app = FastAPI(title="Transcode Service API")


async def get_file_size(url: str) -> Optional[int]:
    """Get file size from URL using HEAD request"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.head(url)
            if response.status_code == 200:
                content_length = response.headers.get("content-length")
                if content_length:
                    return int(content_length)
    except Exception as e:
        logger.warning(f"Failed to get file size for {url}: {e}")
    return None


def ensure_outputs_compatibility(outputs: Dict) -> Dict:
    """Ensure outputs format is compatible with frontend (backward compatibility)"""
    if not outputs:
        return outputs

    compatible_outputs = {}
    for profile, items in outputs.items():
        if not items:
            continue

        item_list = items if isinstance(items, list) else [items]
        compatible_items = []

        for item in item_list:
            if isinstance(item, dict) and "url" in item:
                # New format with metadata - keep as is
                compatible_items.append(item)
            else:
                # Old format (URL only) - convert to new format
                compatible_items.append({"url": item, "metadata": {}})

        compatible_outputs[profile] = compatible_items

    return compatible_outputs


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database and start background tasks"""
    start_time = time.time()

    try:
        logger.info("Starting database initialization...")
        await init_db()
        db_time = time.time() - start_time
        logger.info(f"Database initialized in {db_time:.2f}s")

        # Start background result subscriber
        logger.info("Starting background result subscriber...")
        asyncio.create_task(result_subscriber())
        #
        total_time = time.time() - start_time
        logger.info(
            f"Background services started. Total startup time: {
            total_time:.2f}s"
        )

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


def _validate_media_url(url: str) -> bool:
    """Validate if URL is accessible and points to media file"""
    try:
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
        ]
        path = parsed.path.lower()
        return any(path.endswith(ext) for ext in allowed_extensions)
    except BaseException:
        return False


@app.post("/transcode")
async def create_transcode_task(
        # Optional file upload
        video: Optional[UploadFile] = File(None),
        # Optional URL input
        media_url: Optional[str] = Form(None),
        # Required config
        profiles: str = Form(...),
        s3_output_config: str = Form(...),
        # Optional face detection config
        face_detection_config: Optional[str] = Form(None),
        # Optional callback/notification
        callback_url: Optional[str] = Form(None),
        callback_auth: Optional[str] = Form(None),
        pubsub_topic: Optional[str] = Form(None),
        db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Unified transcode endpoint - handles both file upload and URL input with optional face detection

    Parameters:
    - video: File upload (optional)
    - media_url: Media URL (optional)
    - profiles: JSON array of transcode profiles
    - s3_output_config: JSON object for S3 output configuration
    - face_detection_config: JSON object for face detection configuration (optional)
    - callback_url: Optional webhook URL
    - callback_auth: Optional auth config for callback
    - pubsub_topic: Optional PubSub topic for notifications

    Note: Either video OR media_url must be provided, not both
    """
    task_id = str(uuid.uuid4())
    source_key = None
    source_url = None

    try:
        # Validate input - either file or URL, not both
        if not video and not media_url:
            raise HTTPException(400, "Either 'video' file or 'media_url' must be provided")
        if video and media_url:
            raise HTTPException(400, "Provide either 'video' file or 'media_url', not both")

        # Parse JSON configs - V2 format required
        try:
            profiles_data = json.loads(profiles)
            s3_config_data = json.loads(s3_output_config)
            face_detection_config_data = None
            if face_detection_config:
                face_detection_config_data = json.loads(face_detection_config)

            # Validate v2 format - each profile must have 'config' field
            for i, profile_data in enumerate(profiles_data):
                if "config" not in profile_data:
                    raise HTTPException(
                        400, f"Profile {i} missing 'config' field - v2 Universal format required"
                    )

        except json.JSONDecodeError as e:
            raise HTTPException(400, f"Invalid JSON format: {e}") from e

        # Parse callback auth if provided
        callback_auth_obj = None
        if callback_auth:
            try:
                callback_auth_data = json.loads(callback_auth)
                callback_auth_obj = CallbackAuth(**callback_auth_data)
            except json.JSONDecodeError as exc:
                raise HTTPException(400, "Invalid callback_auth JSON format") from exc

        # Detect media type
        detected_media_type = None
        if video:
            # For file uploads, use filename and content type
            detected_media_type = media_detection_service.detect_media_type(
                filename=video.filename, content_type=video.content_type
            )
        elif media_url:
            # For URL inputs, use URL path
            detected_media_type = media_detection_service.detect_media_type(url=media_url)

        logger.info(f"Detected media type: {detected_media_type}")

        # Create v2 profiles from data
        universal_profiles = []
        for profile_data in profiles_data:
            try:
                # Parse v2 config
                universal_config = UniversalConverterConfig(**profile_data["config"])

                universal_profile = UniversalTranscodeProfile(
                    id_profile=profile_data["id_profile"],
                    input_type=profile_data.get("input_type"),
                    output_filename=profile_data.get("output_filename"),
                    config=universal_config,
                )
                universal_profiles.append(universal_profile)

            except Exception as e:
                raise HTTPException(
                    400,
                    f"Invalid profile {
                    profile_data.get(
                        'id_profile', 'unknown')}: {e}",
                ) from e

        # Create S3 config
        s3_config = S3OutputConfig.with_defaults(s3_config_data, settings)

        # Filter profiles based on detected media type
        filtered_profiles = []
        skipped_profiles = []

        for profile in universal_profiles:
            if profile.input_type and profile.input_type != detected_media_type:
                skipped_profiles.append(profile.id_profile)
            else:
                filtered_profiles.append(profile)

        # Get filtering summary
        filter_summary = media_detection_service.get_profile_summary(
            original_count=len(universal_profiles),
            filtered_count=len(filtered_profiles),
            skipped_profiles=skipped_profiles,
            media_type=detected_media_type,
        )

        logger.info(f"Profile filtering summary: {filter_summary}")

        # Create v2 config
        transcode_config = UniversalTranscodeConfig(
            profiles=filtered_profiles,
            s3_output_config=s3_config,
            face_detection_config=face_detection_config_data,
        )

        # Check if we have any profiles left after filtering
        if not transcode_config.profiles:
            raise HTTPException(
                400,
                f"No profiles match the detected media type '{detected_media_type}'. "
                f"Skipped profiles: {skipped_profiles}",
            )

        # Handle file upload
        if video:
            # Validate file type
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
            ]
            file_extension = os.path.splitext(video.filename)[1].lower()
            if file_extension not in allowed_extensions:
                raise HTTPException(400, f"File type {file_extension} not supported")

            # Upload to S3
            source_key = f"uploads/{task_id}/{video.filename}"
            source_url = s3_service.upload_file(
                video.file, source_key, content_type=video.content_type
            )

            # Small delay to ensure S3 consistency for large files
            time.sleep(1)

        # Handle URL input
        if media_url:
            # Validate media URL
            if not _validate_media_url(media_url):
                raise HTTPException(400, "Invalid media URL or unsupported file type")

            # Test if URL is accessible
            async with httpx.AsyncClient(timeout=30.0) as client:
                try:
                    response = await client.head(media_url)
                    if response.status_code >= 400:
                        raise HTTPException(
                            400,
                            f"Media URL not accessible: HTTP {
                            response.status_code}",
                        )
                except httpx.TimeoutException as exc:
                    raise HTTPException(400, "Media URL request timeout") from exc
                except Exception as e:
                    raise HTTPException(
                        400,
                        f"Cannot access media URL: {
                        str(e)}",
                    ) from e

            source_url = media_url
            source_key = None  # No S3 key for URL sources

        # Create task in database and publish messages in transaction-like
        # manner
        try:
            # Store v2 config directly as dict in database
            config_dict = transcode_config.model_dump()

            task = await TaskCRUD.create_task(
                db=db,
                task_id=task_id,
                source_url=source_url,
                source_key=source_key,
                config=config_dict,
                callback_url=callback_url,
                callback_auth=callback_auth_obj.model_dump() if callback_auth_obj else None,
                pubsub_topic=pubsub_topic,
            )

            # Publish transcode messages for each profile
            published_count = 0
            failed_profiles = []

            logger.info(
                f"=== PUBLISHING START: task {task_id} with {len(transcode_config.profiles)} profiles ==="
            )

            for i, profile in enumerate(transcode_config.profiles, 1):
                try:
                    logger.info(
                        f"Publishing v2 {i}/{len(transcode_config.profiles)}: profile {profile.id_profile} for task {task_id}"
                    )

                    # Create v2 message
                    message = UniversalTranscodeMessage(
                        task_id=task_id,
                        source_url=source_url,
                        profile=profile,
                        s3_output_config=transcode_config.s3_output_config,
                        source_key=source_key,
                    )
                    message_id = pubsub_service.publish_universal_transcode_task(message)
                    published_count += 1
                    logger.info(
                        f"✅ Published v2 {i}/{
                        len(
                            transcode_config.profiles)}: profile {
                        profile.id_profile}, message_id: {message_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"❌ Failed to publish v2 {i}/{len(transcode_config.profiles)}: profile {profile.id_profile}, error: {e}"
                    )
                    failed_profiles.append(profile.id_profile)

            logger.info(
                f"=== PUBLISHING COMPLETE: {published_count}/{len(transcode_config.profiles)} messages for task {task_id} ==="
            )
            if failed_profiles:
                logger.warning(f"❌ Failed profiles for task {task_id}: {failed_profiles}")
            else:
                logger.info(f"✅ All profiles published successfully for task {task_id}")

            # Publish face detection task if enabled
            face_detection_published = False
            if (
                    transcode_config.face_detection_config
                    and getattr(transcode_config.face_detection_config, "enabled", False)
            ):
                try:
                    logger.info(f"Publishing face detection task for {task_id}")

                    # Set face detection status to processing
                    await TaskCRUD.update_face_detection_status(db, task_id, TaskStatus.PROCESSING)

                    face_message = FaceDetectionMessage(
                        task_id=task_id,
                        source_url=source_url,
                        config=transcode_config.face_detection_config,
                    )

                    face_message_id = pubsub_service.publish_face_detection_task(face_message)
                    face_detection_published = True
                    logger.info(f"✅ Published face detection task, message_id: {face_message_id}")

                except Exception as e:
                    logger.error(f"❌ Failed to publish face detection task: {e}")
                    await TaskCRUD.update_face_detection_status(
                        db,
                        task_id,
                        TaskStatus.FAILED,
                        error_message=f"Failed to publish face detection task: {str(e)}",
                    )

            # If no messages were published, fail the task and cleanup
            if published_count == 0:
                await TaskCRUD.update_task_status(
                    db,
                    task_id,
                    TaskStatus.FAILED,
                    f"Failed to publish any transcode messages: {failed_profiles}",
                )
                # Clean up uploaded file if exists
                if source_key:
                    try:
                        s3_service.delete_file(source_key)
                    except BaseException:
                        pass
                raise HTTPException(500, f"Failed to publish transcode messages: {failed_profiles}")

            # Update task status to processing only if messages were published
            await TaskCRUD.update_task_status(db, task_id, TaskStatus.PROCESSING)

        except HTTPException:
            # Re-raise HTTP exceptions (already handled)
            raise
        except Exception as e:
            # Handle any unexpected errors during task creation or publishing
            logger.error(f"Unexpected error during task creation/publishing: {e}")
            # Try to clean up the task if it was created
            try:
                if "task" in locals():
                    await TaskCRUD.update_task_status(
                        db, task_id, TaskStatus.FAILED, f"Unexpected error: {str(e)}"
                    )
            except BaseException:
                pass
            # Clean up uploaded file if exists
            if source_key:
                try:
                    s3_service.delete_file(source_key)
                except BaseException:
                    pass
            raise HTTPException(
                500,
                f"Failed to create transcode task: {
                str(e)}",
            ) from e

        return {
            "task_id": task_id,
            "status": "processing",
            "source_url": source_url,
            "input_type": "file" if video else "url",
            "profiles_count": len(transcode_config.profiles),
            "media_detection": filter_summary,
            "face_detection_enabled": bool(
                transcode_config.face_detection_config
                and getattr(transcode_config.face_detection_config, "enabled", False)
            ),
            "face_detection_published": locals().get("face_detection_published", False),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating transcode task: {e}")
        # Clean up uploaded file if exists
        if source_key:
            try:
                s3_service.delete_file(source_key)
            except BaseException:
                pass
        raise HTTPException(500, str(e)) from e


@app.get("/task/{task_id}")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)) -> Dict:
    """Get task status and results"""
    task = await TaskCRUD.get_task(db, task_id)

    if not task:
        raise HTTPException(404, "Task not found")

    def calculate_progress(task):
        """Calculate task progress based on outputs vs expected profiles"""
        if not task.config or not task.config.get("profiles"):
            return {
                "expected_profiles": 0,
                "completed_profiles": 0,
                "failed_profiles": 0,
                "completion_percentage": 0,
            }

        expected_profiles = task.config["profiles"]
        expected_count = len(expected_profiles)

        completed_count = len(task.outputs) if task.outputs else 0
        failed_count = len(task.failed_profiles) if task.failed_profiles else 0

        # Calculate percentage based on processed profiles (completed + failed)
        processed_count = completed_count + failed_count
        completion_percentage = (
            (processed_count / expected_count * 100) if expected_count > 0 else 0
        )

        return {
            "expected_profiles": expected_count,
            "completed_profiles": completed_count,
            "failed_profiles_count": failed_count,
            "completion_percentage": min(round(completion_percentage, 1), 100.0),
        }

    def format_profile_config(profile):
        """Format profile config for display"""
        if not isinstance(profile, dict):
            return {
                "id": str(profile),
                "display_name": str(profile),
                "config_summary": "Basic profile",
            }

        config_summary = []
        output_type = profile.get("output_type", "unknown")

        if output_type == "video":
            if profile.get("video_config"):
                vc = profile["video_config"]
                if vc.get("codec"):
                    config_summary.append(f"Codec: {vc['codec']}")
                if vc.get("max_width") or vc.get("max_height"):
                    config_summary.append(
                        f"Max: {
                        vc.get(
                            'max_width',
                            'auto')}x{
                        vc.get(
                            'max_height',
                            'auto')}"
                    )
                if vc.get("bitrate"):
                    config_summary.append(f"Bitrate: {vc['bitrate']}")
                if vc.get("fps"):
                    config_summary.append(f"FPS: {vc['fps']}")
            elif profile.get("ffmpeg_args"):
                config_summary.append("Custom FFmpeg args")

        elif output_type == "image":
            if profile.get("image_config"):
                ic = profile["image_config"]
                if ic.get("format"):
                    config_summary.append(f"Format: {ic['format']}")
                if ic.get("quality"):
                    config_summary.append(f"Quality: {ic['quality']}%")
                if ic.get("max_width") or ic.get("max_height"):
                    config_summary.append(
                        f"Max: {
                        ic.get(
                            'max_width',
                            'auto')}x{
                        ic.get(
                            'max_height',
                            'auto')}"
                    )

        elif output_type == "gif":
            if profile.get("gif_config"):
                gc = profile["gif_config"]
                if gc.get("fps"):
                    config_summary.append(f"FPS: {gc['fps']}")
                if gc.get("width") or gc.get("height"):
                    config_summary.append(
                        f"Size: {
                        gc.get(
                            'width',
                            'auto')}x{
                        gc.get(
                            'height',
                            'auto')}"
                    )
                if gc.get("duration"):
                    config_summary.append(f"Duration: {gc['duration']}s")

        return {
            "id": profile.get("id_profile", "unknown"),
            "display_name": profile.get("id_profile", "unknown"),
            "output_type": output_type,
            "config_summary": " | ".join(config_summary) if config_summary else "Standard config",
            "full_config": profile,
        }

    # Ensure outputs format compatibility (metadata already included from
    # consumer)
    enhanced_outputs = ensure_outputs_compatibility(task.outputs) if task.outputs else None

    # Face detection info - check v2 config format
    face_detection_enabled = False
    if task.config and task.config.get("face_detection_config"):
        face_detection_config = task.config["face_detection_config"]
        face_detection_enabled = bool(
            face_detection_config and face_detection_config.get("enabled", False)
        )

    # Format face detection results for task status
    face_detection_results = None
    if task.face_detection_results:
        # Process faces to exclude avatar base64 and normed_embedding, but keep
        # URLs
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
                # Keep face image URL
                "face_image_url": face.get("face_image_url"),
                "metrics": face.get("metrics"),
            }
            # Only include non-null values
            face_data = {k: v for k, v in face_data.items() if v is not None}
            faces.append(face_data)

        face_detection_results = {
            "faces": faces,
            "is_change_index": task.face_detection_results.get("is_change_index", False),
        }

    return {
        "task_id": task.task_id,
        "status": task.status,
        "source_url": task.source_url,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "outputs": enhanced_outputs,
        "failed_profiles": task.failed_profiles,
        "config": task.config,
        "profiles": (
            [format_profile_config(p) for p in task.config.get("profiles", [])]
            if task.config
            else []
        ),
        "profiles_count": len(task.config.get("profiles", [])) if task.config else 0,
        "outputs_count": len(task.outputs) if task.outputs else 0,
        "error_message": task.error_message,
        "callback_url": task.callback_url,
        "has_callback": bool(task.callback_url),
        "face_detection_enabled": face_detection_enabled,
        "face_detection_status": task.face_detection_status,
        "face_detection_results": face_detection_results,
        "face_detection_error": task.face_detection_error,
        **calculate_progress(task),
    }


@app.post("/task/{task_id}/callback")
async def resend_callback(task_id: str, db: AsyncSession = Depends(get_db)) -> Dict:
    """Resend callback for completed task"""
    task = await TaskCRUD.get_task(db, task_id)

    if not task:
        raise HTTPException(404, "Task not found")

    if not task.callback_url:
        raise HTTPException(400, "No callback URL configured for this task")

    if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        raise HTTPException(400, "Task is not in a final state (completed/failed)")

    # Send callback
    success = await callback_service.send_callback(task)

    return {"task_id": task_id, "callback_sent": success, "callback_url": task.callback_url}


@app.get("/tasks")
async def list_tasks(
        status: TaskStatus = None,
        limit: int = 50,
        offset: int = 0,
        include_details: bool = False,
        db: AsyncSession = Depends(get_db),
) -> Dict:
    """List tasks by status with pagination and optional details"""
    # Use optimized method
    tasks = await TaskCRUD.get_tasks_optimized(db, status, limit, offset)

    def calculate_progress_fast(task):
        """Fast progress calculation without full config parsing"""
        if not task.config or not task.config.get("profiles"):
            return {
                "expected_profiles": 0,
                "completed_profiles": 0,
                "failed_profiles": 0,
                "completion_percentage": 0,
            }

        expected_count = len(task.config["profiles"])
        completed_count = len(task.outputs) if task.outputs else 0
        failed_count = len(task.failed_profiles) if task.failed_profiles else 0

        processed_count = completed_count + failed_count
        completion_percentage = (
            (processed_count / expected_count * 100) if expected_count > 0 else 0
        )

        return {
            "expected_profiles": expected_count,
            "completed_profiles": completed_count,
            "failed_profiles": failed_count,
            "completion_percentage": min(round(completion_percentage, 1), 100.0),
        }

    # Build response with conditional details
    task_list = []
    for task in tasks:
        task_data = {
            "task_id": task.task_id,
            "status": task.status,
            "source_url": task.source_url,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "profiles_count": len(task.config.get("profiles", [])) if task.config else 0,
            "outputs_count": len(task.outputs) if task.outputs else 0,
            "has_callback": bool(task.callback_url),
            **calculate_progress_fast(task),
        }

        # Include heavy data only if requested
        if include_details:
            task_data.update(
                {
                    "outputs": task.outputs,
                    "failed_profiles": task.failed_profiles,
                    "config": task.config,
                    "profiles": task.config.get("profiles", []) if task.config else [],
                    "error_message": task.error_message,
                }
            )

        task_list.append(task_data)

    return {
        "tasks": task_list,
        "count": len(tasks),
        "limit": limit,
        "offset": offset,
        "has_more": len(tasks) == limit,
    }


@app.get("/tasks/summary")
async def get_tasks_summary(db: AsyncSession = Depends(get_db)) -> Dict:
    """Get tasks summary with counts by status - very fast endpoint"""
    # Get status counts in single query
    result = await db.execute(
        select(TranscodeTaskDB.status, func.count(TranscodeTaskDB.task_id).label("count")).group_by(
            TranscodeTaskDB.status
        )
    )

    status_counts = {row.status: row.count for row in result}

    # Get total count
    total_result = await db.execute(select(func.count(TranscodeTaskDB.task_id)))
    total_count = total_result.scalar()

    return {
        "total_tasks": total_count,
        "status_counts": status_counts,
        "statuses": {
            "pending": status_counts.get(TaskStatus.PENDING, 0),
            "processing": status_counts.get(TaskStatus.PROCESSING, 0),
            "completed": status_counts.get(TaskStatus.COMPLETED, 0),
            "failed": status_counts.get(TaskStatus.FAILED, 0),
        },
    }


@app.get("/task/{task_id}/result")
async def get_task_result(task_id: str, db: AsyncSession = Depends(get_db)) -> Dict:
    """Get formatted task result for copying or callback"""
    task = await TaskCRUD.get_task(db, task_id)

    if not task:
        raise HTTPException(404, "Task not found")

    # Get profile counts from v2 config format
    expected_profiles = len(task.config.get("profiles", [])) if task.config else 0
    completed_profiles = len(task.outputs) if task.outputs else 0
    failed_profiles = len(task.failed_profiles) if task.failed_profiles else 0

    # Face detection info - check v2 config format
    face_detection_enabled = False
    if task.config and task.config.get("face_detection_config"):
        face_detection_config = task.config["face_detection_config"]
        face_detection_enabled = bool(
            face_detection_config and face_detection_config.get("enabled", False)
        )

    # Format outputs
    outputs = []
    if task.outputs:
        for profile_name, profile_outputs in task.outputs.items():
            if isinstance(profile_outputs, list):
                for output in profile_outputs:
                    if isinstance(output, dict) and output.get("url"):
                        outputs.append(
                            {
                                "profile": profile_name,
                                "url": output["url"],
                                "metadata": output.get("metadata", {}),
                                "size": output.get("size"),
                            }
                        )
                    elif isinstance(output, str):
                        outputs.append(
                            {"profile": profile_name, "url": output, "metadata": {}, "size": None}
                        )

    # Format face detection results
    face_detection_results = None
    if task.face_detection_results:
        # Process faces to exclude avatar base64 and normed_embedding, but keep
        # URLs
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
                # Keep face image URL
                "face_image_url": face.get("face_image_url"),
                "metrics": face.get("metrics"),
            }
            # Only include non-null values
            face_data = {k: v for k, v in face_data.items() if v is not None}
            faces.append(face_data)

        face_detection_results = {
            "faces": faces,
            "is_change_index": task.face_detection_results.get("is_change_index", False),
        }

    # Build result object
    result = {
        "task_id": task.task_id,
        "status": task.status.value if hasattr(task.status, "value") else str(task.status),
        "source_url": task.source_url,
        "expected_profiles": expected_profiles,
        "completed_profiles": completed_profiles,
        "failed_profiles": failed_profiles,
        "face_detection_enabled": face_detection_enabled,
        "face_detection_status": (
            task.face_detection_status.value
            if hasattr(task.face_detection_status, "value")
            else str(task.face_detection_status) if task.face_detection_status else None
        ),
        "face_detection_results": face_detection_results,
        "outputs": outputs,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "error_message": task.error_message,
    }

    return result


@app.delete("/task/{task_id}")
async def delete_task(
        task_id: str,
        delete_files: bool = False,
        delete_faces: bool = False,
        db: AsyncSession = Depends(get_db),
) -> Dict:
    """Delete task from database with optional S3 file deletion"""
    task = await TaskCRUD.get_task(db, task_id)

    if not task:
        raise HTTPException(404, "Task not found")

    deleted_files = []
    failed_deletions = []

    # Delete S3 files if requested
    if delete_files:
        logger.info(f"Deleting S3 files for task {task_id}")

        # Delete source file if it was uploaded (has source_key)
        if task.source_key:
            try:
                s3_service.delete_file(task.source_key)
                deleted_files.append(f"source: {task.source_key}")
                logger.info(f"Deleted source file: {task.source_key}")
            except Exception as e:
                failed_deletions.append(f"source: {task.source_key} - {str(e)}")
                logger.error(f"Error deleting source file: {e}")

        # Delete output files
        if task.outputs:
            for profile_id, items in task.outputs.items():
                item_list = items if isinstance(items, list) else [items]

                for item in item_list:
                    # Handle both new format {url, metadata} and old format
                    # (URL string)
                    url = item.get("url") if isinstance(item, dict) else item
                    if not url:
                        continue

                    try:
                        # Extract S3 key from URL
                        if settings.aws_endpoint_public_url in url:
                            key = url.replace(
                                f"{settings.aws_endpoint_public_url}/{settings.aws_bucket_name}/",
                                "",
                            )
                        else:
                            # Handle different URL formats
                            parsed_url = urlparse(url)
                            key = parsed_url.path.lstrip("/")
                            if key.startswith(f"{settings.aws_bucket_name}/"):
                                key = key.replace(f"{settings.aws_bucket_name}/", "")

                        s3_service.delete_file(key)
                        deleted_files.append(f"{profile_id}: {key}")
                        logger.info(f"Deleted output file: {key}")
                    except Exception as e:
                        failed_deletions.append(f"{profile_id}: {url} - {str(e)}")
                        logger.error(f"Error deleting output file {url}: {e}")

        # Delete face detection files if requested
        if delete_faces and task.face_detection_results:
            face_results = task.face_detection_results.get("faces", [])
            for face in face_results:
                # Delete avatar URL
                if face.get("avatar_url"):
                    try:
                        avatar_url = face["avatar_url"]
                        if settings.aws_endpoint_public_url in avatar_url:
                            key = avatar_url.replace(
                                f"{settings.aws_endpoint_public_url}/{settings.aws_bucket_name}/",
                                "",
                            )
                        else:
                            parsed_url = urlparse(avatar_url)
                            key = parsed_url.path.lstrip("/")
                            if key.startswith(f"{settings.aws_bucket_name}/"):
                                key = key.replace(f"{settings.aws_bucket_name}/", "")

                        s3_service.delete_file(key)
                        deleted_files.append(f"face_avatar: {key}")
                        logger.info(f"Deleted face avatar: {key}")
                    except Exception as e:
                        failed_deletions.append(f"face_avatar: {face['avatar_url']} - {str(e)}")
                        logger.error(
                            f"Error deleting face avatar {
                            face['avatar_url']}: {e}"
                        )

                # Delete face image URL
                if face.get("face_image_url"):
                    try:
                        face_image_url = face["face_image_url"]
                        if settings.aws_endpoint_public_url in face_image_url:
                            key = face_image_url.replace(
                                f"{settings.aws_endpoint_public_url}/{settings.aws_bucket_name}/",
                                "",
                            )
                        else:
                            parsed_url = urlparse(face_image_url)
                            key = parsed_url.path.lstrip("/")
                            if key.startswith(f"{settings.aws_bucket_name}/"):
                                key = key.replace(f"{settings.aws_bucket_name}/", "")

                        s3_service.delete_file(key)
                        deleted_files.append(f"face_image: {key}")
                        logger.info(f"Deleted face image: {key}")
                    except Exception as e:
                        failed_deletions.append(f"face_image: {face['face_image_url']} - {str(e)}")
                        logger.error(
                            f"Error deleting face image {
                            face['face_image_url']}: {e}"
                        )

    # Delete from database
    await db.delete(task)
    await db.commit()

    if delete_files:
        logger.info(
            f"Task {task_id} deleted successfully. Deleted {
            len(deleted_files)} files, {
            len(failed_deletions)} failed"
        )
        return {
            "message": "Task deleted successfully",
            "files_deleted": len(deleted_files) > 0,
            "deleted_files": deleted_files,
            "failed_deletions": failed_deletions,
        }
    logger.info(f"Task {task_id} deleted from database successfully (S3 files preserved)")
    return {
        "message": "Task deleted successfully from database",
        "files_deleted": False,
        "note": "S3 files are preserved and not deleted",
    }


@app.post("/task/{task_id}/retry")
async def retry_task(
        task_id: str, delete_files: bool = False, db: AsyncSession = Depends(get_db)
) -> Dict:
    """Retry task - clear results and restart processing with optional S3 file deletion"""
    task = await TaskCRUD.get_task(db, task_id)

    if not task:
        raise HTTPException(404, "Task not found")

    deleted_outputs = []
    failed_deletions = []

    # Delete existing output files from S3 if requested
    if delete_files:
        logger.info(f"Retrying task {task_id} - deleting S3 files and clearing database records")

        if task.outputs:
            for profile_id, items in task.outputs.items():
                item_list = items if isinstance(items, list) else [items]

                for item in item_list:
                    # Handle both new format {url, metadata} and old format
                    # (URL string)
                    url = item.get("url") if isinstance(item, dict) else item
                    if not url:
                        continue

                    try:
                        # Extract S3 key from URL
                        if settings.aws_endpoint_public_url in url:
                            key = url.replace(
                                f"{settings.aws_endpoint_public_url}/{settings.aws_bucket_name}/",
                                "",
                            )
                        else:
                            # Handle different URL formats
                            parsed_url = urlparse(url)
                            key = parsed_url.path.lstrip("/")
                            if key.startswith(f"{settings.aws_bucket_name}/"):
                                key = key.replace(f"{settings.aws_bucket_name}/", "")

                        s3_service.delete_file(key)
                        deleted_outputs.append(f"{profile_id}: {key}")
                        logger.info(f"Deleted output file for retry: {key}")
                    except Exception as e:
                        failed_deletions.append(f"{profile_id}: {url} - {str(e)}")
                        logger.error(f"Error deleting output file for retry {url}: {e}")
    else:
        logger.info(
            f"Retrying task {task_id} - preserving S3 files, only clearing database records"
        )

    # Reset task state
    await TaskCRUD.update_task_status(db, task_id, TaskStatus.PENDING, error_message=None)

    # Clear outputs and failed profiles
    await TaskCRUD.clear_task_results(db, task_id)

    # Reset face detection status if it was enabled
    if task.face_detection_status:
        await TaskCRUD.update_face_detection_status(db, task_id, None)

    # Re-publish task messages using v2 format
    try:
        # Parse v2 config from task
        config = UniversalTranscodeConfig(**task.config)
        published_count = 0

        logger.info(
            f"=== RETRY PUBLISHING V2 START: task {task_id} with {len(config.profiles)} profiles ==="
        )

        for profile in config.profiles:
            try:
                message = UniversalTranscodeMessage(
                    task_id=task_id,
                    source_url=task.source_url,
                    profile=profile,
                    s3_output_config=config.s3_output_config,
                    source_key=task.source_key,
                )

                message_id = pubsub_service.publish_universal_transcode_task(message)
                published_count += 1
                logger.info(
                    f"✅ RETRY: Published v2 profile {
                    profile.id_profile}, message_id: {message_id}"
                )

            except Exception as e:
                logger.error(
                    f"❌ RETRY: Failed to publish v2 profile {
                    profile.id_profile}: {
                    str(e)}"
                )

                # Mark this profile as failed immediately
                await TaskCRUD.add_failed_profile(
                    db, task_id, profile.id_profile, f"Failed to publish retry message: {str(e)}"
                )

        logger.info(
            f"=== RETRY PUBLISHING V2 COMPLETE: {published_count}/{len(config.profiles)} messages for task {task_id} ==="
        )

        # Re-publish face detection task if enabled
        face_detection_published = False
        if config.face_detection_config and getattr(config.face_detection_config, "enabled", False):
            try:
                from ..models.schemas import FaceDetectionMessage

                logger.info(f"RETRY: Publishing face detection task for {task_id}")

                # Set face detection status to processing
                await TaskCRUD.update_face_detection_status(db, task_id, TaskStatus.PROCESSING)

                face_message = FaceDetectionMessage(
                    task_id=task_id, source_url=task.source_url, config=config.face_detection_config
                )

                face_message_id = pubsub_service.publish_face_detection_task(face_message)
                face_detection_published = True
                logger.info(
                    f"✅ RETRY: Published face detection task, message_id: {face_message_id}"
                )

            except Exception as e:
                logger.error(f"❌ RETRY: Failed to publish face detection task: {e}")
                await TaskCRUD.update_face_detection_status(
                    db,
                    task_id,
                    TaskStatus.FAILED,
                    error_message=f"Failed to publish face detection task on retry: {str(e)}",
                )

        if published_count == 0:
            # No messages published, mark as failed
            await TaskCRUD.update_task_status(
                db, task_id, TaskStatus.FAILED, error_message="Failed to publish any retry messages"
            )
            return {
                "message": "Retry failed - no messages could be published",
                "published_profiles": 0,
                "total_profiles": len(config.profiles),
                "files_deleted": delete_files,
                "deleted_outputs": deleted_outputs if delete_files else [],
                "failed_deletions": failed_deletions if delete_files else [],
            }
        else:
            # Update to processing status
            await TaskCRUD.update_task_status(db, task_id, TaskStatus.PROCESSING)

            response = {
                "message": "Task retry initiated successfully",
                "published_profiles": published_count,
                "total_profiles": len(config.profiles),
                "face_detection_retried": face_detection_published,
                "files_deleted": delete_files,
            }

            if delete_files:
                response.update(
                    {"deleted_outputs": deleted_outputs, "failed_deletions": failed_deletions}
                )
            else:
                response["note"] = "S3 files preserved, only database records cleared"

            return response

    except Exception as e:
        logger.error(f"❌ RETRY ERROR for task {task_id}: {str(e)}")
        await TaskCRUD.update_task_status(
            db, task_id, TaskStatus.FAILED, error_message=f"Retry failed: {str(e)}"
        )
        raise HTTPException(500, f"Failed to retry task: {str(e)}")


@app.get("/health")
def health_check():
    """Ultra-fast health check endpoint - synchronous for maximum speed"""
    return {"status": "healthy"}


@app.get("/health/detailed")
async def health_check_detailed():
    """Detailed health check with timing info"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "server": "transcode-api",
        "version": "1.0.0",
    }


@app.get("/health/db")
async def health_check_with_db(db: AsyncSession = Depends(get_db)):
    """Health check with database connection test"""
    import time

    start_time = time.time()

    try:
        # Simple DB query to test connection
        from sqlalchemy import text

        result = await db.execute(text("SELECT 1"))
        db_result = result.scalar()

        db_time = time.time() - start_time

        return {
            "status": "healthy",
            "database": {
                "status": "connected",
                "query_result": db_result,
                "connection_time_ms": round(db_time * 1000, 2),
            },
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": {"status": "error", "error": str(e)},
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }


# Config Templates Management Endpoints


@app.get("/config-templates")
async def list_config_templates(db: AsyncSession = Depends(get_db)) -> Dict:
    """List all config templates"""
    try:
        templates = await ConfigTemplateCRUD.get_all_templates(db)
        return {
            "templates": [
                {
                    "template_id": template.template_id,
                    "name": template.name,
                    "config": template.config,
                    "created_at": template.created_at,
                    "updated_at": template.updated_at,
                }
                for template in templates
            ],
            "count": len(templates),
        }
    except Exception as e:
        logger.error(f"Error listing config templates: {e}")
        raise HTTPException(500, "Failed to list config templates")


@app.get("/config-templates/{template_id}")
async def get_config_template(template_id: str, db: AsyncSession = Depends(get_db)) -> Dict:
    """Get specific config template"""
    try:
        template = await ConfigTemplateCRUD.get_template(db, template_id)
        if not template:
            raise HTTPException(404, "Config template not found")

        return {
            "template_id": template.template_id,
            "name": template.name,
            "config": template.config,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting config template: {e}")
        raise HTTPException(500, "Failed to get config template")


@app.post("/config-templates")
async def create_config_template(
        request: ConfigTemplateRequest, db: AsyncSession = Depends(get_db)
) -> Dict:
    """Create new config template"""
    try:
        template = await ConfigTemplateCRUD.create_template(db, request)
        return {
            "template_id": template.template_id,
            "name": template.name,
            "config": template.config,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
            "status": "created",
        }
    except Exception as e:
        logger.error(f"Error creating config template: {e}")
        raise HTTPException(500, "Failed to create config template")


@app.put("/config-templates/{template_id}")
async def update_config_template(
        template_id: str, request: ConfigTemplateRequest, db: AsyncSession = Depends(get_db)
) -> Dict:
    """Update existing config template"""
    try:
        template = await ConfigTemplateCRUD.update_template(db, template_id, request)
        if not template:
            raise HTTPException(404, "Config template not found")

        return {
            "template_id": template.template_id,
            "name": template.name,
            "config": template.config,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
            "status": "updated",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config template: {e}")
        raise HTTPException(500, "Failed to update config template")


@app.delete("/config-templates/{template_id}")
async def delete_config_template(template_id: str, db: AsyncSession = Depends(get_db)) -> Dict:
    """Delete config template"""
    try:
        success = await ConfigTemplateCRUD.delete_template(db, template_id)
        if not success:
            raise HTTPException(404, "Config template not found")

        return {
            "message": "Config template deleted successfully",
            "template_id": template_id,
            "status": "deleted",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting config template: {e}")
        raise HTTPException(500, "Failed to delete config template")

# Legacy profile endpoints removed - use /config-templates instead
