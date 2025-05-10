import logging

from config import get_config
from services.ffmpeg_service import FFmpegService
from services.s3_service import S3Service
from services.transcode_service import TranscodeService
from .celery_config import celery_app

# Get configuration
config = get_config()

# Setup services
ffmpeg_service = FFmpegService(
    ffmpeg_path=config.FFMPEG_PATH,
    ffprobe_path=config.FFPROBE_PATH,
    gpu_enabled=config.GPU_ENABLED,
    gpu_type=config.GPU_TYPE
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

    return results