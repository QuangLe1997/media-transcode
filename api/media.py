import os
import uuid
from flask import Blueprint, request, jsonify, g, current_app
from werkzeug.utils import secure_filename
import magic
from database.models import db, Job, Media
from services.auth_service import AuthService
from services.transcode_service import TranscodeService
from services.ffmpeg_service import FFmpegService
from services.s3_service import S3Service
from config import get_config

media_bp = Blueprint('media', __name__)

# Initialize services
config = get_config()
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


def allowed_file(filename, file_type='both'):
    """Check if the file extension is allowed."""
    if '.' not in filename:
        return False

    extension = filename.rsplit('.', 1)[1].lower()

    if file_type == 'video':
        return extension in config.ALLOWED_VIDEO_EXTENSIONS
    elif file_type == 'image':
        return extension in config.ALLOWED_IMAGE_EXTENSIONS
    else:
        return (extension in config.ALLOWED_VIDEO_EXTENSIONS or
                extension in config.ALLOWED_IMAGE_EXTENSIONS)


@media_bp.route('/upload/<int:job_id>', methods=['POST'])
@AuthService.token_required
def upload_media(job_id):
    """Upload media files to a job."""
    user = g.current_user

    # Find job
    job = Job.query.get(job_id)

    if not job:
        return jsonify({'message': 'Job not found'}), 404

    # Check ownership
    if job.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    # Check if job is already processing or completed
    if job.status not in ['pending', 'created']:
        return jsonify({'message': f'Job is already in {job.status} state'}), 400

    # Check if the post request has the file part
    if 'files[]' not in request.files:
        return jsonify({'message': 'No files part in the request'}), 400

    files = request.files.getlist('files[]')

    if not files or files[0].filename == '':
        return jsonify({'message': 'No files selected'}), 400

    uploaded_media = []

    for file in files:
        # Check if file is allowed
        if not allowed_file(file.filename):
            continue

        # Secure the filename and add a unique ID
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"

        # Create upload directory if it doesn't exist
        upload_folder = os.path.join(config.UPLOAD_FOLDER, f'job_{job_id}')
        os.makedirs(upload_folder, exist_ok=True)

        # Save the file
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        # Determine file type and MIME type
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(file_path)

        if mime_type.startswith('video/'):
            file_type = 'video'
        elif mime_type.startswith('image/'):
            file_type = 'image'
        else:
            # Remove unsupported file
            os.remove(file_path)
            continue

        # Add to job
        media = transcode_service.add_media_to_job(
            job_id=job_id,
            file_path=file_path,
            original_filename=filename,
            file_type=file_type,
            mime_type=mime_type
        )

        uploaded_media.append({
            'id': media.id,
            'original_filename': media.original_filename,
            'file_type': media.file_type,
            'file_size': media.file_size,
            'mime_type': media.mime_type,
            'width': media.width,
            'height': media.height,
            'duration': media.duration,
        })

    return jsonify({
        'message': f'Successfully uploaded {len(uploaded_media)} files',
        'media': uploaded_media
    }), 201


@media_bp.route('/<int:media_id>', methods=['GET'])
@AuthService.token_required
def get_media(media_id):
    """Get details for a specific media."""
    user = g.current_user

    # Find media
    media = Media.query.get(media_id)

    if not media:
        return jsonify({'message': 'Media not found'}), 404

    # Check job ownership
    job = Job.query.get(media.job_id)
    if job.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    return jsonify({
        'id': media.id,
        'job_id': media.job_id,
        'original_filename': media.original_filename,
        'file_type': media.file_type,
        'file_size': media.file_size,
        'mime_type': media.mime_type,
        'width': media.width,
        'height': media.height,
        'duration': media.duration,
        'created_at': media.created_at.isoformat()
    }), 200


@media_bp.route('/<int:media_id>', methods=['DELETE'])
@AuthService.token_required
def delete_media(media_id):
    """Delete a specific media."""
    user = g.current_user

    # Find media
    media = Media.query.get(media_id)

    if not media:
        return jsonify({'message': 'Media not found'}), 404

    # Check job ownership
    job = Job.query.get(media.job_id)
    if job.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    # Delete the local file if it exists
    if media.local_path and os.path.exists(media.local_path):
        os.remove(media.local_path)

    # Delete from database (cascade to tasks and outputs)
    db.session.delete(media)
    db.session.commit()

    return jsonify({'message': 'Media deleted successfully'}), 200