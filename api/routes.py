from flask import Blueprint

# Create main API blueprint
api_bp = Blueprint('api', __name__)

# Import and register sub-blueprints
from .auth import auth_bp
from .media import media_bp
from .jobs import jobs_bp
from .configs import configs_bp

api_bp.register_blueprint(auth_bp, url_prefix='/auth')
api_bp.register_blueprint(media_bp, url_prefix='/media')
api_bp.register_blueprint(jobs_bp, url_prefix='/jobs')
api_bp.register_blueprint(configs_bp, url_prefix='/configs')

# Root route - API info
@api_bp.route('/')
def api_info():
    """Return API information."""
    return {
        'name': 'Media Transcode API',
        'version': '1.0.0',
        'endpoints': [
            '/api/auth',
            '/api/media',
            '/api/jobs',
            '/api/configs'
        ]
    }