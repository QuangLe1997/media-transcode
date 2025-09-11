import logging

from config import get_config
from services.ffmpeg_service import get_ffmpeg_service
from services.s3_service import S3Service
from services.transcode_service import TranscodeService
from .celery_config import celery_app

# Get configuration
config = get_config()

# # Setup services
# ffmpeg_service = FFmpegService(
#     ffmpeg_path=config.FFMPEG_PATH,
#     ffprobe_path=config.FFPROBE_PATH,
#     gpu_enabled=config.GPU_ENABLED,
#     gpu_type=config.GPU_TYPE
# )
ffmpeg_service = get_ffmpeg_service(
)

s3_service = S3Service(
    aws_access_key_id=config.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
    region_name=config.AWS_REGION,
    bucket_name=config.S3_BUCKET
)

transcode_service = TranscodeService(
    ffmpeg_service=ffmpeg_service,
    s3_service=s3_service,
    temp_dir=config.TEMP_STORAGE_PATH
)

logger = logging.getLogger(__name__)


@celery_app.task(name='tasks.video_tasks.transcode_video')
def transcode_video(task_id):
    """Process a video transcode task."""
    logger.info(f"Processing video transcode task {task_id}")
    return transcode_service.process_video_transcode(task_id)


@celery_app.task(name='tasks.video_tasks.create_video_preview')
def create_video_preview(task_id):
    """Process a video preview task (now GIF creation)."""
    logger.info(f"Processing video preview task {task_id}")
    return transcode_service.process_video_preview(task_id)


@celery_app.task(name='tasks.video_tasks.create_video_thumbnail')
def create_video_thumbnail(task_id):
    """Process a video thumbnail task."""
    logger.info(f"Processing video thumbnail task {task_id}")
    return transcode_service.process_video_thumbnail(task_id)


@celery_app.task(name='tasks.video_tasks.detect_faces')
def detect_faces(task_id):
    """Process face detection task for video."""
    logger.info(f"Processing face detection task {task_id}")
    return transcode_service.process_face_detection(task_id)


@celery_app.task(name='tasks.video_tasks.process_all_video_tasks')
def process_all_video_tasks(job_id):
    """Process all video tasks for a job."""
    logger.info(f"Processing all video tasks for job {job_id}")

    from database.models import Media, TranscodeTask
    # Thêm đường dẫn dự án vào sys.path
    import sys
    import os
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)

    # Tạo Flask app và app context
    # Điều chỉnh import dựa trên cấu trúc dự án
    import importlib.util
    spec = importlib.util.spec_from_file_location("app", os.path.join(project_dir, "app.py"))
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)

    # Lấy hàm create_app (nếu có)
    create_app = getattr(app_module, "create_app", None)
    # Hoặc lấy app instance trực tiếp (nếu có)
    app = getattr(app_module, "app", None)

    if create_app:
        app = create_app()

    if not app:
        raise RuntimeError("Could not find Flask app")

    with app.app_context():

        # Get all video media for this job
        media_list = Media.query.filter_by(job_id=job_id, file_type='video').all()

        results = {
            'total': 0,
            'success': 0,
            'failed': 0
        }

        for media in media_list:
            # Get all tasks for this media
            tasks = TranscodeTask.query.filter_by(media_id=media.id).all()

            for task in tasks:
                results['total'] += 1
                if transcode_service.process_task(task.id):
                    results['success'] += 1
                else:
                    results['failed'] += 1

        # Update job status based on results
        _update_job_status(job_id)

        return results


def _update_job_status(job_id):
    """Update job status based on task completion."""
    from database.models import Job, Media, TranscodeTask, db

    job = Job.query.get(job_id)
    if not job:
        return

    # Get all tasks for this job
    all_tasks = db.session.query(TranscodeTask).join(Media).filter(Media.job_id == job_id).all()

    if not all_tasks:
        job.status = 'completed'
        db.session.commit()
        return

    # Count task statuses
    pending_count = sum(1 for task in all_tasks if task.status == 'pending')
    processing_count = sum(1 for task in all_tasks if task.status == 'processing')
    completed_count = sum(1 for task in all_tasks if task.status == 'completed')
    failed_count = sum(1 for task in all_tasks if task.status == 'failed')

    total_count = len(all_tasks)

    # Determine job status
    if processing_count > 0 or pending_count > 0:
        job.status = 'processing'
    elif failed_count == total_count:
        job.status = 'failed'
    elif completed_count == total_count:
        job.status = 'completed'
    elif completed_count > 0:
        job.status = 'partial'
    else:
        job.status = 'failed'

    db.session.commit()
    logger.info(
        f"Updated job {job_id} status to {job.status} (completed: {completed_count}, failed: {failed_count}, total: {total_count})")
