from flask import Blueprint, request, jsonify, g

from database.models import User
from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()

    # Log data for debugging
    print("Register request data:", data)

    # Validate required fields
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing required fields'}), 400

    # Create user
    success, message, user = AuthService.create_user(
        username=data.get('username'),
        password=data.get('password'),
        email=data.get('email')
    )

    if success:
        return jsonify({'message': message}), 201
    else:
        return jsonify({'message': message}), 409


@auth_bp.route('/login', methods=['POST'])
def login():
    """Login and get authentication token."""
    data = request.get_json()

    # Validate required fields
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing required fields'}), 400

    # Authenticate user
    success, message, user_data = AuthService.authenticate(
        username=data.get('username'),
        password=data.get('password')
    )

    if success:
        return jsonify({
            'message': message,
            'token': user_data['token'],
            'user': {
                'id': user_data['id'],
                'username': user_data['username'],
                'email': user_data['email']
            }
        }), 200
    else:
        return jsonify({'message': message}), 401


@auth_bp.route('/profile', methods=['GET'])
@AuthService.token_required
def get_profile():
    """Get the current user's profile."""
    user = g.current_user

    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'created_at': user.created_at.isoformat()
    }), 200


@auth_bp.route('/change-password', methods=['PUT'])
@AuthService.token_required
def change_password():
    """Change the current user's password."""
    user = g.current_user
    data = request.get_json()

    # Validate required fields
    if not data or not data.get('current_password') or not data.get('new_password'):
        return jsonify({'message': 'Missing required fields'}), 400

    # Change password
    success, message = AuthService.change_password(
        user_id=user.id,
        current_password=data.get('current_password'),
        new_password=data.get('new_password')
    )

    if success:
        return jsonify({'message': message}), 200
    else:
        return jsonify({'message': message}), 401


@auth_bp.route('/logout', methods=['POST'])
@AuthService.token_required
def logout():
    """Logout a user. (Client-side token removal)"""
    # JWT is stateless, so we don't need to do anything on the server side
    # The client should remove the token from their local storage
    return jsonify({'message': 'Logout successful'}), 200


@auth_bp.route('/profile', methods=['PUT'])
@AuthService.token_required
def update_profile():
    """Update user profile information."""
    user = g.current_user
    data = request.get_json()

    # Update email if provided
    if 'email' in data:
        email = data['email'].strip()
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user.id:
            return jsonify({'message': 'Email already in use'}), 409
        user.email = email

    # Save changes
    from database.models import db
    db.session.commit()

    return jsonify({
        'message': 'Profile updated successfully',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'created_at': user.created_at.isoformat()
        }
    }), 200


@auth_bp.route('/delete-account', methods=['DELETE'])
@AuthService.token_required
def delete_account():
    """Delete user account and all associated data."""
    user = g.current_user
    data = request.get_json()

    # Require password confirmation
    if not data or not data.get('password'):
        return jsonify({'message': 'Password confirmation required'}), 400

    # Verify password
    if not user.check_password(data['password']):
        return jsonify({'message': 'Invalid password'}), 401

    # Delete all user data (cascading deletes will handle related records)
    from database.models import db
    db.session.delete(user)
    db.session.commit()

    return jsonify({'message': 'Account deleted successfully'}), 200


@auth_bp.route('/refresh-token', methods=['POST'])
@AuthService.token_required
def refresh_token():
    """Refresh authentication token."""
    user = g.current_user

    # Generate new token
    new_token = AuthService.generate_token(user.id)

    return jsonify({
        'message': 'Token refreshed successfully',
        'token': new_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    }), 200


@auth_bp.route('/verify-token', methods=['GET'])
@AuthService.token_required
def verify_token():
    """Verify if token is valid."""
    user = g.current_user

    return jsonify({
        'valid': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email
        }
    }), 200
