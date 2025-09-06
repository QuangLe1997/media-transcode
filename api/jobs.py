from flask import Blueprint, request, jsonify, g

from config import get_config
from database.models import db, Job, Media, TranscodeTask, TranscodeOutput
from services.auth_service import AuthService
from services.ffmpeg_service import get_ffmpeg_service
from services.s3_service import S3Service
from services.transcode_service import TranscodeService
from tasks.image_tasks import process_all_image_tasks, cleanup_job
from tasks.video_tasks import process_all_video_tasks

jobs_bp = Blueprint('jobs', __name__)

# Initialize services
config = get_config()
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


@jobs_bp.route('/', methods=['GET'])
@AuthService.token_required
def get_jobs():
    """Get all jobs for the current user."""
    user = g.current_user

    # Get all jobs for this user
    jobs = Job.query.filter_by(user_id=user.id).order_by(Job.created_at.desc()).all()

    jobs_list = []
    for job in jobs:
        job_data = {
            'id': job.id,
            'status': job.status,
            'created_at': job.created_at.isoformat(),
            'updated_at': job.updated_at.isoformat(),
            'config_id': job.config_id,
            'config_name': job.config.name if job.config else 'Deleted Configuration',
            'media_count': len(job.media)
        }
        jobs_list.append(job_data)

    return jsonify({'jobs': jobs_list}), 200


@jobs_bp.route('/<int:job_id>', methods=['GET'])
@AuthService.token_required
def get_job(job_id):
    """Get details for a specific job."""
    user = g.current_user

    # Find job
    job = Job.query.get(job_id)

    if not job:
        return jsonify({'message': 'Job not found'}), 404

    # Check ownership
    if job.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    # Get media for this job
    media_items = Media.query.filter_by(job_id=job.id).all()

    media_list = []
    for media in media_items:
        # Get tasks for this media
        tasks = TranscodeTask.query.filter_by(media_id=media.id).all()

        task_list = []
        for task in tasks:
            # Get outputs for this task
            outputs = TranscodeOutput.query.filter_by(task_id=task.id).all()

            task_list.append({
                'id': task.id,
                'task_type': task.task_type,
                'profile_name': task.profile_name,
                'status': task.status,
                'error_message': task.error_message,
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'outputs': [{
                    'id': output.id,
                    'output_filename': output.output_filename,
                    's3_url': output.s3_url,
                    'file_size': output.file_size,
                    'width': output.width,
                    'height': output.height,
                    'duration': output.duration,
                    'format': output.format
                } for output in outputs]
            })

        media_list.append({
            'id': media.id,
            'original_filename': media.original_filename,
            'file_type': media.file_type,
            'file_size': media.file_size,
            'mime_type': media.mime_type,
            'width': media.width,
            'height': media.height,
            'duration': media.duration,
            'tasks': task_list
        })

    return jsonify({
        'id': job.id,
        'status': job.status,
        'created_at': job.created_at.isoformat(),
        'updated_at': job.updated_at.isoformat(),
        'config_id': job.config_id,
        'media': media_list
    }), 200


@jobs_bp.route('/', methods=['POST'])
@AuthService.token_required
def create_job():
    """Create a new job."""
    user = g.current_user
    data = request.get_json()

    # Validate required fields
    if not data or not data.get('config_id'):
        return jsonify({'message': 'Missing required fields'}), 400

    # Create job
    job = transcode_service.create_job(user.id, data['config_id'])

    return jsonify({
        'message': 'Job created successfully',
        'id': job.id
    }), 201


@jobs_bp.route('/<int:job_id>/process', methods=['POST'])
@AuthService.token_required
def process_job(job_id):
    """Start processing a job."""
    user = g.current_user

    # Find job
    job = Job.query.get(job_id)

    if not job:
        return jsonify({'message': 'Job not found'}), 404

    # Check ownership
    if job.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    # Get media items and create tasks
    media_items = Media.query.filter_by(job_id=job.id).all()

    if not media_items:
        return jsonify({'message': 'No media found for this job'}), 400

    # Create transcode tasks for each media
    for media in media_items:
        transcode_service.create_transcode_tasks(media.id)

    # Start processing tasks in the background
    video_task = process_all_video_tasks.delay(job.id)
    image_task = process_all_image_tasks.delay(job.id)

    # Schedule cleanup
    cleanup_job.apply_async(args=[job.id], countdown=3600)  # Clean up after 1 hour

    return jsonify({
        'message': 'Job processing started',
        'video_task_id': video_task.id,
        'image_task_id': image_task.id
    }), 200


@jobs_bp.route('/<int:job_id>', methods=['DELETE'])
@AuthService.token_required
def delete_job(job_id):
    """Delete a job."""
    user = g.current_user

    # Find job
    job = Job.query.get(job_id)

    if not job:
        return jsonify({'message': 'Job not found'}), 404

    # Check ownership
    if job.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    # First clean up any local files
    transcode_service.cleanup_job(job.id)

    # Delete from database (cascade to media, tasks, and outputs)
    db.session.delete(job)
    db.session.commit()

    return jsonify({'message': 'Job deleted successfully'}), 200


@jobs_bp.route('/stats', methods=['GET'])
@AuthService.token_required
def get_job_stats():
    """Get statistics for user's jobs."""
    user = g.current_user

    # Total jobs
    total_jobs = Job.query.filter_by(user_id=user.id).count()

    # Jobs by status
    pending_jobs = Job.query.filter_by(user_id=user.id, status='pending').count()
    processing_jobs = Job.query.filter_by(user_id=user.id, status='processing').count()
    completed_jobs = Job.query.filter_by(user_id=user.id, status='completed').count()
    failed_jobs = Job.query.filter_by(user_id=user.id, status='failed').count()

    # Total media processed
    total_media = db.session.query(Media).join(Job).filter(Job.user_id == user.id).count()

    # Media by type
    video_count = db.session.query(Media).join(Job).filter(
        Job.user_id == user.id,
        Media.file_type == 'video'
    ).count()

    image_count = db.session.query(Media).join(Job).filter(
        Job.user_id == user.id,
        Media.file_type == 'image'
    ).count()

    # Total outputs generated
    total_outputs = db.session.query(TranscodeOutput).join(
        TranscodeTask
    ).join(Media).join(Job).filter(Job.user_id == user.id).count()

    return jsonify({
        'total_jobs': total_jobs,
        'jobs_by_status': {
            'pending': pending_jobs,
            'processing': processing_jobs,
            'completed': completed_jobs,
            'failed': failed_jobs
        },
        'media': {
            'total': total_media,
            'videos': video_count,
            'images': image_count
        },
        'outputs': total_outputs
    }), 200


@jobs_bp.route('/search', methods=['GET'])
@AuthService.token_required
def search_jobs():
    """Search jobs with filters."""
    user = g.current_user

    # Get query parameters
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    config_id = request.args.get('config_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Build query
    query = Job.query.filter_by(user_id=user.id)

    if status:
        query = query.filter_by(status=status)

    if config_id:
        query = query.filter_by(config_id=config_id)

    if date_from:
        try:
            from datetime import datetime
            date_from_obj = datetime.fromisoformat(date_from)
            query = query.filter(Job.created_at >= date_from_obj)
        except:
            pass

    if date_to:
        try:
            from datetime import datetime
            date_to_obj = datetime.fromisoformat(date_to)
            query = query.filter(Job.created_at <= date_to_obj)
        except:
            pass

    # Order by created date desc
    query = query.order_by(Job.created_at.desc())

    # Paginate
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'jobs': [{
            'id': job.id,
            'status': job.status,
            'created_at': job.created_at.isoformat(),
            'updated_at': job.updated_at.isoformat(),
            'config_id': job.config_id,
            'media_count': len(job.media)
        } for job in paginated.items],
        'pagination': {
            'page': paginated.page,
            'per_page': paginated.per_page,
            'total': paginated.total,
            'pages': paginated.pages,
            'has_prev': paginated.has_prev,
            'has_next': paginated.has_next
        }
    }), 200


@jobs_bp.route('/batch/delete', methods=['POST'])
@AuthService.token_required
def batch_delete_jobs():
    """Delete multiple jobs at once."""
    user = g.current_user
    data = request.get_json()

    if not data or not data.get('job_ids'):
        return jsonify({'message': 'Missing job IDs'}), 400

    job_ids = data.get('job_ids', [])
    deleted_count = 0

    for job_id in job_ids:
        job = Job.query.get(job_id)
        if job and job.user_id == user.id:
            # Clean up files
            transcode_service.cleanup_job(job.id)
            # Delete from database
            db.session.delete(job)
            deleted_count += 1

    db.session.commit()

    return jsonify({
        'message': f'Successfully deleted {deleted_count} jobs',
        'deleted_count': deleted_count
    }), 200


@jobs_bp.route('/<int:job_id>/retry', methods=['POST'])
@AuthService.token_required
def retry_job(job_id):
    """Retry a failed job."""
    user = g.current_user

    # Find job
    job = Job.query.get(job_id)

    if not job:
        return jsonify({'message': 'Job not found'}), 404

    # Check ownership
    if job.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    # Check if job can be retried
    if job.status not in ['failed', 'partial']:
        return jsonify({'message': 'Job cannot be retried in current status'}), 400

    # Reset job status
    job.status = 'pending'

    # Reset failed tasks
    failed_tasks = TranscodeTask.query.join(Media).filter(
        Media.job_id == job.id,
        TranscodeTask.status == 'failed'
    ).all()

    for task in failed_tasks:
        task.status = 'pending'
        task.error_message = None
        task.started_at = None
        task.completed_at = None

    db.session.commit()

    # Start processing again
    video_task = process_all_video_tasks.delay(job.id)
    image_task = process_all_image_tasks.delay(job.id)

    return jsonify({
        'message': 'Job retry started',
        'video_task_id': video_task.id,
        'image_task_id': image_task.id
    }), 200
