from flask import Blueprint, request, jsonify, g
from services.auth_service import AuthService
from database.models import User

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