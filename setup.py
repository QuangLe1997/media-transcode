#!/usr/bin/env python3
"""
Setup script for Media Transcode Service
"""

from setuptools import setup, find_packages

setup(
    name="transcode-service",
    version="1.0.0",
    description="Media Transcoding Service with WebP support",
    author="Media Transcode Team",
    python_requires=">=3.11",
    
    # Package configuration
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    
    # Dependencies
    install_requires=[
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.20.0",
        "sqlalchemy>=2.0.0",
        "alembic>=1.10.0",
        "pydantic>=2.0.0",
        "pillow>=10.0.0",
        "imageio>=2.25.0",
        "asyncpg>=0.28.0",
        "boto3>=1.26.0",
        "aioboto3>=11.0.0",
    ],
    
    # Optional dependencies
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "face-detection": [
            "onnxruntime>=1.14.0",
            "opencv-python>=4.7.0",
            "scikit-learn>=1.2.0",
        ],
    },
    
    # Entry points
    entry_points={
        "console_scripts": [
            "transcode-api=transcode_service.app:main",
            "transcode-task-listener=transcode_service.workers.task_listener:main",
            "transcode-face-worker=transcode_service.workers.face_detect_worker:main",
        ],
    },
    
    # Metadata
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video :: Conversion",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)