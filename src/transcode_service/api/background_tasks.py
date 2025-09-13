import asyncio
import logging

from ..core.db import TaskCRUD, get_db
from ..models.schemas import FaceDetectionResult, TaskStatus
from ..models.schemas_v2 import UniversalTranscodeResult
from ..services import pubsub_service, s3_service
from ..services.callback_service import callback_service

logger = logging.getLogger(__name__)


async def handle_transcode_result(result: UniversalTranscodeResult):
    """Handle transcode result from Pub/Sub - V2 ONLY"""
    await _handle_transcode_result_common(result)


async def handle_universal_transcode_result(result: UniversalTranscodeResult):
    """Handle universal transcode result from Pub/Sub v2"""
    await _handle_transcode_result_common(result)


async def _handle_transcode_result_common(result: UniversalTranscodeResult):
    """Handle transcode result from Pub/Sub"""
    logger.info(
        f"📥 === BACKGROUND PROCESSING RESULT: task {
            result.task_id}, profile {
            result.profile_id} ==="
    )
    logger.info(
        f"Result status: {
            result.status}, URLs count: {
            len(
                result.output_urls) if result.output_urls else 0}"
    )

    try:
        async for db in get_db():
            # Get task
            task = await TaskCRUD.get_task(db, result.task_id)
            if not task:
                logger.error(f"❌ Task not found: {result.task_id}")
                return

            logger.info(
                f"Found task with status: {
                    task.status}, current outputs: {
                    len(
                        task.outputs) if task.outputs else 0}"
            )

            # Ignore results for FAILED tasks (don't reset them)
            if task.status == TaskStatus.FAILED:
                logger.info(
                    f"Task {
                        result.task_id} is FAILED, ignoring transcode result"
                )
                return

            # Update task status to PROCESSING
            if task.status == TaskStatus.PENDING:
                await TaskCRUD.update_task_status(db, result.task_id, TaskStatus.PROCESSING)
                logger.info(
                    f"🔄 Task {
                        result.task_id} status updated to PROCESSING"
                )

            if result.status == "completed" and result.output_urls:
                logger.info(
                    f"Adding outputs for profile {
                        result.profile_id}: {
                        result.output_urls}"
                )
                # Add output URLs and metadata to task
                await TaskCRUD.add_task_output(
                    db, result.task_id, result.profile_id, result.output_urls, result.metadata
                )
                logger.info(
                    f"✅ Successfully added outputs for profile {
                        result.profile_id}"
                )

                # Check if all profiles are completed - get from task config
                task = await TaskCRUD.get_task(db, result.task_id)

                current_outputs = len(task.outputs) if task.outputs else 0
                expected_outputs = len(task.config.get("profiles", [])) if task.config else 0
                logger.info(
                    f"Progress check: {current_outputs}/{expected_outputs} profiles completed"
                )

                # Always check if task should be completed (including partial
                # completion)
                logger.info(
                    f"🔄 Checking if task {
                        result.task_id} should be completed..."
                )
                updated_task = await TaskCRUD.mark_task_completed_check_all(db, result.task_id)

                if updated_task and updated_task.status == TaskStatus.COMPLETED:
                    logger.info(f"🎉 Task fully completed: {result.task_id}")
                    # Delete source file only if it was uploaded (has
                    # source_key)
                    if updated_task.source_key:
                        try:
                            s3_service.delete_file(updated_task.source_key)
                            logger.info(
                                f"Deleted source file: {
                                    updated_task.source_key}"
                            )
                        except Exception as e:
                            logger.error(f"Error deleting source file: {e}")

                    # Send callback if configured
                    if updated_task.callback_url:
                        await callback_service.retry_callback(updated_task)
                        logger.info(
                            f"Callback sent for completed task: {
                                updated_task.task_id}"
                        )

            elif result.status == "failed":
                # Add failed profile information
                await TaskCRUD.add_failed_profile(
                    db, result.task_id, result.profile_id, result.error_message
                )

                # Check if all profiles are processed (completed or failed)
                task = await TaskCRUD.get_task(db, result.task_id)

                completed_profiles = len(task.outputs) if task.outputs else 0
                failed_profiles = len(task.failed_profiles) if task.failed_profiles else 0
                total_processed = completed_profiles + failed_profiles

                expected_profiles = len(task.config.get("profiles", [])) if task.config else 0

                if total_processed >= expected_profiles:
                    # All profiles processed
                    if completed_profiles > 0:
                        # Some profiles succeeded, mark as completed with
                        # partial failure
                        await TaskCRUD.update_task_status(
                            db,
                            result.task_id,
                            TaskStatus.COMPLETED,
                            error_message=f"Partially completed: {failed_profiles} profile(s) failed",
                        )
                    else:
                        # All profiles failed, mark as failed
                        await TaskCRUD.update_task_status(
                            db,
                            result.task_id,
                            TaskStatus.FAILED,
                            error_message=f"All {failed_profiles} profile(s) failed",
                        )

                    # Get updated task for accurate data
                    updated_task = await TaskCRUD.get_task(db, result.task_id)

                    # Delete source file only if it was uploaded (has
                    # source_key)
                    if updated_task.source_key:
                        try:
                            s3_service.delete_file(updated_task.source_key)
                            logger.info(
                                f"Deleted source file: {
                                    updated_task.source_key}"
                            )
                        except Exception as e:
                            logger.error(f"Error deleting source file: {e}")

                    # Send callback if configured
                    if updated_task.callback_url:
                        await callback_service.retry_callback(updated_task)
                        logger.info(
                            f"Callback sent for processed task: {
                                updated_task.task_id}"
                        )

            logger.info(
                f"✅ === BACKGROUND PROCESSING COMPLETE: task {
                    result.task_id}, profile {
                    result.profile_id} ==="
            )

    except Exception as e:
        logger.error(
            f"❌ === BACKGROUND PROCESSING ERROR: task {
                result.task_id}, profile {
                result.profile_id} ==="
        )
        logger.error(f"Error details: {str(e)}")


async def handle_face_detection_result(result: FaceDetectionResult):
    """Handle face detection result from Pub/Sub"""
    logger.info(
        f"📥 === BACKGROUND PROCESSING FACE DETECTION RESULT: task {
            result.task_id} ==="
    )
    logger.info(f"Face detection status: {result.status}")

    try:
        async for db in get_db():
            # Get task
            task = await TaskCRUD.get_task(db, result.task_id)
            if not task:
                logger.error(f"❌ Task not found: {result.task_id}")
                return

            logger.info(
                f"Found task with face detection status: {
                    task.face_detection_status}"
            )

            # Face detection results should not reset existing tasks or delete S3 files
            # They should only update face detection status and results
            logger.info(
                f"Processing face detection result for existing task {
                    result.task_id} (status: {
                    task.status})"
            )

            # Update task status to PROCESSING
            if task.status == TaskStatus.PENDING:
                await TaskCRUD.update_task_status(db, result.task_id, TaskStatus.PROCESSING)
                logger.info(
                    f"🔄 Task {
                        result.task_id} status updated to PROCESSING"
                )

            if result.status == "completed":
                logger.info(
                    f"Face detection completed for task {
                        result.task_id}"
                )
                # Add face detection results to task
                face_results = {
                    "faces": result.faces,
                    "is_change_index": result.is_change_index,
                    "output_urls": result.output_urls,
                    "completed_at": (
                        result.completed_at.isoformat() if result.completed_at else None
                    ),
                }

                await TaskCRUD.add_face_detection_results(db, result.task_id, face_results)
                logger.info(f"✅ Successfully added face detection results")

                # Check if task is fully completed
                updated_task = await TaskCRUD.mark_task_completed_check_all(db, result.task_id)

                if updated_task and updated_task.status == TaskStatus.COMPLETED:
                    logger.info(f"🎉 Task fully completed: {result.task_id}")

                    # Delete source file only if it was uploaded (has
                    # source_key)
                    if updated_task.source_key:
                        try:
                            s3_service.delete_file(updated_task.source_key)
                            logger.info(
                                f"Deleted source file: {
                                    updated_task.source_key}"
                            )
                        except Exception as e:
                            logger.error(f"Error deleting source file: {e}")

                    # Send callback if configured
                    if updated_task.callback_url:
                        await callback_service.retry_callback(updated_task)
                        logger.info(
                            f"Callback sent for completed task: {
                                updated_task.task_id}"
                        )

            elif result.status == "failed":
                logger.error(
                    f"Face detection failed for task {
                        result.task_id}: {
                        result.error_message}"
                )
                # Update face detection status to failed
                await TaskCRUD.update_face_detection_status(
                    db, result.task_id, TaskStatus.FAILED, result.error_message
                )

                # Check if task should be marked as failed overall
                # (depends on whether transcode is complete and successful)
                task = await TaskCRUD.get_task(db, result.task_id)
                expected_profiles = len(task.config.get("profiles", [])) if task.config else 0

                if task.outputs and len(task.outputs) >= expected_profiles:
                    # Transcode is complete, but face detection failed
                    # Mark as completed with partial failure
                    await TaskCRUD.update_task_status(
                        db,
                        result.task_id,
                        TaskStatus.COMPLETED,
                        error_message=f"Completed with face detection failure: {result.error_message}",
                    )

                    # Send callback for partial completion
                    if task.callback_url:
                        await callback_service.retry_callback(task)
                        logger.info(
                            f"Callback sent for partially completed task: {
                                task.task_id}"
                        )

            logger.info(
                f"✅ === FACE DETECTION PROCESSING COMPLETE: task {
                    result.task_id} ==="
            )

    except Exception as e:
        logger.error(
            f"❌ === FACE DETECTION PROCESSING ERROR: task {
                result.task_id} ==="
        )
        logger.error(f"Error details: {str(e)}")


async def face_detection_subscriber():
    """Background task to subscribe to face detection results"""
    logger.info("Starting face detection subscriber background task")

    # Initial delay to let API start properly
    await asyncio.sleep(3)

    while True:
        try:
            # Pull face detection results
            results = pubsub_service.pull_face_detection_results(max_messages=10)

            if results:
                logger.info(
                    f"🔄 FACE DETECTION SUBSCRIBER: Processing {
                        len(results)} face detection results"
                )
                for result in results:
                    await handle_face_detection_result(result)
                logger.info(
                    f"✅ FACE DETECTION SUBSCRIBER: Completed processing {
                        len(results)} face detection results"
                )

            # Wait before next pull - shorter if we had results
            wait_time = 2 if results else 5
            await asyncio.sleep(wait_time)

        except Exception as e:
            logger.error(f"Error in face detection subscriber: {e}")
            await asyncio.sleep(10)


async def transcode_result_subscriber():
    """Background task to subscribe to transcode results - DISABLED (v1 system)"""
    logger.info("V1 transcode result subscriber is DISABLED - using v2 system only")
    # V1 system disabled - all processing moved to v2
    while True:
        await asyncio.sleep(60)  # Sleep indefinitely


async def universal_transcode_result_subscriber():
    """Background task to subscribe to universal transcode results (v2)"""
    logger.info("Starting universal transcode result subscriber background task")

    # Initial delay to let API start properly
    await asyncio.sleep(2)

    while True:
        try:
            # Pull universal transcode results (v2)
            results = pubsub_service.pull_universal_results(max_messages=10)

            if results:
                logger.info(
                    f"🔄 UNIVERSAL TRANSCODE SUBSCRIBER: Processing {
                        len(results)} v2 results"
                )
                for result in results:
                    await handle_universal_transcode_result(result)
                logger.info(
                    f"✅ UNIVERSAL TRANSCODE SUBSCRIBER: Completed processing {
                        len(results)} v2 results"
                )

            # Wait before next pull
            wait_time = 2 if results else 5
            await asyncio.sleep(wait_time)

        except Exception as e:
            logger.error(f"Error in universal transcode result subscriber: {e}")
            await asyncio.sleep(10)


async def result_subscriber():
    """Background task to subscribe to all result types"""
    logger.info("Starting result subscriber background task")

    # Run v2 and face detection subscribers only (v1 disabled)
    await asyncio.gather(
        universal_transcode_result_subscriber(),  # v2 results only
        face_detection_subscriber(),  # face detection results
        return_exceptions=True,
    )
