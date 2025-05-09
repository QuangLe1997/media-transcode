import jwt
import datetime
from functools import wraps
from typing import Dict, Tuple, Optional, Any, Callable
from flask import request, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash

from database.models import User, db


class AuthService:
    @staticmethod
    def create_user(username: str, password: str, email: Optional[str] = None) -> Tuple[bool, str, Optional[User]]:
        """
        Create a new user account.

        Args:
            username: Username
            password: Plain text password
            email: Optional email address

        Returns:
            Tuple of (success, message, user)
        """
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return False, "Username already exists", None

        # Check if email already exists (if provided)
        if email:
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                return False, "Email already exists", None

        # Create new user
        try:
            new_user = User(username=username, email=email)
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()

            return True, "User created successfully", new_user
        except Exception as e:
            db.session.rollback()
            return False, f"Error creating user: {str(e)}", None

    @staticmethod
    def authenticate(username: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Authenticate a user and generate token.

        Args:
            username: Username
            password: Plain text password

        Returns:
            Tuple of (success, message, data)
            where data is a dict with token and user info on success
        """
        # Find user
        user = User.query.filter_by(username=username).first()

        # Check credentials
        if not user or not user.check_password(password):
            return False, "Invalid username or password", None

        # Generate token
        token = AuthService.generate_token(user.id, user.username)

        # Return user data and token
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'token': token
        }

        return True, "Authentication successful", user_data

    @staticmethod
    def generate_token(user_id: int, username: str) -> str:
        """
        Generate JWT token for user.

        Args:
            user_id: User ID
            username: Username

        Returns:
            JWT token string
        """
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }

        return jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def verify_token(token: str) -> Tuple[bool, str, Optional[User]]:
        """
        Verify JWT token and get user.

        Args:
            token: JWT token string

        Returns:
            Tuple of (success, message, user)
        """
        try:
            # Decode token
            payload = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )

            # Get user
            user = User.query.get(payload['user_id'])

            if not user:
                return False, "User not found", None

            return True, "Token valid", user

        except jwt.ExpiredSignatureError:
            return False, "Token has expired", None
        except jwt.InvalidTokenError:
            return False, "Invalid token", None
        except Exception as e:
            return False, f"Error verifying token: {str(e)}", None

    @staticmethod
    def token_required(f: Callable) -> Callable:
        """
        Decorator for protected routes that require authentication.

        Usage:
            @app.route('/protected')
            @AuthService.token_required
            def protected_route():
                return 'This is protected'
        """

        @wraps(f)
        def decorated(*args, **kwargs):
            token = None

            # Check for token in headers
            if 'Authorization' in request.headers:
                auth_header = request.headers['Authorization']
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]

            if not token:
                return {'message': 'Token is missing'}, 401

            # Verify token
            success, message, user = AuthService.verify_token(token)

            if not success:
                return {'message': message}, 401

            # Set current user in request context
            g.current_user = user

            return f(*args, **kwargs)

        return decorated

    @staticmethod
    def change_password(user_id: int, current_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Change user password.

        Args:
            user_id: User ID
            current_password: Current password
            new_password: New password

        Returns:
            Tuple of (success, message)
        """
        # Find user
        user = User.query.get(user_id)

        if not user:
            return False, "User not found"

        # Check current password
        if not user.check_password(current_password):
            return False, "Current password is incorrect"

        # Update password
        try:
            user.set_password(new_password)
            db.session.commit()
            return True, "Password changed successfully"
        except Exception as e:
            db.session.rollback()
            return False, f"Error changing password: {str(e)}"