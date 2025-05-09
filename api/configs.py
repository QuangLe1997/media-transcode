import json
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

    # Delete from database
    db.session.delete(config)
    db.session.commit()

    return jsonify({'message': 'Config deleted successfully'}), 200


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