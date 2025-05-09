import logging
from .celery_config import celery_app
from services.transcode_service import TranscodeService
from services.ffmpeg_service import FFmpegService
from services.s3_service import S3Service
from config import get_config

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


@celery_app.task(name='tasks.image_tasks.transcode_image')
def transcode_image(task_id):
    """Process an image transcode task."""
    logger.info(f"Processing image transcode task {task_id}")
    return transcode_service.process_image_transcode(task_id)


@celery_app.task(name='tasks.image_tasks.create_image_thumbnail')
def create_image_thumbnail(task_id):
    """Process an image thumbnail task."""
    logger.info(f"Processing image thumbnail task {task_id}")
    return transcode_service.process_image_thumbnail(task_id)


@celery_app.task(name='tasks.image_tasks.process_all_image_tasks')
def process_all_image_tasks(job_id):
    """Process all image tasks for a job."""
    logger.info(f"Processing all image tasks for job {job_id}")

    from database.models import Media, TranscodeTask

    # Get all image media for this job
    media_list = Media.query.filter_by(job_id=job_id, file_type='image').all()

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


@celery_app.task(name='tasks.image_tasks.cleanup_job')
def cleanup_job(job_id):
    """Clean up job temporary files."""
    logger.info(f"Cleaning up job {job_id}")
    return transcode_service.cleanup_job(job_id)