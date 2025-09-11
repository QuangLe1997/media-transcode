#!/usr/bin/env python3
"""
Development server script for the Media Transcode Service.
"""
import os
from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7889))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'

    # Run the Flask development server
    app.run(host=host, port=port, debug=debug)