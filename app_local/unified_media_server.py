#!/usr/bin/env python3
"""
Unified Media Server - Flask backend for all media conversion needs
- WebP Converter: Convert video/image to WebP
- Media Transcode: Convert image to JPG, video to MP4
"""

import os
import shutil
import time
import uuid
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from universal_media_converter import UniversalMediaConverter

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Configuration
UPLOAD_FOLDER = 'temp_uploads'
WEBP_OUTPUT_FOLDER = 'videos/output'
TRANSCODE_OUTPUT_FOLDER = 'transcode_output'

ALLOWED_EXTENSIONS = {
    # Video formats
    'mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v', 'flv', 'wmv', 'm2ts', 'ts',
    # Image formats  
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'heic', 'raw'
}

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(WEBP_OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TRANSCODE_OUTPUT_FOLDER, exist_ok=True)

# Initialize unified converter
converter = UniversalMediaConverter()


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ================================
# WebP Converter Endpoints
# ================================

@app.route('/api/convert', methods=['POST'])
def convert_to_webp():
    """Handle media to WebP conversion request"""
    try:
        # Check if file is present
        if 'video' not in request.files:
            return jsonify({'error': 'No media file provided'}), 400

        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Get configuration parameters
        config = {
            # Basic settings
            'width': int(request.form.get('width')) if request.form.get('width') else None,
            'height': int(request.form.get('height')) if request.form.get('height') else None,
            'quality': int(request.form.get('quality', 85)),
            'fps': float(request.form.get('fps', 15)),
            'duration': float(request.form.get('duration', 6)),
            'speed': float(request.form.get('speed', 1.0)),
            'start_time': float(request.form.get('startTime', 0)),

            # Advanced settings
            'method': int(request.form.get('method', 4)),
            'preset': request.form.get('preset', 'default'),
            'near_lossless': int(request.form.get('nearLossless')) if request.form.get('nearLossless') else None,
            'alpha_quality': int(request.form.get('alphaQuality', 100)),
            'alpha_method': int(request.form.get('alphaMethod', 1)),

            # Image processing
            'contrast': float(request.form.get('contrast', 1.0)),
            'brightness': float(request.form.get('brightness', 0.0)),
            'saturation': float(request.form.get('saturation', 1.0)),
            'enable_denoising': request.form.get('denoising', 'false').lower() == 'true',
            'enable_sharpening': request.form.get('sharpening', 'false').lower() == 'true',
            'auto_filter': request.form.get('autoFilter', 'false').lower() == 'true',

            # Special modes
            'lossless': request.form.get('lossless', 'false').lower() == 'true',
            'pass_count': 2 if request.form.get('twoPass', 'false').lower() == 'true' else 1,
            'animated': request.form.get('animated', 'true').lower() == 'true',
            'loop': int(request.form.get('loopCount', 0)),
            'save_frames': request.form.get('saveFrames', 'false').lower() == 'true',
            'target_size': int(request.form.get('targetSize')) if request.form.get('targetSize') else None,

            # System settings
            'verbose': False
        }

        # Generate smart output filename
        unique_id = str(uuid.uuid4())[:4]
        input_filename = f"{unique_id}_{file.filename}"

        base_name = Path(file.filename).stem[:8]
        width_str = f"w{config['width']}" if config['width'] else "auto"
        quality_str = f"q{config['quality']}"
        fps_str = f"{int(config['fps'])}fps"
        speed_str = f"{config['speed']}x" if config['speed'] != 1.0 else ""
        duration_str = f"{int(config['duration'])}s"

        filename_parts = [base_name, width_str, quality_str, fps_str]
        if speed_str:
            filename_parts.append(speed_str)
        filename_parts.append(duration_str)

        output_filename = f"{unique_id}_{'_'.join(filename_parts)}.webp"

        # Save uploaded file
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        output_path = os.path.join(WEBP_OUTPUT_FOLDER, output_filename)

        file.save(input_path)

        # Perform conversion using UniversalMediaConverter
        start_time = time.time()
        result = converter.convert(
            input_path=input_path,
            output_path=output_path,
            # Map config parameters to UniversalMediaConverter format
            width=config.get('width'),
            height=config.get('height'),
            quality=config.get('quality', 85),
            fps=config.get('fps', 15),
            duration=config.get('duration', 6),
            start_time=config.get('start_time', 0),
            speed=config.get('speed', 1.0),
            method=config.get('method', 4),
            preset=config.get('preset', 'default'),
            near_lossless=config.get('near_lossless'),
            alpha_quality=config.get('alpha_quality', 100),
            alpha_method=config.get('alpha_method', 1),
            contrast=config.get('contrast', 1.0),
            brightness=config.get('brightness', 0.0),
            saturation=config.get('saturation', 1.0),
            enable_denoising=config.get('enable_denoising', False),
            enable_sharpening=config.get('enable_sharpening', False),
            auto_filter=config.get('auto_filter', False),
            lossless=config.get('lossless', False),
            pass_count=config.get('pass_count', 1),
            animated=config.get('animated', True),
            loop=config.get('loop', 0),
            save_frames=config.get('save_frames', False),
            target_size=config.get('target_size'),
            verbose=config.get('verbose', False)
        )
        conversion_time = time.time() - start_time

        # Clean up input file
        try:
            os.remove(input_path)
        except:
            pass

        if result.get('success'):
            file_size = os.path.getsize(output_path)

            response_data = {
                'success': True,
                'outputPath': output_path,
                'outputFilename': output_filename,
                'fileSize': file_size,
                'fileSizeMB': file_size / (1024 * 1024),
                'conversionTime': conversion_time,
                'config': config,
                'dimensions': {
                    'width': result.get('width') or 0,
                    'height': result.get('height') or 0
                },
                'actualDimensions': f"{result.get('width') or 'Unknown'}×{result.get('height') or 'Unknown'}",
                'duration': result.get('duration', 0),
                'frames': result.get('frames', 0),
                'codec': result.get('codec', 'webp')
            }

            return jsonify(response_data)
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Conversion failed'),
                'command': result.get('command', '')
            }), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/output/<filename>')
def serve_webp_output_file(filename):
    """Serve converted WebP files"""
    return send_from_directory(WEBP_OUTPUT_FOLDER, filename)


@app.route('/api/files')
def list_webp_output_files():
    """List all WebP output files"""
    try:
        files = []
        output_path = Path(WEBP_OUTPUT_FOLDER)

        for file_path in output_path.glob('*.webp'):
            stat = file_path.stat()
            files.append({
                'filename': file_path.name,
                'size': stat.st_size,
                'sizeMB': stat.st_size / (1024 * 1024),
                'modified': stat.st_mtime,
                'url': f'/api/output/{file_path.name}'
            })

        files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'files': files})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/presets')
def get_webp_presets():
    """Get WebP preset configurations"""
    presets = {
        'tiny': {
            'name': 'Tiny Preview',
            'width': 180,
            'quality': 60,
            'fps': 8,
            'duration': 3,
            'method': 1,
            'description': 'Small thumbnail, fast conversion'
        },
        'low': {
            'name': 'Preview Low',
            'width': 270,
            'quality': 75,
            'fps': 10,
            'duration': 5,
            'method': 2,
            'description': 'Medium quality, social media'
        },
        'high': {
            'name': 'Preview High',
            'width': 360,
            'quality': 85,
            'fps': 15,
            'duration': 6,
            'method': 4,
            'description': 'High quality, desktop'
        },
        'banner': {
            'name': 'Banner Ad',
            'width': 540,
            'quality': 80,
            'fps': 12,
            'duration': 8,
            'method': 4,
            'description': 'Large banner format'
        },
        'lossless': {
            'name': 'Lossless',
            'width': 270,
            'quality': 100,
            'fps': 12,
            'duration': 4,
            'method': 6,
            'lossless': True,
            'description': 'Maximum quality, larger size'
        }
    }

    return jsonify({'presets': presets})


# ================================
# Media Transcode Endpoints
# ================================

@app.route('/api/transcode', methods=['POST'])
def transcode_media():
    """Handle media transcode request (Image→JPG, Video→MP4)"""
    try:
        # Check if file is present
        if 'media' not in request.files:
            return jsonify({'error': 'No media file provided'}), 400

        file = request.files['media']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Get configuration parameters
        config = {
            # Common settings
            'width': int(request.form.get('width')) if request.form.get('width') else None,
            'height': int(request.form.get('height')) if request.form.get('height') else None,
            'quality': int(request.form.get('quality', 85)),

            # Image settings
            'jpeg_quality': int(request.form.get('jpegQuality', 90)),
            'optimize': request.form.get('optimize', 'false').lower() == 'true',
            'progressive': request.form.get('progressive', 'false').lower() == 'true',

            # Video settings
            'codec': request.form.get('codec', 'h264'),
            'crf': int(request.form.get('crf', 23)),
            'preset': request.form.get('preset', 'medium'),
            'fps': float(request.form.get('fps')) if request.form.get('fps') else None,
            'duration': float(request.form.get('duration')) if request.form.get('duration') else None,
            'start_time': float(request.form.get('startTime', 0)),

            # Video advanced settings
            'bitrate': request.form.get('bitrate'),
            'max_bitrate': request.form.get('maxBitrate'),
            'buffer_size': request.form.get('bufferSize'),
            'profile': request.form.get('profile', 'high'),
            'level': request.form.get('level', '4.1'),
            'pixel_format': request.form.get('pixelFormat', 'yuv420p'),

            # Audio settings
            'audio_codec': request.form.get('audioCodec', 'aac'),
            'audio_bitrate': request.form.get('audioBitrate', '128k'),
            'audio_sample_rate': int(request.form.get('audioSampleRate', 44100)),

            # Color/Filter settings
            'contrast': float(request.form.get('contrast', 1.0)),
            'brightness': float(request.form.get('brightness', 0.0)),
            'saturation': float(request.form.get('saturation', 1.0)),
            'gamma': float(request.form.get('gamma', 1.0)),
            'enable_denoising': request.form.get('denoising', 'false').lower() == 'true',
            'enable_sharpening': request.form.get('sharpening', 'false').lower() == 'true',

            # Advanced options
            'two_pass': request.form.get('twoPass', 'false').lower() == 'true',
            'hardware_accel': request.form.get('hardwareAccel', 'false').lower() == 'true',

            # System settings
            'verbose': False
        }

        # Detect media type for output extension
        media_type = converter._detect_media_type(file.filename)
        output_ext = '.jpg' if media_type == 'image' else '.mp4'

        # Generate smart output filename
        unique_id = str(uuid.uuid4())[:4]
        input_filename = f"{unique_id}_{file.filename}"

        base_name = Path(file.filename).stem[:10]

        if media_type == 'image':
            width_str = f"w{config['width']}" if config['width'] else "wauto"
            quality_str = f"q{config['jpeg_quality']}"
            filename_parts = [base_name, width_str, quality_str]
        else:  # video
            width_str = f"w{config['width']}" if config['width'] else "wauto"
            codec_str = config['codec']
            crf_str = f"crf{config['crf']}"
            preset_str = config['preset']
            duration_str = f"{int(config['duration'])}s" if config['duration'] else "full"
            filename_parts = [base_name, width_str, codec_str, crf_str, preset_str, duration_str]

        output_filename = f"{unique_id}_{'_'.join(filename_parts)}{output_ext}"

        # Save uploaded file
        input_path = os.path.join(UPLOAD_FOLDER, input_filename)
        output_path = os.path.join(TRANSCODE_OUTPUT_FOLDER, output_filename)

        file.save(input_path)

        # Perform conversion using UniversalMediaConverter
        start_time = time.time()
        result = converter.convert(
            input_path=input_path,
            output_path=output_path,
            # Map config parameters to UniversalMediaConverter format
            width=config.get('width'),
            height=config.get('height'),
            quality=config.get('quality', 85),
            # Image-specific
            jpeg_quality=config.get('jpeg_quality', 90),
            optimize=config.get('optimize', True),
            progressive=config.get('progressive', False),
            # Video-specific
            codec=config.get('codec', 'h264'),
            crf=config.get('crf', 23),
            mp4_preset=config.get('preset', 'medium'),
            fps=config.get('fps'),
            duration=config.get('duration'),
            start_time=config.get('start_time', 0),
            bitrate=config.get('bitrate'),
            max_bitrate=config.get('max_bitrate'),
            buffer_size=config.get('buffer_size'),
            profile=config.get('profile', 'high'),
            level=config.get('level', '4.1'),
            pixel_format=config.get('pixel_format', 'yuv420p'),
            # Audio settings
            audio_codec=config.get('audio_codec', 'aac'),
            audio_bitrate=config.get('audio_bitrate', '128k'),
            audio_sample_rate=config.get('audio_sample_rate', 44100),
            # Color/Filter settings
            contrast=config.get('contrast', 1.0),
            brightness=config.get('brightness', 0.0),
            saturation=config.get('saturation', 1.0),
            gamma=config.get('gamma', 1.0),
            enable_denoising=config.get('enable_denoising', False),
            enable_sharpening=config.get('enable_sharpening', False),
            # Advanced options
            two_pass=config.get('two_pass', False),
            hardware_accel=config.get('hardware_accel', False),
            verbose=config.get('verbose', False)
        )
        conversion_time = time.time() - start_time

        # Clean up input file
        try:
            os.remove(input_path)
        except:
            pass

        if result.get('success'):
            file_size = os.path.getsize(output_path)

            response_data = {
                'success': True,
                'outputPath': output_path,
                'outputFilename': output_filename,
                'fileSize': file_size,
                'fileSizeMB': file_size / (1024 * 1024),
                'conversionTime': conversion_time,
                'config': config,
                'mediaType': result.get('input_type'),
                'dimensions': {
                    'width': result.get('width') or 0,
                    'height': result.get('height') or 0
                },
                'actualDimensions': f"{result.get('width') or 'Unknown'}×{result.get('height') or 'Unknown'}",
                'duration': result.get('duration', 0),
                'fps': result.get('fps', 0),
                'codec': result.get('codec', 'unknown'),
                'bitRate': result.get('bit_rate', 0)
            }

            return jsonify(response_data)
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Conversion failed'),
                'command': result.get('command', ''),
                'mediaType': result.get('input_type', 'unknown')
            }), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/transcode/output/<filename>')
def serve_transcode_output_file(filename):
    """Serve converted transcode files"""
    return send_from_directory(TRANSCODE_OUTPUT_FOLDER, filename)


@app.route('/api/transcode/files')
def list_transcode_output_files():
    """List all transcode output files"""
    try:
        files = []
        output_path = Path(TRANSCODE_OUTPUT_FOLDER)

        for file_path in output_path.glob('*'):
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    'filename': file_path.name,
                    'size': stat.st_size,
                    'sizeMB': stat.st_size / (1024 * 1024),
                    'modified': stat.st_mtime,
                    'url': f'/api/transcode/output/{file_path.name}',
                    'extension': file_path.suffix.lower()
                })

        files.sort(key=lambda x: x['modified'], reverse=True)
        return jsonify({'files': files})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/transcode/presets')
def get_transcode_presets():
    """Get transcode preset configurations"""
    presets = {
        # Image presets
        'image_web': {
            'name': 'Web Optimized',
            'width': 800,
            'jpegQuality': 85,
            'optimize': True,
            'description': 'Optimized for web display'
        },
        'image_high': {
            'name': 'High Quality',
            'width': 1200,
            'jpegQuality': 95,
            'optimize': True,
            'progressive': True,
            'description': 'High quality for print'
        },
        'image_thumbnail': {
            'name': 'Thumbnail',
            'width': 300,
            'jpegQuality': 80,
            'optimize': True,
            'description': 'Small thumbnails'
        },

        # Video presets
        'video_web': {
            'name': 'Web Video',
            'width': 720,
            'codec': 'h264',
            'crf': 25,
            'preset': 'fast',
            'audioCodec': 'aac',
            'description': 'Optimized for web streaming'
        },
        'video_hd': {
            'name': 'HD Quality',
            'width': 1080,
            'codec': 'h264',
            'crf': 20,
            'preset': 'medium',
            'audioCodec': 'aac',
            'description': 'High definition quality'
        },
        'video_mobile': {
            'name': 'Mobile Friendly',
            'width': 480,
            'codec': 'h264',
            'crf': 28,
            'preset': 'fast',
            'audioCodec': 'aac',
            'audioBitrate': '96k',
            'description': 'Small size for mobile'
        },
        'video_4k': {
            'name': '4K Quality',
            'codec': 'h265',
            'crf': 22,
            'preset': 'slow',
            'audioCodec': 'aac',
            'audioBitrate': '192k',
            'description': '4K high quality (H265)'
        }
    }

    return jsonify({'presets': presets})


# ================================
# Common Health Endpoints
# ================================

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'ffmpeg_available': shutil.which('ffmpeg') is not None,
        'webpinfo_available': shutil.which('webpinfo') is not None,
        'upload_folder': UPLOAD_FOLDER,
        'webp_output_folder': WEBP_OUTPUT_FOLDER,
        'transcode_output_folder': TRANSCODE_OUTPUT_FOLDER,
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'services': {
            'webp_converter': 'active',
            'media_transcode': 'active'
        }
    })


# ================================
# UI Routes
# ================================

@app.route('/')
def serve_webp_ui():
    """Serve the WebP converter UI (default)"""
    return send_from_directory('.', 'webp_converter_ui.html')


@app.route('/webp')
def serve_webp_ui_explicit():
    """Serve the WebP converter UI"""
    return send_from_directory('.', 'webp_converter_ui.html')


@app.route('/transcode')
def serve_transcode_ui():
    """Serve the transcode UI"""
    return send_from_directory('.', 'media_transcode_ui.html')


@app.route('/viewer')
def serve_viewer_ui():
    """Serve the WebP viewer UI"""
    return send_from_directory('.', 'webp_viewer.html')


if __name__ == '__main__':
    print("🚀 Starting Unified Media Server...")
    print(f"📁 Upload folder: {UPLOAD_FOLDER}")
    print(f"📁 WebP output folder: {WEBP_OUTPUT_FOLDER}")
    print(f"📁 Transcode output folder: {TRANSCODE_OUTPUT_FOLDER}")
    print("🌐 Server will be available at: http://localhost:5001")
    print("🎨 WebP Converter: http://localhost:5001/webp")
    print("🎬 Media Transcode: http://localhost:5001/transcode")
    print("👁️  WebP Viewer: http://localhost:5001/viewer")

    app.run(debug=True, host='0.0.0.0', port=5001)
