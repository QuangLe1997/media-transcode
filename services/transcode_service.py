import os
import json
import uuid
import logging
import time
import shutil
from typing import Dict, List, Any, Tuple, Optional, Union
from datetime import datetime
from pathlib import Path

from services.ffmpeg_service import FFmpegService
from services.s3_service import S3Service
from database.models import (
    db, User, Config, Job, Media, TranscodeTask, TranscodeOutput
)

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

            # Create preview tasks if enabled
            if 'preview_settings' in config['video_settings']:
                preview_profiles = config['video_settings']['preview_settings'].get('use_profiles', [])
                for profile_name in preview_profiles:
                    # Find matching profile
                    profile = next((p for p in config['video_settings']['transcode_profiles']
                                    if p['name'] == profile_name), None)
                    if profile:
                        task = TranscodeTask(
                            media_id=media.id,
                            task_type='preview',
                            profile_name=profile_name,
                            status='pending'
                        )
                        tasks.append(task)

            # Create thumbnail tasks if enabled
            if 'thumbnail_settings' in config['video_settings']:
                for size in config['video_settings']['thumbnail_settings']['sizes']:
                    task = TranscodeTask(
                        media_id=media.id,
                        task_type='thumbnail',
                        profile_name=size['name'],
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

            # Execute transcode
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
        """Process a video preview task."""
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

            # Get profile and preview settings
            profile = next((p for p in config['video_settings']['transcode_profiles']
                            if p['name'] == task.profile_name), None)

            if not profile:
                raise ValueError(f"Profile {task.profile_name} not found in config")

            preview_settings = config['video_settings']['preview_settings']
            duration = preview_settings.get('duration_seconds', 30)

            # Create output filename
            filename, ext = os.path.splitext(os.path.basename(media.original_filename))
            output_filename = f"{filename}_{profile['name']}_preview.{profile['format']}"

            # Create output directory
            output_dir = os.path.join(self.temp_dir, f'job_{job.id}', f'media_{media.id}')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, output_filename)

            # Execute preview creation
            success = self.ffmpeg_service.create_video_preview(
                input_path=media.local_path,
                output_path=output_path,
                duration=duration,
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
                raise Exception("Preview creation failed")

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
            logger.error(f"Error processing video preview: {str(e)}")
            task.status = 'failed'
            task.error_message = str(e)
            db.session.commit()
            return False

    def process_video_thumbnail(self, task_id: int) -> bool:
        """Process a video thumbnail task."""
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
            size_profile = next((s for s in thumbnail_settings['sizes']
                                 if s['name'] == task.profile_name), None)

            if not size_profile:
                raise ValueError(f"Thumbnail size profile {task.profile_name} not found in config")

            timestamps = thumbnail_settings.get('timestamps', ['00:00:05'])
            format = thumbnail_settings.get('format', 'jpg')
            quality = thumbnail_settings.get('quality', 90)

            outputs = []

            # Create output directory
            output_dir = os.path.join(self.temp_dir, f'job_{job.id}', f'media_{media.id}')
            os.makedirs(output_dir, exist_ok=True)

            # Process each timestamp
            for ts in timestamps:
                # Create output filename
                filename, ext = os.path.splitext(os.path.basename(media.original_filename))
                ts_formatted = ts.replace(':', '_')
                output_filename = f"{filename}_{task.profile_name}_thumb_{ts_formatted}.{format}"
                output_path = os.path.join(output_dir, output_filename)

                # Execute thumbnail extraction
                success = self.ffmpeg_service.extract_video_thumbnail(
                    input_path=media.local_path,
                    output_path=output_path,
                    timestamp=ts,
                    width=size_profile['width'],
                    height=size_profile['height'],
                    format=format,
                    quality=quality
                )

                if not success:
                    raise Exception(f"Thumbnail extraction failed for timestamp {ts}")

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
                    width=size_profile['width'],
                    height=size_profile['height'],
                    format=format
                )
                db.session.add(output)
                outputs.append(output)

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

    def process_task(self, task_id: int) -> bool:
        """Process a transcode task based on its type."""
        task = TranscodeTask.query.get(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")

        media = Media.query.get(task.media_id)
        if not media:
            raise ValueError(f"Media with ID {task.media_id} not found")

        # Process based on media type and task type
        if media.file_type == 'video':
            if task.task_type == 'transcode':
                return self.process_video_transcode(task.id)
            elif task.task_type == 'preview':
                return self.process_video_preview(task.id)
            elif task.task_type == 'thumbnail':
                return self.process_video_thumbnail(task.id)
        elif media.file_type == 'image':
            if task.task_type == 'transcode':
                return self.process_image_transcode(task.id)
            elif task.task_type == 'thumbnail':
                return self.process_image_thumbnail(task.id)

        return False

    def process_all_tasks(self, job_id: int) -> Dict[str, int]:
        """Process all tasks for a job."""
        job = Job.query.get(job_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")

        # Get all media for this job
        media_list = Media.query.filter_by(job_id=job.id).all()

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
                if self.process_task(task.id):
                    results['success'] += 1
                else:
                    results['failed'] += 1

        # Update job status
        if results['failed'] == 0:
            job.status = 'completed'
        elif results['success'] == 0:
            job.status = 'failed'
        else:
            job.status = 'partial'

        job.updated_at = datetime.utcnow()
        db.session.commit()

        return results

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