#!/usr/bin/env python3
"""
Test script for WebP conversion functionality
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from typing import List

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.schemas import (
    TranscodeMessage, TranscodeProfile, WebPConfig, OutputType, 
    S3OutputConfig, MediaMetadata
)
from consumer.transcode_worker import TranscodeWorker

def create_test_webp_profiles() -> List[TranscodeProfile]:
    """Create test WebP profiles with various configurations"""
    
    profiles = [
        # Basic animated WebP
        TranscodeProfile(
            id_profile="test_webp_basic",
            output_type=OutputType.WEBP,
            webp_config=WebPConfig(
                fps=10,
                width=480,
                height=270,
                duration=5.0,
                start_time=0,
                quality=80,
                animated=True,
                lossless=False,
                method=4,
                loop=0
            )
        ),
        
        # High quality lossless WebP
        TranscodeProfile(
            id_profile="test_webp_lossless",
            output_type=OutputType.WEBP,
            webp_config=WebPConfig(
                fps=15,
                width=640,
                height=360,
                duration=3.0,
                start_time=2,
                quality=100,
                animated=True,
                lossless=True,
                method=6,
                loop=0
            )
        ),
        
        # Static WebP (single frame)
        TranscodeProfile(
            id_profile="test_webp_static",
            output_type=OutputType.WEBP,
            webp_config=WebPConfig(
                fps=1,
                width=800,
                height=450,
                start_time=1,
                quality=85,
                animated=False,
                lossless=False,
                method=4
            )
        ),
        
        # Small fast WebP
        TranscodeProfile(
            id_profile="test_webp_small",
            output_type=OutputType.WEBP,
            webp_config=WebPConfig(
                fps=8,
                width=240,
                height=135,
                duration=3.0,
                start_time=0,
                quality=70,
                animated=True,
                lossless=False,
                method=0,  # Fast compression
                loop=0
            )
        )
    ]
    
    return profiles

def create_test_video():
    """Create a simple test video using FFmpeg"""
    test_video = "/tmp/test_video.mp4"
    
    # Create a simple test video if it doesn't exist
    if not os.path.exists(test_video):
        import subprocess
        cmd = [
            'ffmpeg', '-f', 'lavfi', '-i', 
            'testsrc=duration=10:size=640x480:rate=25', 
            '-c:v', 'libx264', '-preset', 'ultrafast', 
            '-y', test_video
        ]
        
        print("Creating test video...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to create test video: {result.stderr}")
        print(f"Test video created: {test_video}")
    
    return test_video

def test_webp_conversion():
    """Test WebP conversion with different profiles"""
    print("=" * 60)
    print("WebP Conversion Test")
    print("=" * 60)
    
    try:
        # Create test video
        test_video = create_test_video()
        
        # Create WebP profiles
        profiles = create_test_webp_profiles()
        
        # Create worker
        worker = TranscodeWorker()
        
        # Test each profile
        for profile in profiles:
            print(f"\\n--- Testing profile: {profile.id_profile} ---")
            print(f"WebP config: {profile.webp_config}")
            
            # Create test message
            message = TranscodeMessage(
                task_id=f"test_{profile.id_profile}_{int(datetime.now().timestamp())}",
                profile=profile,
                source_url=f"file://{test_video}",
                s3_output_config=S3OutputConfig(
                    bucket="test-bucket",
                    base_path="test-webp",
                    folder_structure="{task_id}/{profile_id}",
                    cleanup_temp_files=False  # Keep files for inspection
                )
            )
            
            try:
                # Process WebP
                temp_outputs = []
                temp_input = test_video  # Use test video directly
                output_urls = worker._process_webp(message, temp_input, temp_outputs)
                
                print(f"✅ Success! Generated {len(output_urls)} WebP outputs")
                for i, url in enumerate(output_urls):
                    print(f"   Output {i+1}: {url}")
                
                # Check file exists and get info
                for temp_output in temp_outputs:
                    if os.path.exists(temp_output):
                        file_size = os.path.getsize(temp_output)
                        print(f"   File: {temp_output}")
                        print(f"   Size: {file_size} bytes ({file_size/1024:.1f} KB)")
                        
                        # Try to get metadata
                        try:
                            from consumer.transcode_worker import extract_media_metadata
                            metadata = extract_media_metadata(temp_output)
                            print(f"   Metadata: {metadata}")
                        except Exception as e:
                            print(f"   Metadata extraction failed: {e}")
                    else:
                        print(f"   ❌ Output file not found: {temp_output}")
                
            except Exception as e:
                print(f"❌ Failed: {str(e)}")
                import traceback
                traceback.print_exc()
        
        print(f"\\n--- Test completed ---")
        print(f"Test video: {test_video}")
        
    except Exception as e:
        print(f"❌ Test setup failed: {str(e)}")
        import traceback
        traceback.print_exc()

def test_webp_vs_gif_comparison():
    """Compare WebP vs GIF output for same settings"""
    print("\\n" + "=" * 60)
    print("WebP vs GIF Comparison Test")
    print("=" * 60)
    
    try:
        test_video = create_test_video()
        worker = TranscodeWorker()
        
        # Common settings
        common_config = {
            "fps": 10,
            "width": 480,
            "height": 270,
            "duration": 5.0,
            "start_time": 0,
            "quality": 80,
        }
        
        # WebP profile
        webp_profile = TranscodeProfile(
            id_profile="comparison_webp",
            output_type=OutputType.WEBP,
            webp_config=WebPConfig(
                animated=True,
                lossless=False,
                method=4,
                loop=0,
                **common_config
            )
        )
        
        # GIF profile
        from models.schemas import GifConfig
        gif_profile = TranscodeProfile(
            id_profile="comparison_gif",
            output_type=OutputType.GIF,
            gif_config=GifConfig(
                colors=256,
                dither=True,
                optimize=True,
                loop=0,
                **common_config
            )
        )
        
        profiles = [webp_profile, gif_profile]
        results = {}
        
        for profile in profiles:
            print(f"\\n--- Testing {profile.output_type} ---")
            
            message = TranscodeMessage(
                task_id=f"comparison_{profile.output_type}_{int(datetime.now().timestamp())}",
                profile=profile,
                source_url=f"file://{test_video}",
                s3_output_config=S3OutputConfig(
                    bucket="test-bucket",
                    base_path="test-comparison",
                    folder_structure="{task_id}/{profile_id}",
                    cleanup_temp_files=False
                )
            )
            
            try:
                temp_outputs = []
                if profile.output_type == OutputType.WEBP:
                    output_urls = worker._process_webp(message, test_video, temp_outputs)
                else:  # GIF
                    output_urls = worker._process_gif(message, test_video, temp_outputs)
                
                # Get file info
                for temp_output in temp_outputs:
                    if os.path.exists(temp_output):
                        file_size = os.path.getsize(temp_output)
                        results[profile.output_type] = {
                            'file': temp_output,
                            'size': file_size,
                            'size_kb': file_size / 1024
                        }
                        print(f"   ✅ {profile.output_type}: {file_size} bytes ({file_size/1024:.1f} KB)")
                        break
                
            except Exception as e:
                print(f"   ❌ {profile.output_type} failed: {str(e)}")
                results[profile.output_type] = {'error': str(e)}
        
        # Compare results
        print(f"\\n--- Comparison Results ---")
        if OutputType.WEBP in results and OutputType.GIF in results:
            webp_data = results[OutputType.WEBP]
            gif_data = results[OutputType.GIF]
            
            if 'size' in webp_data and 'size' in gif_data:
                webp_size = webp_data['size']
                gif_size = gif_data['size']
                
                compression_ratio = (gif_size - webp_size) / gif_size * 100
                
                print(f"WebP size: {webp_size} bytes ({webp_size/1024:.1f} KB)")
                print(f"GIF size:  {gif_size} bytes ({gif_size/1024:.1f} KB)")
                print(f"WebP is {compression_ratio:.1f}% smaller than GIF")
                
                if compression_ratio > 0:
                    print("🎉 WebP provides better compression!")
                else:
                    print("🤔 GIF is smaller in this case")
        
    except Exception as e:
        print(f"❌ Comparison test failed: {str(e)}")

if __name__ == "__main__":
    # Run tests
    test_webp_conversion()
    test_webp_vs_gif_comparison()
    
    print("\\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)