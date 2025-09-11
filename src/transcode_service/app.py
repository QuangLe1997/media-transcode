import os

from flask import Flask, render_template, send_from_directory, jsonify, request
from flask_cors import CORS

from .api.routes import api_bp
from .core.config import get_config
from .database.models import db


def create_app(config_class=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load config
    if config_class is None:
        config_class = get_config()
    app.config.from_object(config_class)

    # Initialize extensions
    CORS(app)
    db.init_app(app)

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')

    # Create database tables
    with app.app_context():
        db.create_all()

    # Define routes
    @app.route('/')
    def index():
        return render_template('index.html')

    # Auth routes
    @app.route('/login')
    def login():
        return render_template('login.html')

    @app.route('/register')
    def register():
        return render_template('register.html')

    @app.route('/profile')
    def profile():
        return render_template('profile.html')

    @app.route('/dashboard')
    def dashboard():
        return render_template('dashboard.html')

    # Jobs routes
    @app.route('/jobs')
    def jobs():
        return render_template('jobs.html')

    @app.route('/jobs/new')
    def new_job():
        return render_template('new_job.html')

    @app.route('/jobs/<job_id>')
    def job_detail(job_id):
        return render_template('job_detail.html')

    # Configs routes
    @app.route('/configs')
    def configs():
        return render_template('configs.html')

    @app.route('/configs/new')
    def new_config():
        return render_template('new_config.html')

    @app.route('/configs/edit/<config_id>')
    def edit_config(config_id):
        return render_template('new_config.html', config_id=config_id)
    
    # Static files routes
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Config samples route
    @app.route('/config_samples/<path:filename>')
    def config_samples(filename):
        return send_from_directory('config_samples', filename)

    # Health check route
    @app.route('/health')
    def health_check():
        return jsonify({'status': 'ok'}), 200

    # Debug route (only in development)
    if app.config['DEBUG']:
        @app.route('/debug/routes')
        def debug_routes():
            """Display all registered routes"""
            rules = []
            for rule in app.url_map.iter_rules():
                rules.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods),
                    'rule': str(rule)
                })
            return jsonify(sorted(rules, key=lambda x: x['rule']))

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'message': 'Not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'message': 'Server error'}), 500
        return render_template('errors/500.html'), 500

    return app


# Create app instance
app = create_app()

def main():
    """Main entry point for running the application"""
    import os
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', '8087'))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    app.run(debug=debug, host=host, port=port)


if __name__ == '__main__':
    main()
