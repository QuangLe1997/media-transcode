"""
WSGI entry point for the Media Transcode Service.
This file is used by production WSGI servers like Gunicorn.
"""
from app import app

if __name__ == "__main__":
    app.run()