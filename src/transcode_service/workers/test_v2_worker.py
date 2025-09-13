#!/usr/bin/env python3
"""
Test script for TranscodeWorker v2
Demonstrates how to use the new UniversalMediaConverter-based system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas_v2 import (
    UniversalTranscodeMessage, 
    UniversalTranscodeProfile, 
    UniversalConverterConfig,
    S3OutputConfig,
    OutputFormat
)
from workers.transcode_worker_v2 import TranscodeWorkerV2

def test_webp_conversion():
    """Test WebP conversion using v2 worker"""
    print("🧪 Testing WebP conversion with TranscodeWorker v2...")
    
    # Create WebP config
    webp_config = UniversalConverterConfig(
        output_format=OutputFormat.WEBP,
        width=360,
        height=None,  # Maintain aspect ratio
        quality=85,
        fps=15,
        duration=6.0,
        start_time=0,
        speed=1.0,
        lossless=False,
        method=4,
        preset="default",
        animated=True,
        loop=0,  # Infinite loop
        verbose=True
    )
    
    # Create profile
    profile = UniversalTranscodeProfile(
        id_profile="test_webp_profile",
        input_type="video",
        output_filename="test_video_converted",
        config=webp_config
    )
    
    # Create S3 config (minimal for testing)
    s3_config = S3OutputConfig(
        bucket="test-bucket",
        base_path="test-outputs",
        folder_structure="{task_id}/profiles/{profile_id}",
        cleanup_temp_files=False  # Keep files for inspection
    )
    
    # Create message
    message = UniversalTranscodeMessage(
        task_id="test-task-001",
        source_url="https://example.com/test-video.mp4",  # Replace with real URL
        profile=profile,
        s3_output_config=s3_config,
        source_key=None
    )
    
    # Process (this will fail without real URL and S3 setup, but shows the flow)
    try:
        worker = TranscodeWorkerV2()
        worker.process_transcode_task(message)
        print("✅ WebP conversion test completed")
    except Exception as e:
        print(f"❌ WebP conversion test failed (expected): {e}")

def test_jpg_conversion():
    """Test JPG conversion using v2 worker"""
    print("🧪 Testing JPG conversion with TranscodeWorker v2...")
    
    # Create JPG config
    jpg_config = UniversalConverterConfig(
        output_format=OutputFormat.JPG,
        width=800,
        height=600,
        jpeg_quality=90,
        optimize=True,
        progressive=False,
        verbose=True
    )
    
    # Create profile
    profile = UniversalTranscodeProfile(
        id_profile="test_jpg_profile",
        input_type="image",
        output_filename="test_image_converted",
        config=jpg_config
    )
    
    # Create S3 config
    s3_config = S3OutputConfig(
        bucket="test-bucket",
        base_path="test-outputs",
        cleanup_temp_files=False
    )
    
    # Create message
    message = UniversalTranscodeMessage(
        task_id="test-task-002",
        source_url="https://example.com/test-image.png",  # Replace with real URL
        profile=profile,
        s3_output_config=s3_config
    )
    
    try:
        worker = TranscodeWorkerV2()
        worker.process_transcode_task(message)
        print("✅ JPG conversion test completed")
    except Exception as e:
        print(f"❌ JPG conversion test failed (expected): {e}")

def test_mp4_conversion():
    """Test MP4 conversion using v2 worker"""
    print("🧪 Testing MP4 conversion with TranscodeWorker v2...")
    
    # Create MP4 config
    mp4_config = UniversalConverterConfig(
        output_format=OutputFormat.MP4,
        width=1280,
        height=720,
        fps=30,
        duration=10.0,
        codec="h264",
        crf=23,
        mp4_preset="medium",
        profile="high",
        level="4.1",
        audio_codec="aac",
        audio_bitrate="128k",
        verbose=True
    )
    
    # Create profile
    profile = UniversalTranscodeProfile(
        id_profile="test_mp4_profile",
        input_type="video",
        output_filename="test_video_h264",
        config=mp4_config
    )
    
    # Create S3 config
    s3_config = S3OutputConfig(
        bucket="test-bucket",
        base_path="test-outputs",
        cleanup_temp_files=False
    )
    
    # Create message
    message = UniversalTranscodeMessage(
        task_id="test-task-003",
        source_url="https://example.com/test-input.avi",  # Replace with real URL
        profile=profile,
        s3_output_config=s3_config
    )
    
    try:
        worker = TranscodeWorkerV2()
        worker.process_transcode_task(message)
        print("✅ MP4 conversion test completed")
    except Exception as e:
        print(f"❌ MP4 conversion test failed (expected): {e}")

def demonstrate_config_format():
    """Show examples of v2 configuration format"""
    print("\n📋 UniversalMediaConverter Configuration Examples:")
    print("=" * 60)
    
    # WebP config example
    webp_example = {
        "task_id": "demo-webp-001",
        "source_url": "https://example.com/video.mp4",
        "profile": {
            "id_profile": "webp_animated",
            "input_type": "video",
            "output_filename": "animated_preview",
            "config": {
                "output_format": "webp",
                "width": 480,
                "quality": 85,
                "fps": 12,
                "duration": 8.0,
                "animated": True,
                "loop": 0,
                "lossless": False,
                "method": 4,
                "preset": "default"
            }
        },
        "s3_output_config": {
            "bucket": "media-outputs",
            "base_path": "transcode-results",
            "folder_structure": "{task_id}/profiles/{profile_id}"
        }
    }
    
    print("WebP Animated Example:")
    print(f"  Task ID: {webp_example['task_id']}")
    print(f"  Output: {webp_example['profile']['config']['width']}px WebP @ {webp_example['profile']['config']['fps']}fps")
    print(f"  Duration: {webp_example['profile']['config']['duration']}s")
    print(f"  Quality: {webp_example['profile']['config']['quality']}")
    
    # JPG config example
    jpg_example = {
        "profile": {
            "id_profile": "jpg_thumbnail",
            "config": {
                "output_format": "jpg",
                "width": 300,
                "height": 300,
                "jpeg_quality": 85,
                "optimize": True,
                "progressive": False
            }
        }
    }
    
    print("\nJPG Thumbnail Example:")
    print(f"  Dimensions: {jpg_example['profile']['config']['width']}x{jpg_example['profile']['config']['height']}")
    print(f"  Quality: {jpg_example['profile']['config']['jpeg_quality']}")
    print(f"  Optimized: {jpg_example['profile']['config']['optimize']}")
    
    # MP4 config example
    mp4_example = {
        "profile": {
            "id_profile": "mp4_hd",
            "config": {
                "output_format": "mp4",
                "width": 1920,
                "height": 1080,
                "codec": "h264",
                "crf": 20,
                "mp4_preset": "slow",
                "audio_codec": "aac",
                "audio_bitrate": "192k"
            }
        }
    }
    
    print("\nMP4 HD Example:")
    print(f"  Resolution: {mp4_example['profile']['config']['width']}x{mp4_example['profile']['config']['height']}")
    print(f"  Codec: {mp4_example['profile']['config']['codec']}")
    print(f"  CRF: {mp4_example['profile']['config']['crf']}")
    print(f"  Audio: {mp4_example['profile']['config']['audio_codec']} @ {mp4_example['profile']['config']['audio_bitrate']}")

def main():
    """Run all tests and demonstrations"""
    print("🚀 TranscodeWorker v2 - UniversalMediaConverter Integration Test")
    print("=" * 70)
    
    print("\n📝 Key Differences from v1:")
    print("- No GIF support (removed)")
    print("- Unified parameter structure for WebP, JPG, MP4")
    print("- Uses UniversalMediaConverter from app_local")
    print("- Simplified message format")
    print("- Direct parameter mapping (no complex config building)")
    
    demonstrate_config_format()
    
    print("\n🔧 Running conversion tests...")
    test_webp_conversion()
    test_jpg_conversion() 
    test_mp4_conversion()
    
    print(f"\n✅ All tests completed!")
    print("\n💡 To use in production:")
    print("1. Start task_listener_v2.py to handle incoming messages")
    print("2. Start transcode_worker_v2.py to process tasks")
    print("3. Send UniversalTranscodeMessage format to pub/sub")
    print("4. Use schemas_v2.py for message validation")

if __name__ == "__main__":
    main()