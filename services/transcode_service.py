import json
import logging
import os
import shutil
from datetime import datetime
from typing import Dict, List

from database.models import (
    db, Config, Job, Media, TranscodeTask, TranscodeOutput
)
from services.face_detect_service import FaceProcessor
from services.ffmpeg_service import FFmpegService
from services.s3_service import S3Service

logger = logging.getLogger(__name__)


class TranscodeService:
    def __init__(self, ffmpeg_service: FFmpegService, s3_service: S3Service,
                 temp_dir: str = '/tmp/transcode-jobs/'):
        """Initialize the transcode service."""
        self.ffmpeg_service = ffmpeg_service
        self.s3_service = s3_service
        self.temp_dir = temp_dir

        # Ensure temp directory exists
        os.makedirs(self.temp_dir, exist_ok=True)

    def create_job(self, user_id: int, config_id: int) -> Job:
        """Create a new transcode job."""
        job = Job(
            user_id=user_id,
            config_id=config_id,
            status='pending'
        )
        db.session.add(job)
        db.session.commit()

        # Create job directory
        job_dir = os.path.join(self.temp_dir, f'job_{job.id}')
        os.makedirs(job_dir, exist_ok=True)

        return job

    def add_media_to_job(self, job_id: int, file_path: str, original_filename: str,
                         file_type: str, mime_type: str) -> Media:
        """Add a media file to a job."""
        # Get the job
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")

        # Get file size
        file_size = os.path.getsize(file_path)

        # Create media record
        media = Media(
            job_id=job_id,
            original_filename=original_filename,
            file_type=file_type,
            file_size=file_size,
            mime_type=mime_type,
            local_path=file_path
        )
        db.session.add(media)
        db.session.commit()

        # Get media info if it's an image or video
        try:
            info = self.ffmpeg_service.get_media_info(file_path)

            # Update media with metadata
            if file_type == 'video':
                media.duration = info.get('duration')

            media.width = info.get('width')
            media.height = info.get('height')

            db.session.commit()
        except Exception as e:
            logger.error(f"Error getting media info: {str(e)}")

        return media

    def get_job_config(self, job_id: int) -> Dict:
        """Get the configuration for a job."""
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")

        config = Config.query.get(job.config_id)
        if not config:
            raise ValueError(f"Config with ID {job.config_id} not found")

        try:
            return json.loads(config.config_json)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in config {config.id}")

    def create_transcode_tasks(self, media_id: int) -> List[TranscodeTask]:
        """Create transcode tasks for a media file based on job configuration."""
        media = Media.query.get(media_id)
        if not media:
            raise ValueError(f"Media with ID {media_id} not found")

        job = Job.query.get(media.job_id)
        if not job:
            raise ValueError(f"Job with ID {media.job_id} not found")

        # Get job configuration
        config = self.get_job_config(media.job_id)

        tasks = []

        # Process based on media type
        if media.file_type == 'video':
            # Create video transcode tasks
            for profile in config['video_settings']['transcode_profiles']:
                task = TranscodeTask(
                    media_id=media.id,
                    task_type='transcode',
                    profile_name=profile['name'],
                    status='pending'
                )
                tasks.append(task)

            # Create preview tasks if enabled (now GIF creation)
            if 'preview_settings' in config['video_settings']:
                for profile in config['video_settings']['preview_settings']['profiles']:
                    task = TranscodeTask(
                        media_id=media.id,
                        task_type='preview',
                        profile_name=profile['name'],
                        status='pending'
                    )
                    tasks.append(task)

            # Create thumbnail tasks if enabled
            if 'thumbnail_settings' in config['video_settings']:
                for profile in config['video_settings']['thumbnail_settings']['profiles']:
                    task = TranscodeTask(
                        media_id=media.id,
                        task_type='thumbnail',
                        profile_name=profile['name'],
                        status='pending'
                    )
                    tasks.append(task)

            # Create face detection task if enabled
            if config.get('face_detection', {}).get('enabled', False):
                task = TranscodeTask(
                    media_id=media.id,
                    task_type='face_detection',
                    profile_name='default',
                    status='pending'
                )
                tasks.append(task)

        elif media.file_type == 'image':
            # Create image transcode tasks
            for profile in config['image_settings']['transcode_profiles']:
                task = TranscodeTask(
                    media_id=media.id,
                    task_type='transcode',
                    profile_name=profile['name'],
                    status='pending'
                )
                tasks.append(task)

            # Create thumbnail tasks
            for profile in config['image_settings']['thumbnail_profiles']:
                task = TranscodeTask(
                    media_id=media.id,
                    task_type='thumbnail',
                    profile_name=profile['name'],
                    status='pending'
                )
                tasks.append(task)

            # Create face detection task if enabled
            if config.get('face_detection', {}).get('enabled', False):
                task = TranscodeTask(
                    media_id=media.id,
                    task_type='face_detection',
                    profile_name='default',
                    status='pending'
                )
                tasks.append(task)

        # Add tasks to database
        for task in tasks:
            db.session.add(task)

        db.session.commit()

        # Update job status
        job.status = 'processing'
        db.session.commit()

        return tasks

    def process_video_transcode(self, task_id: int) -> bool:
        """Process a video transcode task."""
        task = TranscodeTask.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")

        # Update task status
        task.status = 'processing'
        task.started_at = datetime.utcnow()
        db.session.commit()

        try:
            # Get required data
            media = Media.query.get(task.media_id)
            job = Job.query.get(media.job_id)
            config = self.get_job_config(job.id)

            # Get profile
            profile = next((p for p in config['video_settings']['transcode_profiles']
                            if p['name'] == task.profile_name), None)

            if not profile:
                raise ValueError(f"Profile {task.profile_name} not found in config")

            # Create output filename
            filename, ext = os.path.splitext(os.path.basename(media.original_filename))
            output_filename = f"{filename}_{profile['name']}.{profile['format']}"

            # Create output directory
            output_dir = os.path.join(self.temp_dir, f'job_{job.id}', f'media_{media.id}')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)

            # Check if we need to trim the video (new feature)
            start_time = profile.get('start')
            end_time = profile.get('end')

            # Execute transcode
            if start_time is not None and end_time is not None:
                # Trim and transcode the video
                success = self.ffmpeg_service.transcode_video_segment(
                    input_path=media.local_path,
                    output_path=output_path,
                    start_time=start_time,
                    end_time=end_time,
                    width=profile['width'],
                    height=profile['height'],
                    codec=profile['codec'],
                    preset=profile['preset'],
                    crf=profile['crf'],
                    format=profile['format'],
                    audio_codec=profile['audio_codec'],
                    audio_bitrate=profile['audio_bitrate'],
                    use_gpu=profile.get('use_gpu', True)
                )
            else:
                # Regular transcode (full video)
                success = self.ffmpeg_service.transcode_video(
                    input_path=media.local_path,
                    output_path=output_path,
                    width=profile['width'],
                    height=profile['height'],
                    codec=profile['codec'],
                    preset=profile['preset'],
                    crf=profile['crf'],
                    format=profile['format'],
                    audio_codec=profile['audio_codec'],
                    audio_bitrate=profile['audio_bitrate'],
                    use_gpu=profile.get('use_gpu', True)
                )

            if not success:
                raise Exception("Transcode failed")

            # Upload to S3
            folder_structure = config['output_settings']['folder_structure']
            s3_key = folder_structure.format(
                user_id=job.user_id,
                job_id=job.id,
                type='video',
                profile_name=profile['name']
            )
            s3_key = os.path.join(s3_key, output_filename)

            success, url = self.s3_service.upload_file(
                file_path=output_path,
                s3_key=s3_key,
                public=True
            )

            if not success:
                raise Exception(f"S3 upload failed: {url}")

            # Get output file metadata
            output_info = self.ffmpeg_service.get_media_info(output_path)

            # Create output record
            output = TranscodeOutput(
                task_id=task.id,
                output_filename=output_filename,
                s3_url=url,
                local_path=output_path,
                file_size=os.path.getsize(output_path),
                width=output_info.get('width'),
                height=output_info.get('height'),
                duration=output_info.get('duration'),
                format=profile['format']
            )
            db.session.add(output)

            # Update task status
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Error processing video transcode: {str(e)}")
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            return False

    def process_video_preview(self, task_id: int) -> bool:
        """Process a video preview task (now creates GIF instead of video)."""
        task = TranscodeTask.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")

        # Update task status
        task.status = 'processing'
        task.started_at = datetime.utcnow()
        db.session.commit()

        try:
            # Get required data
            media = Media.query.get(task.media_id)
            job = Job.query.get(media.job_id)
            config = self.get_job_config(job.id)

            # Get profile from the preview settings
            preview_settings = config['video_settings']['preview_settings']
            profile = next((p for p in preview_settings['profiles']
                            if p['name'] == task.profile_name), None)

            if not profile:
                raise ValueError(f"Preview profile {task.profile_name} not found in config")

            # Extract parameters for GIF creation
            start = profile.get('start', 0)
            end = profile.get('end', 5)  # Default is 0-5 seconds
            fps = profile.get('fps', 10)
            width = profile.get('width', 320)
            height = profile.get('height', 180)
            quality = profile.get('quality', 75)

            # Create output filename
            filename, ext = os.path.splitext(os.path.basename(media.original_filename))
            output_filename = f"{filename}_{profile['name']}_preview.gif"

            # Create output directory
            output_dir = os.path.join(self.temp_dir, f'job_{job.id}', f'media_{media.id}')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)

            # Execute GIF creation
            success = self.ffmpeg_service.create_gif_from_video(
                input_path=media.local_path,
                output_path=output_path,
                start=start,
                end=end,
                fps=fps,
                width=width,
                height=height,
                quality=quality
            )

            if not success:
                raise Exception("GIF creation failed")

            # Upload to S3
            folder_structure = config['output_settings']['folder_structure']
            s3_key = folder_structure.format(
                user_id=job.user_id,
                job_id=job.id,
                type='preview',
                profile_name=profile['name']
            )
            s3_key = os.path.join(s3_key, output_filename)

            success, url = self.s3_service.upload_file(
                file_path=output_path,
                s3_key=s3_key,
                public=True
            )

            if not success:
                raise Exception(f"S3 upload failed: {url}")

            # Create output record
            output = TranscodeOutput(
                task_id=task.id,
                output_filename=output_filename,
                s3_url=url,
                local_path=output_path,
                file_size=os.path.getsize(output_path),
                width=width,
                height=height,
                duration=end - start,
                format='gif'
            )
            db.session.add(output)

            # Update task status
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Error processing video preview (GIF): {str(e)}")
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            return False

    def process_video_thumbnail(self, task_id: int) -> bool:
        """Process a video thumbnail task (modified to take one frame)."""
        task = TranscodeTask.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")

        # Update task status
        task.status = 'processing'
        task.started_at = datetime.utcnow()
        db.session.commit()

        try:
            # Get required data
            media = Media.query.get(task.media_id)
            job = Job.query.get(media.job_id)
            config = self.get_job_config(job.id)

            # Get thumbnail settings
            thumbnail_settings = config['video_settings']['thumbnail_settings']
            profile = next((s for s in thumbnail_settings['profiles']
                            if s['name'] == task.profile_name), None)

            if not profile:
                raise ValueError(f"Thumbnail profile {task.profile_name} not found in config")

            # Get timestamp to extract frame
            timestamp = thumbnail_settings.get('timestamp')
            # If timestamp is not specified, choose a frame from the middle or use a default
            if timestamp is None:
                if media.duration and media.duration > 0:
                    # Take frame from middle of video
                    timestamp_seconds = media.duration / 2
                else:
                    # Default to 5 seconds if duration is unknown
                    timestamp_seconds = 5
            else:
                timestamp_seconds = timestamp

            # Format timestamp for ffmpeg
            timestamp_str = self._format_timestamp(timestamp_seconds)

            # Get output format and quality
            format = profile.get('format', 'jpg')
            quality = profile.get('quality', 90)

            # Create output filename
            filename, ext = os.path.splitext(os.path.basename(media.original_filename))
            output_filename = f"{filename}_{task.profile_name}_thumb.{format}"

            # Create output directory
            output_dir = os.path.join(self.temp_dir, f'job_{job.id}', f'media_{media.id}')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)

            # Execute thumbnail extraction
            success = self.ffmpeg_service.extract_video_thumbnail(
                input_path=media.local_path,
                output_path=output_path,
                timestamp=timestamp_str,
                width=profile['width'],
                height=profile['height'],
                format=format,
                quality=quality
            )

            if not success:
                raise Exception(f"Thumbnail extraction failed for timestamp {timestamp_str}")

            # Upload to S3
            folder_structure = config['output_settings']['folder_structure']
            s3_key = folder_structure.format(
                user_id=job.user_id,
                job_id=job.id,
                type='thumbnail',
                profile_name=task.profile_name
            )
            s3_key = os.path.join(s3_key, output_filename)

            success, url = self.s3_service.upload_file(
                file_path=output_path,
                s3_key=s3_key,
                public=True
            )

            if not success:
                raise Exception(f"S3 upload failed: {url}")

            # Create output record
            output = TranscodeOutput(
                task_id=task.id,
                output_filename=output_filename,
                s3_url=url,
                local_path=output_path,
                file_size=os.path.getsize(output_path),
                width=profile['width'],
                height=profile['height'],
                format=format
            )
            db.session.add(output)

            # Update task status
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Error processing video thumbnail: {str(e)}")
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            return False

    def process_image_transcode(self, task_id: int) -> bool:
        """Process an image transcode task."""
        task = TranscodeTask.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")

        # Update task status
        task.status = 'processing'
        task.started_at = datetime.utcnow()
        db.session.commit()

        try:
            # Get required data
            media = Media.query.get(task.media_id)
            job = Job.query.get(media.job_id)
            config = self.get_job_config(job.id)

            # Get profile
            profile = next((p for p in config['image_settings']['transcode_profiles']
                            if p['name'] == task.profile_name), None)

            if not profile:
                raise ValueError(f"Profile {task.profile_name} not found in config")

            # Create output filename
            filename, ext = os.path.splitext(os.path.basename(media.original_filename))
            output_filename = f"{filename}_{profile['name']}.{profile['format']}"

            # Create output directory
            output_dir = os.path.join(self.temp_dir, f'job_{job.id}', f'media_{media.id}')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)

            # Execute transcode
            success = self.ffmpeg_service.transcode_image(
                input_path=media.local_path,
                output_path=output_path,
                resize=profile.get('resize', False),
                width=media.width,  # Keep original dimensions if resize is False
                height=media.height,
                format=profile['format'],
                quality=profile['quality']
            )

            if not success:
                raise Exception("Image transcode failed")

            # Upload to S3
            folder_structure = config['output_settings']['folder_structure']
            s3_key = folder_structure.format(
                user_id=job.user_id,
                job_id=job.id,
                type='image',
                profile_name=profile['name']
            )
            s3_key = os.path.join(s3_key, output_filename)

            success, url = self.s3_service.upload_file(
                file_path=output_path,
                s3_key=s3_key,
                public=True
            )

            if not success:
                raise Exception(f"S3 upload failed: {url}")

            # Create output record
            output = TranscodeOutput(
                task_id=task.id,
                output_filename=output_filename,
                s3_url=url,
                local_path=output_path,
                file_size=os.path.getsize(output_path),
                width=media.width,
                height=media.height,
                format=profile['format']
            )
            db.session.add(output)

            # Update task status
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Error processing image transcode: {str(e)}")
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            return False

    def process_image_thumbnail(self, task_id: int) -> bool:
        """Process an image thumbnail task."""
        task = TranscodeTask.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")

        # Update task status
        task.status = 'processing'
        task.started_at = datetime.utcnow()
        db.session.commit()

        try:
            # Get required data
            media = Media.query.get(task.media_id)
            job = Job.query.get(media.job_id)
            config = self.get_job_config(job.id)

            # Get profile
            profile = next((p for p in config['image_settings']['thumbnail_profiles']
                            if p['name'] == task.profile_name), None)

            if not profile:
                raise ValueError(f"Thumbnail profile {task.profile_name} not found in config")

            # Create output filename
            filename, ext = os.path.splitext(os.path.basename(media.original_filename))
            output_filename = f"{filename}_{profile['name']}_thumb.{profile['format']}"

            # Create output directory
            output_dir = os.path.join(self.temp_dir, f'job_{job.id}', f'media_{media.id}')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)

            # Execute thumbnail creation
            success = self.ffmpeg_service.transcode_image(
                input_path=media.local_path,
                output_path=output_path,
                resize=True,
                width=profile['width'],
                height=profile['height'],
                maintain_aspect_ratio=profile.get('maintain_aspect_ratio', True),
                format=profile['format'],
                quality=profile['quality']
            )

            if not success:
                raise Exception("Image thumbnail creation failed")

            # Upload to S3
            folder_structure = config['output_settings']['folder_structure']
            s3_key = folder_structure.format(
                user_id=job.user_id,
                job_id=job.id,
                type='thumbnail',
                profile_name=profile['name']
            )
            s3_key = os.path.join(s3_key, output_filename)

            success, url = self.s3_service.upload_file(
                file_path=output_path,
                s3_key=s3_key,
                public=True
            )

            if not success:
                raise Exception(f"S3 upload failed: {url}")

            # Create output record
            output = TranscodeOutput(
                task_id=task.id,
                output_filename=output_filename,
                s3_url=url,
                local_path=output_path,
                file_size=os.path.getsize(output_path),
                width=profile['width'],
                height=profile['height'],
                format=profile['format']
            )
            db.session.add(output)

            # Update task status
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Error processing image thumbnail: {str(e)}")
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            return False

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to ffmpeg timestamp format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

    def process_face_detection(self, task_id: int) -> bool:
        """Process face detection task for video or image."""
        task = TranscodeTask.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")

        # Update task status
        task.status = 'processing'
        task.started_at = datetime.utcnow()
        db.session.commit()

        try:
            # Get required data
            media = Media.query.get(task.media_id)
            job = Job.query.get(media.job_id)
            config = self.get_job_config(job.id)

            # Get face detection configuration
            face_config = config.get('face_detection', {}).get('config', {})

            # Create face processor with provided configuration
            face_processor = FaceProcessor(face_config)

            # Create output directory
            output_dir = os.path.join(self.temp_dir, f'job_{job.id}', f'media_{media.id}', 'faces')
            os.makedirs(output_dir, exist_ok=True)

            # Set custom output path in face processor config
            face_processor.output_path = output_dir

            # Process media based on its type
            if media.file_type == 'video':
                result = face_processor.process_video(media.local_path)
            else:  # image
                result = face_processor.process_image(media.local_path)

            # Save results as JSON file
            result_file = os.path.join(output_dir, 'faces_result.json')
            with open(result_file, 'w') as f:
                json.dump(result, f, cls=face_processor.__class__.__module__.NumpyJSONEncoder)

            # Upload results to S3
            folder_structure = config['output_settings']['folder_structure']
            base_s3_key = folder_structure.format(
                user_id=job.user_id,
                job_id=job.id,
                type='faces',
                profile_name=task.profile_name
            )

            # Upload JSON result file
            result_filename = f"{os.path.splitext(media.original_filename)[0]}_faces_result.json"
            result_s3_key = os.path.join(base_s3_key, result_filename)

            success, url = self.s3_service.upload_file(
                file_path=result_file,
                s3_key=result_s3_key,
                public=True
            )

            if not success:
                raise Exception(f"S3 upload of result file failed: {url}")

            # Create output record for the result JSON
            output = TranscodeOutput(
                task_id=task.id,
                output_filename=result_filename,
                s3_url=url,
                local_path=result_file,
                file_size=os.path.getsize(result_file),
                format='json'
            )
            db.session.add(output)

            # Upload face avatars if any faces were detected
            for i, face in enumerate(result.get('faces', [])):
                if 'avatar' in face:
                    # The avatar is already in base64 format in the result
                    # We need to create a file for it to upload to S3

                    # Get face data
                    face_name = face.get('name', f"face_{i}")
                    avatar_file = os.path.join(output_dir, f"{face_name}.jpg")

                    # Save base64 content to file
                    import base64
                    img_data = base64.b64decode(face['avatar'])
                    with open(avatar_file, 'wb') as f:
                        f.write(img_data)

                    # Upload to S3
                    avatar_s3_key = os.path.join(base_s3_key, f"{face_name}.jpg")
                    success, avatar_url = self.s3_service.upload_file(
                        file_path=avatar_file,
                        s3_key=avatar_s3_key,
                        public=True
                    )

                    if not success:
                        logger.warning(f"Failed to upload face avatar {i}: {avatar_url}")
                        continue

                    # Create output record for each face avatar
                    avatar_output = TranscodeOutput(
                        task_id=task.id,
                        output_filename=f"{face_name}.jpg",
                        s3_url=avatar_url,
                        local_path=avatar_file,
                        file_size=os.path.getsize(avatar_file),
                        format='jpg'
                    )
                    db.session.add(avatar_output)

            # Commit all avatar outputs to database
            db.session.commit()

            # Update task status
            task.status = 'completed'
            task.completed_at = datetime.utcnow()
            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Error processing face detection: {str(e)}")
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            return False

    def cleanup_job(self, job_id: int, delete_local: bool = True) -> bool:
        """Clean up temporary files for a job."""
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")

        if not delete_local:
            return True

        try:
            job_dir = os.path.join(self.temp_dir, f'job_{job.id}')
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir)

            return True
        except Exception as e:
            logger.error(f"Error cleaning up job: {str(e)}")
            return False
