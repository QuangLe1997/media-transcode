import json
from datetime import datetime

from flask import Blueprint, request, jsonify, g

from database.models import db, Config
from services.auth_service import AuthService

configs_bp = Blueprint('configs', __name__)


@configs_bp.route('/', methods=['GET'])
@AuthService.token_required
def get_configs():
    """Get all configs for the current user."""
    user = g.current_user

    # Get user-specific configs and public configs
    configs = Config.query.filter(
        (Config.user_id == user.id) | (Config.user_id == None)
    ).all()

    return jsonify({
        'configs': [{
            'id': config.id,
            'name': config.name,
            'description': config.description,
            'is_default': config.is_default,
            'created_at': config.created_at.isoformat(),
            'updated_at': config.updated_at.isoformat(),
            'is_public': config.user_id is None
        } for config in configs]
    }), 200


@configs_bp.route('/<int:config_id>', methods=['GET'])
@AuthService.token_required
def get_config(config_id):
    """Get a specific config."""
    user = g.current_user

    # Find config
    config = Config.query.get(config_id)

    if not config:
        return jsonify({'message': 'Config not found'}), 404

    # Check access (user owns the config or it's public)
    if config.user_id is not None and config.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    return jsonify({
        'id': config.id,
        'name': config.name,
        'description': config.description,
        'config_json': json.loads(config.config_json),
        'is_default': config.is_default,
        'created_at': config.created_at.isoformat(),
        'updated_at': config.updated_at.isoformat(),
        'is_public': config.user_id is None
    }), 200


@configs_bp.route('/', methods=['POST'])
@AuthService.token_required
def create_config():
    """Create a new config."""
    user = g.current_user
    data = request.get_json()

    # Validate required fields
    if not data or not data.get('name') or not data.get('config_json'):
        return jsonify({'message': 'Missing required fields'}), 400

    # Validate JSON
    try:
        config_json = data['config_json']
        if isinstance(config_json, dict):
            config_json = json.dumps(config_json)
        else:
            # Validate that it's valid JSON if it's a string
            json.loads(config_json)
    except (TypeError, json.JSONDecodeError):
        return jsonify({'message': 'Invalid JSON configuration'}), 400

    # Create config
    config = Config(
        name=data['name'],
        description=data.get('description', ''),
        config_json=config_json,
        user_id=user.id,
        is_default=data.get('is_default', False)
    )

    # If this is the default, unset other defaults
    if config.is_default:
        Config.query.filter_by(user_id=user.id, is_default=True).update({'is_default': False})

    # Add to database
    db.session.add(config)
    db.session.commit()

    return jsonify({
        'message': 'Config created successfully',
        'id': config.id
    }), 201


@configs_bp.route('/<int:config_id>', methods=['PUT'])
@AuthService.token_required
def update_config(config_id):
    """Update a specific config."""
    user = g.current_user
    data = request.get_json()

    # Find config
    config = Config.query.get(config_id)

    if not config:
        return jsonify({'message': 'Config not found'}), 404

    # Check ownership
    if config.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    # Update fields
    if 'name' in data:
        config.name = data['name']

    if 'description' in data:
        config.description = data['description']

    if 'config_json' in data:
        try:
            config_json = data['config_json']
            if isinstance(config_json, dict):
                config_json = json.dumps(config_json)
            else:
                # Validate that it's valid JSON if it's a string
                json.loads(config_json)
            config.config_json = config_json
        except (TypeError, json.JSONDecodeError):
            return jsonify({'message': 'Invalid JSON configuration'}), 400

    if 'is_default' in data and data['is_default']:
        # Unset other defaults
        Config.query.filter_by(user_id=user.id, is_default=True).update({'is_default': False})
        config.is_default = True

    # Save changes
    db.session.commit()

    return jsonify({'message': 'Config updated successfully'}), 200


@configs_bp.route('/<int:config_id>', methods=['DELETE'])
@AuthService.token_required
def delete_config(config_id):
    """Delete a specific config."""
    user = g.current_user

    # Find config
    config = Config.query.get(config_id)

    if not config:
        return jsonify({'message': 'Config not found'}), 404

    # Check ownership
    if config.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    # Check if config has associated jobs
    from database.models import Job
    jobs_count = Job.query.filter_by(config_id=config_id).count()

    # Delete from database (jobs.config_id will be set to NULL automatically)
    db.session.delete(config)
    db.session.commit()

    message = 'Config deleted successfully'
    if jobs_count > 0:
        message += f'. {jobs_count} job(s) were unlinked from this configuration.'

    return jsonify({
        'message': message,
        'affected_jobs': jobs_count
    }), 200


@configs_bp.route('/default', methods=['GET'])
@AuthService.token_required
def get_default_config():
    """Get the default config for the current user."""
    user = g.current_user

    # Try to find user's default
    config = Config.query.filter_by(user_id=user.id, is_default=True).first()

    # If no user default, try system default
    if not config:
        config = Config.query.filter_by(user_id=None, is_default=True).first()

    if not config:
        return jsonify({'message': 'No default config found'}), 404

    return jsonify({
        'id': config.id,
        'name': config.name,
        'description': config.description,
        'config_json': json.loads(config.config_json),
        'is_default': config.is_default,
        'created_at': config.created_at.isoformat(),
        'updated_at': config.updated_at.isoformat(),
        'is_public': config.user_id is None
    }), 200


@configs_bp.route('/templates', methods=['GET'])
def get_config_templates():
    """Get predefined config templates."""
    from datetime import datetime

    base_template = {
        "_schema_version": "1.0",
        "_config_type": "media_transcode_profile",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "tags": [],
        "face_detection": {
            "enabled": False,
            "config": {
                "model_version": "v2.0",
                "similarity_threshold": 0.7,
                "output_path": "./output/faces"
            }
        },
        "output_settings": {
            "storage": {
                "s3_bucket": "",
                "s3_region": "us-east-1",
                "folder_structure": "{user_id}/{job_id}/{type}/{profile_name}/",
                "generate_unique_filenames": True,
                "preserve_original_filename": True,
                "filename_template": "{timestamp}_{profile}_{original_name}",
                "use_temporary_local_storage": True,
                "local_storage_path": "/tmp/transcode-jobs/",
                "delete_local_after_upload": True
            },
            "notifications": {
                "webhook_url": "",
                "email_notifications": [],
                "include_processing_stats": True
            }
        }
    }

    templates = [
        {
            'id': 'standard',
            'name': 'Standard Transcoding',
            'description': 'Balanced quality and file size for most use cases',
            'config': {
                **base_template,
                'config_name': 'Standard Transcoding',
                'description': 'Balanced quality and file size for most use cases',
                'video_settings': {
                    '_enabled': True,
                    'transcode_profiles': [{
                        '_id': '',
                        'name': '720p_standard',
                        'description': 'Standard 720p profile',
                        'enabled': True,
                        'width': 1280,
                        'height': 720,
                        'codec': 'libx264',
                        'preset': 'medium',
                        'crf': 23,
                        'format': 'mp4',
                        'audio_codec': 'aac',
                        'audio_bitrate': '128k',
                        'audio_channels': 2,
                        'use_gpu': True
                    }],
                    'preview_settings': {
                        '_enabled': True,
                        'profiles': [{
                            '_id': '',
                            'name': 'standard_preview',
                            'enabled': True,
                            'start': 0,
                            'end': 5,
                            'fps': 12,
                            'width': 640,
                            'height': 360,
                            'quality': 80,
                            'format': 'gif'
                        }]
                    },
                    'thumbnail_settings': {
                        '_enabled': True,
                        'timestamp': 5,
                        'profiles': [{
                            '_id': '',
                            'name': 'standard_thumb',
                            'enabled': True,
                            'width': 640,
                            'height': 360,
                            'format': 'jpg',
                            'quality': 90
                        }]
                    }
                },
                'image_settings': {
                    '_enabled': True,
                    'transcode_profiles': [{
                        '_id': '',
                        'name': 'webp_standard',
                        'enabled': True,
                        'format': 'webp',
                        'quality': 85,
                        'compression_level': 6,
                        'optimize': True
                    }],
                    'thumbnail_profiles': [{
                        '_id': '',
                        'name': 'image_thumb',
                        'enabled': True,
                        'width': 320,
                        'height': 240,
                        'format': 'webp',
                        'quality': 85
                    }]
                }
            }
        },
        {
            'id': 'high-quality',
            'name': 'High Quality',
            'description': 'Maximum quality with larger file sizes',
            'config': {
                **base_template,
                'config_name': 'High Quality',
                'description': 'Maximum quality with larger file sizes',
                'video_settings': {
                    '_enabled': True,
                    'transcode_profiles': [{
                        '_id': '',
                        'name': '1080p_high',
                        'description': 'High quality 1080p profile',
                        'enabled': True,
                        'width': 1920,
                        'height': 1080,
                        'codec': 'libx265',
                        'preset': 'slow',
                        'crf': 18,
                        'format': 'mp4',
                        'audio_codec': 'aac',
                        'audio_bitrate': '192k',
                        'audio_channels': 2,
                        'use_gpu': True
                    }],
                    'preview_settings': {
                        '_enabled': True,
                        'profiles': [{
                            '_id': '',
                            'name': 'hq_preview',
                            'enabled': True,
                            'start': 0,
                            'end': 5,
                            'fps': 15,
                            'width': 800,
                            'height': 450,
                            'quality': 90,
                            'format': 'gif'
                        }]
                    },
                    'thumbnail_settings': {
                        '_enabled': True,
                        'timestamp': 5,
                        'profiles': [{
                            '_id': '',
                            'name': 'hq_thumb',
                            'enabled': True,
                            'width': 1280,
                            'height': 720,
                            'format': 'jpg',
                            'quality': 95
                        }]
                    }
                },
                'image_settings': {
                    '_enabled': True,
                    'transcode_profiles': [{
                        '_id': '',
                        'name': 'png_high',
                        'enabled': True,
                        'format': 'png',
                        'quality': 100,
                        'optimize': True
                    }],
                    'thumbnail_profiles': [{
                        '_id': '',
                        'name': 'image_hq_thumb',
                        'enabled': True,
                        'width': 640,
                        'height': 480,
                        'format': 'png',
                        'quality': 95
                    }]
                }
            }
        },
        {
            'id': 'web-optimized',
            'name': 'Web Optimized',
            'description': 'Optimized for web streaming and fast loading',
            'config': {
                **base_template,
                'config_name': 'Web Optimized',
                'description': 'Optimized for web streaming and fast loading',
                'video_settings': {
                    '_enabled': True,
                    'transcode_profiles': [{
                        '_id': '',
                        'name': '720p_web',
                        'description': 'Web optimized 720p profile',
                        'enabled': True,
                        'width': 1280,
                        'height': 720,
                        'codec': 'libx264',
                        'preset': 'fast',
                        'crf': 28,
                        'format': 'mp4',
                        'audio_codec': 'aac',
                        'audio_bitrate': '96k',
                        'audio_channels': 2,
                        'use_gpu': True
                    }],
                    'preview_settings': {
                        '_enabled': True,
                        'profiles': [{
                            '_id': '',
                            'name': 'web_preview',
                            'enabled': True,
                            'start': 0,
                            'end': 3,
                            'fps': 10,
                            'width': 480,
                            'height': 270,
                            'quality': 75,
                            'format': 'gif'
                        }]
                    },
                    'thumbnail_settings': {
                        '_enabled': True,
                        'timestamp': 3,
                        'profiles': [{
                            '_id': '',
                            'name': 'web_thumb',
                            'enabled': True,
                            'width': 480,
                            'height': 270,
                            'format': 'webp',
                            'quality': 80
                        }]
                    }
                },
                'image_settings': {
                    '_enabled': True,
                    'transcode_profiles': [{
                        '_id': '',
                        'name': 'webp_optimized',
                        'enabled': True,
                        'format': 'webp',
                        'quality': 80,
                        'compression_level': 4,
                        'optimize': True
                    }],
                    'thumbnail_profiles': [{
                        '_id': '',
                        'name': 'web_image_thumb',
                        'enabled': True,
                        'width': 240,
                        'height': 180,
                        'format': 'webp',
                        'quality': 75
                    }]
                }
            }
        },
        {
            'id': 'mobile',
            'name': 'Mobile Optimized',
            'description': 'Optimized for mobile devices with limited bandwidth',
            'config': {
                **base_template,
                'config_name': 'Mobile Optimized',
                'description': 'Optimized for mobile devices with limited bandwidth',
                'video_settings': {
                    '_enabled': True,
                    'transcode_profiles': [{
                        '_id': '',
                        'name': '480p_mobile',
                        'description': 'Mobile optimized 480p profile',
                        'enabled': True,
                        'width': 854,
                        'height': 480,
                        'codec': 'libx264',
                        'preset': 'faster',
                        'crf': 30,
                        'format': 'mp4',
                        'audio_codec': 'aac',
                        'audio_bitrate': '64k',
                        'audio_channels': 2,
                        'use_gpu': True
                    }],
                    'preview_settings': {
                        '_enabled': True,
                        'profiles': [{
                            '_id': '',
                            'name': 'mobile_preview',
                            'enabled': True,
                            'start': 0,
                            'end': 3,
                            'fps': 8,
                            'width': 320,
                            'height': 180,
                            'quality': 70,
                            'format': 'gif'
                        }]
                    },
                    'thumbnail_settings': {
                        '_enabled': True,
                        'timestamp': 2,
                        'profiles': [{
                            '_id': '',
                            'name': 'mobile_thumb',
                            'enabled': True,
                            'width': 320,
                            'height': 180,
                            'format': 'jpg',
                            'quality': 75
                        }]
                    }
                },
                'image_settings': {
                    '_enabled': True,
                    'transcode_profiles': [{
                        '_id': '',
                        'name': 'jpg_mobile',
                        'enabled': True,
                        'format': 'jpg',
                        'quality': 75,
                        'optimize': True,
                        'resize': True,
                        'width': 1080
                    }],
                    'thumbnail_profiles': [{
                        '_id': '',
                        'name': 'mobile_image_thumb',
                        'enabled': True,
                        'width': 160,
                        'height': 120,
                        'format': 'jpg',
                        'quality': 70
                    }]
                }
            }
        }
    ]

    return jsonify({'templates': templates}), 200


@configs_bp.route('/duplicate/<int:config_id>', methods=['POST'])
@AuthService.token_required
def duplicate_config(config_id):
    """Duplicate an existing config."""
    user = g.current_user
    data = request.get_json()

    # Find original config
    original_config = Config.query.get(config_id)

    if not original_config:
        return jsonify({'message': 'Config not found'}), 404

    # Check access (user owns the config or it's public)
    if original_config.user_id is not None and original_config.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    # Create duplicate
    new_name = data.get('name', f"{original_config.name} (Copy)")

    duplicate = Config(
        name=new_name,
        description=data.get('description', original_config.description),
        config_json=original_config.config_json,
        user_id=user.id,
        is_default=False
    )

    db.session.add(duplicate)
    db.session.commit()

    return jsonify({
        'message': 'Config duplicated successfully',
        'id': duplicate.id
    }), 201


@configs_bp.route('/validate', methods=['POST'])
def validate_config():
    """Validate a config JSON structure."""
    data = request.get_json()

    if not data or not data.get('config_json'):
        return jsonify({'message': 'Missing config JSON'}), 400

    config_json = data['config_json']

    # Required fields for new config structure
    required_fields = ['config_name', 'video_settings', 'image_settings']
    errors = []
    warnings = []

    # Check required fields
    for field in required_fields:
        if field not in config_json:
            errors.append(f"Missing required field: {field}")

    # Validate basic info
    if 'config_name' in config_json and not config_json['config_name'].strip():
        errors.append("Configuration name cannot be empty")

    # Validate video settings
    if 'video_settings' in config_json:
        video_settings = config_json['video_settings']

        # Check if enabled and has profiles
        if video_settings.get('_enabled', True):
            if 'transcode_profiles' not in video_settings:
                errors.append("Video settings missing 'transcode_profiles'")
            elif not isinstance(video_settings['transcode_profiles'], list):
                errors.append("Video transcode_profiles must be an array")
            elif len(video_settings['transcode_profiles']) == 0:
                warnings.append("No video transcode profiles configured")
            else:
                # Validate each video profile
                for i, profile in enumerate(video_settings['transcode_profiles']):
                    profile_errors = validate_video_profile(profile, i)
                    errors.extend(profile_errors)

        # Validate preview settings if present
        if 'preview_settings' in video_settings and video_settings['preview_settings'].get('_enabled'):
            preview_profiles = video_settings['preview_settings'].get('profiles', [])
            for i, profile in enumerate(preview_profiles):
                profile_errors = validate_preview_profile(profile, i)
                errors.extend(profile_errors)

        # Validate thumbnail settings if present
        if 'thumbnail_settings' in video_settings and video_settings['thumbnail_settings'].get('_enabled'):
            thumb_profiles = video_settings['thumbnail_settings'].get('profiles', [])
            for i, profile in enumerate(thumb_profiles):
                profile_errors = validate_thumbnail_profile(profile, i, 'video')
                errors.extend(profile_errors)

    # Validate image settings
    if 'image_settings' in config_json:
        image_settings = config_json['image_settings']

        # Check if enabled and has profiles
        if image_settings.get('_enabled', True):
            if 'transcode_profiles' not in image_settings:
                errors.append("Image settings missing 'transcode_profiles'")
            elif not isinstance(image_settings['transcode_profiles'], list):
                errors.append("Image transcode_profiles must be an array")
            elif len(image_settings['transcode_profiles']) == 0:
                warnings.append("No image transcode profiles configured")
            else:
                # Validate each image profile
                for i, profile in enumerate(image_settings['transcode_profiles']):
                    profile_errors = validate_image_profile(profile, i)
                    errors.extend(profile_errors)

            # Validate thumbnail profiles if present
            if 'thumbnail_profiles' in image_settings:
                for i, profile in enumerate(image_settings['thumbnail_profiles']):
                    profile_errors = validate_thumbnail_profile(profile, i, 'image')
                    errors.extend(profile_errors)

    # Validate face detection settings if enabled
    if config_json.get('face_detection', {}).get('enabled', False):
        face_config = config_json['face_detection'].get('config', {})
        if not face_config:
            errors.append("Face detection enabled but no configuration provided")

    # Validate output settings
    if 'output_settings' in config_json:
        output_settings = config_json['output_settings']
        if 'storage' in output_settings:
            storage = output_settings['storage']
            if 'folder_structure' not in storage:
                warnings.append("No folder structure specified in storage settings")

    if errors:
        return jsonify({
            'valid': False,
            'errors': errors,
            'warnings': warnings
        }), 400

    return jsonify({
        'valid': True,
        'message': 'Config is valid',
        'warnings': warnings
    }), 200


def validate_video_profile(profile, index):
    """Validate a video transcode profile."""
    errors = []
    required_fields = ['name', 'width', 'height', 'codec', 'format']

    for field in required_fields:
        if field not in profile or not profile[field]:
            errors.append(f"Video profile {index + 1}: Missing required field '{field}'")

    # Validate dimensions
    if 'width' in profile and profile['width'] and (profile['width'] < 64 or profile['width'] > 7680):
        errors.append(f"Video profile {index + 1}: Width must be between 64 and 7680")

    if 'height' in profile and profile['height'] and (profile['height'] < 64 or profile['height'] > 4320):
        errors.append(f"Video profile {index + 1}: Height must be between 64 and 4320")

    # Validate CRF if present
    if 'crf' in profile and profile['crf'] is not None:
        try:
            crf = int(profile['crf'])
            if crf < 0 or crf > 51:
                errors.append(f"Video profile {index + 1}: CRF must be between 0 and 51")
        except (ValueError, TypeError):
            errors.append(f"Video profile {index + 1}: CRF must be a valid number")

    # Validate codec
    valid_codecs = ['libx264', 'libx265', 'libvpx-vp9', 'h264_nvenc', 'hevc_nvenc']
    if 'codec' in profile and profile['codec'] not in valid_codecs:
        errors.append(f"Video profile {index + 1}: Invalid codec '{profile['codec']}'")

    # Validate format
    valid_formats = ['mp4', 'webm', 'mov', 'mkv']
    if 'format' in profile and profile['format'] not in valid_formats:
        errors.append(f"Video profile {index + 1}: Invalid format '{profile['format']}'")

    return errors


def validate_image_profile(profile, index):
    """Validate an image transcode profile."""
    errors = []
    required_fields = ['name', 'format', 'quality']

    for field in required_fields:
        if field not in profile or profile[field] is None:
            errors.append(f"Image profile {index + 1}: Missing required field '{field}'")

    # Validate quality
    if 'quality' in profile and profile['quality'] is not None:
        try:
            quality = int(profile['quality'])
            if quality < 1 or quality > 100:
                errors.append(f"Image profile {index + 1}: Quality must be between 1 and 100")
        except (ValueError, TypeError):
            errors.append(f"Image profile {index + 1}: Quality must be a valid number")

    # Validate format
    valid_formats = ['webp', 'avif', 'jpg', 'png']
    if 'format' in profile and profile['format'] not in valid_formats:
        errors.append(f"Image profile {index + 1}: Invalid format '{profile['format']}'")

    # Validate dimensions if resize is enabled
    if profile.get('resize', False):
        if 'width' in profile and profile['width'] and profile['width'] < 1:
            errors.append(f"Image profile {index + 1}: Width must be greater than 0")
        if 'height' in profile and profile['height'] and profile['height'] < 1:
            errors.append(f"Image profile {index + 1}: Height must be greater than 0")

    return errors


def validate_preview_profile(profile, index):
    """Validate a preview/GIF profile."""
    errors = []
    required_fields = ['name', 'format']

    for field in required_fields:
        if field not in profile or not profile[field]:
            errors.append(f"Preview profile {index + 1}: Missing required field '{field}'")

    # Validate start/end times
    if 'start' in profile and 'end' in profile:
        start = profile.get('start', 0)
        end = profile.get('end', 5)
        if start >= end:
            errors.append(f"Preview profile {index + 1}: Start time must be less than end time")

    # Validate FPS for GIF
    if profile.get('format') == 'gif' and 'fps' in profile:
        try:
            fps = int(profile['fps'])
            if fps < 1 or fps > 60:
                errors.append(f"Preview profile {index + 1}: FPS must be between 1 and 60")
        except (ValueError, TypeError):
            errors.append(f"Preview profile {index + 1}: FPS must be a valid number")

    return errors


def validate_thumbnail_profile(profile, index, media_type):
    """Validate a thumbnail profile."""
    errors = []
    required_fields = ['name', 'width', 'height', 'format']

    for field in required_fields:
        if field not in profile or not profile[field]:
            errors.append(f"{media_type.title()} thumbnail profile {index + 1}: Missing required field '{field}'")

    # Validate dimensions
    if 'width' in profile and profile['width'] and (profile['width'] < 32 or profile['width'] > 2048):
        errors.append(f"{media_type.title()} thumbnail profile {index + 1}: Width must be between 32 and 2048")

    if 'height' in profile and profile['height'] and (profile['height'] < 32 or profile['height'] > 2048):
        errors.append(f"{media_type.title()} thumbnail profile {index + 1}: Height must be between 32 and 2048")

    # Validate quality if present
    if 'quality' in profile and profile['quality'] is not None:
        try:
            quality = int(profile['quality'])
            if quality < 1 or quality > 100:
                errors.append(f"{media_type.title()} thumbnail profile {index + 1}: Quality must be between 1 and 100")
        except (ValueError, TypeError):
            errors.append(f"{media_type.title()} thumbnail profile {index + 1}: Quality must be a valid number")

    return errors


@configs_bp.route('/export/<int:config_id>', methods=['GET'])
@AuthService.token_required
def export_config(config_id):
    """Export config as downloadable JSON file."""
    user = g.current_user

    # Find config
    config = Config.query.get(config_id)

    if not config:
        return jsonify({'message': 'Config not found'}), 404

    # Check access
    if config.user_id is not None and config.user_id != user.id:
        return jsonify({'message': 'Access denied'}), 403

    # Create export data
    export_data = {
        'name': config.name,
        'description': config.description,
        'config': json.loads(config.config_json),
        'exported_at': datetime.utcnow().isoformat(),
        'version': '1.0'
    }

    return jsonify(export_data), 200, {
        'Content-Disposition': f'attachment; filename="{config.name.replace(" ", "_")}_config.json"',
        'Content-Type': 'application/json'
    }


@configs_bp.route('/import', methods=['POST'])
@AuthService.token_required
def import_config():
    """Import config from JSON."""
    user = g.current_user
    data = request.get_json()

    if not data:
        return jsonify({'message': 'No data provided'}), 400

    # Extract config data
    name = data.get('name', 'Imported Config')
    description = data.get('description', '')
    config_data = data.get('config')

    if not config_data:
        return jsonify({'message': 'Missing config data'}), 400

    # Validate config structure
    try:
        config_json = json.dumps(config_data) if isinstance(config_data, dict) else config_data
        json.loads(config_json)  # Validate JSON
    except (TypeError, json.JSONDecodeError):
        return jsonify({'message': 'Invalid config JSON'}), 400

    # Create new config
    config = Config(
        name=name,
        description=description,
        config_json=config_json,
        user_id=user.id,
        is_default=False
    )

    db.session.add(config)
    db.session.commit()

    return jsonify({
        'message': 'Config imported successfully',
        'id': config.id
    }), 201
