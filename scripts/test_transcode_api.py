#!/usr/bin/env python3
"""
Test script to create transcode API call with local video input and config templates.
"""

import json
import requests
import os
import time
import sys

def convert_v1_to_v2(v1_profile):
    """Convert a v1 profile to v2 format."""
    v2_profile = {
        "id_profile": v1_profile["id_profile"],
        "input_type": v1_profile.get("input_type", "video")
    }
    
    # Convert config based on output_type
    output_type = v1_profile["output_type"]
    config = {}
    
    if output_type == "video":
        # Extract from video_config
        video_config = v1_profile.get("video_config", {})
        config = {
            "output_format": "mp4",
            "codec": video_config.get("codec", "libx264"),
            "width": video_config.get("max_width"),
            "height": video_config.get("max_height"), 
            "crf": video_config.get("crf"),
            "mp4_preset": video_config.get("preset", "fast"),
            "profile": video_config.get("profile", "main"),
            "level": video_config.get("level"),
            "pixel_format": video_config.get("pixel_format", "yuv420p"),
            "audio_codec": video_config.get("audio_codec"),
            "audio_bitrate": video_config.get("audio_bitrate"),
            "fps": video_config.get("fps"),
            "duration": video_config.get("duration"),
            "start_time": video_config.get("start_time", 0),
            "verbose": False
        }
        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}
        
    elif output_type == "webp":
        # Extract from webp_config
        webp_config = v1_profile.get("webp_config", {})
        config = {
            "output_format": "webp",
            "width": webp_config.get("width"),
            "height": webp_config.get("height"),
            "quality": webp_config.get("quality", 80),
            "fps": webp_config.get("fps", 15),
            "duration": webp_config.get("duration", 5.0),
            "start_time": webp_config.get("start_time", 1.0),
            "animated": webp_config.get("animated", True),
            "lossless": webp_config.get("lossless", False),
            "method": webp_config.get("method", 2),
            "preset": webp_config.get("preset", "default"),
            "loop": webp_config.get("loop", 0),
            "verbose": False
        }
        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}
        
    elif output_type == "image":
        # Extract from image_config
        image_config = v1_profile.get("image_config", {})
        config = {
            "output_format": image_config.get("format", "jpeg"),
            "width": image_config.get("max_width"),
            "height": image_config.get("max_height"),
            "quality": image_config.get("quality", 85),
            "start_time": image_config.get("start_time", 3.0),
            "jpeg_quality": image_config.get("quality", 85),
            "optimize": image_config.get("progressive", True),
            "progressive": image_config.get("progressive", True),
            "verbose": False
        }
        # Remove None values  
        config = {k: v for k, v in config.items() if v is not None}
        
    elif output_type == "gif":
        # Extract from gif_config
        gif_config = v1_profile.get("gif_config", {})
        config = {
            "output_format": "gif",
            "width": gif_config.get("width"),
            "height": gif_config.get("height"),
            "fps": gif_config.get("fps", 12),
            "duration": gif_config.get("duration", 3.0),
            "start_time": gif_config.get("start_time", 2.0),
            "quality": gif_config.get("quality", 75),
            "loop": gif_config.get("loop", 0),
            "verbose": False
        }
        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}
    
    v2_profile["config"] = config
    return v2_profile

def get_available_templates():
    """Get available config templates from API."""
    api_url = 'http://192.168.0.234:8087'
    
    try:
        response = requests.get(f"{api_url}/config-templates")
        if response.status_code == 200:
            result = response.json()
            templates = result.get('templates', [])
            print(f"📋 Available templates ({len(templates)}):")
            for i, template in enumerate(templates, 1):
                print(f"   {i}. {template.get('name', 'Unknown')} (ID: {template.get('template_id', 'N/A')})")
            return templates
        else:
            print(f"❌ Failed to get templates: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error fetching templates: {e}")
        return []

def get_template_config(template_id):
    """Get config from a specific template."""
    api_url = 'http://192.168.0.234:8087'
    
    try:
        response = requests.get(f"{api_url}/config-templates/{template_id}")
        if response.status_code == 200:
            result = response.json()
            return result.get('config', [])
        else:
            print(f"❌ Failed to get template config: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error fetching template config: {e}")
        return None

def create_transcode_task_with_file(template_config, video_file_path):
    """Create a transcode task with file upload and template config."""
    api_url = 'http://192.168.0.234:8087'
    
    # Prepare S3 config
    s3_config = {
        "bucket_name": "dev-facefusion-media",
        "base_path": "transcode-outputs", 
        "folder_structure": "{task_id}/profiles/{profile_id}",
        "cleanup_on_task_reset": True,
        "cleanup_temp_files": True,
        "upload_timeout": 900,
        "max_retries": 3
    }
    
    # Prepare form data
    form_data = {
        'profiles': json.dumps(template_config),
        's3_output_config': json.dumps(s3_config)
    }
    
    # Prepare file upload
    files = {}
    if os.path.exists(video_file_path):
        files['video'] = (os.path.basename(video_file_path), open(video_file_path, 'rb'), 'video/mp4')
    
    try:
        print(f"🚀 Creating transcode task with file upload...")
        print(f"   File: {video_file_path}")
        print(f"   File size: {os.path.getsize(video_file_path) / 1024 / 1024:.2f} MB")
        print(f"   Profiles: {len(template_config)} profile(s)")
        
        response = requests.post(f"{api_url}/transcode", data=form_data, files=files)
        
        # Close file handle
        if 'video' in files:
            files['video'][1].close()
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            print(f"✅ Task created successfully!")
            print(f"   Task ID: {task_id}")
            print(f"   Status: {result.get('status', 'unknown')}")
            return task_id
        else:
            print(f"❌ Failed to create task: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating task: {e}")
        # Close file handle if error
        if 'video' in files and files['video'][1]:
            files['video'][1].close()
        return None

def check_task_status(task_id):
    """Check the status of a transcode task."""
    api_url = 'http://192.168.0.234:8087'
    
    try:
        response = requests.get(f"{api_url}/tasks/{task_id}")
        
        if response.status_code == 200:
            result = response.json()
            status = result.get('status', 'unknown')
            print(f"📊 Task Status: {status}")
            
            if status == 'COMPLETED':
                outputs = result.get('outputs', {})
                print(f"   ✅ Outputs: {len(outputs)} files generated")
                for profile_id, output_info in outputs.items():
                    print(f"      - {profile_id}: {output_info.get('s3_url', 'N/A')}")
            elif status == 'FAILED':
                error_msg = result.get('error_message', 'No error details')
                print(f"   ❌ Error: {error_msg}")
                failed_profiles = result.get('failed_profiles', [])
                if failed_profiles:
                    print(f"   Failed profiles: {failed_profiles}")
            elif status == 'PROCESSING':
                print(f"   ⏳ Task is still processing...")
                
            return result
        else:
            print(f"❌ Failed to get task status: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking task: {e}")
        return None

def monitor_task(task_id, max_wait_time=300):
    """Monitor a task until completion or timeout."""
    api_url = 'http://192.168.0.234:8087'
    start_time = time.time()
    
    print(f"⏰ Monitoring task {task_id} (max wait: {max_wait_time}s)")
    
    while time.time() - start_time < max_wait_time:
        result = check_task_status(task_id)
        
        if not result:
            break
            
        status = result.get('status', 'unknown')
        
        if status in ['COMPLETED', 'FAILED']:
            print(f"🏁 Task finished with status: {status}")
            return result
            
        print(f"   ⏳ Waiting... ({int(time.time() - start_time)}s elapsed)")
        time.sleep(10)  # Check every 10 seconds
    
    print(f"⏰ Monitoring timeout after {max_wait_time}s")
    return check_task_status(task_id)

def test_local_video_transcode():
    """Test transcode with local video file."""
    
    # Step 1: Get available templates
    print("=" * 60)
    print("🎬 Transcode API Test with Local Video")
    print("=" * 60)
    
    templates = get_available_templates()
    if not templates:
        print("❌ No templates available!")
        return
    
    # Step 2: Select Quick Web Video template
    quick_web_template = None
    for template in templates:
        if template.get('name') == 'Quick Web Video':
            quick_web_template = template
            break
    
    if not quick_web_template:
        print("❌ Quick Web Video template not found!")
        print("Using first available template instead...")
        quick_web_template = templates[0]
    
    template_id = quick_web_template.get('template_id')
    template_name = quick_web_template.get('name')
    
    print(f"\n🎯 Selected template: {template_name}")
    print(f"   Template ID: {template_id}")
    
    # Step 3: Get template config
    v1_template_config = get_template_config(template_id)
    if not v1_template_config:
        print("❌ Failed to get template config!")
        return
    
    print(f"   V1 Config profiles: {len(v1_template_config)}")
    for i, profile in enumerate(v1_template_config, 1):
        print(f"      {i}. {profile.get('id_profile', 'unknown')} ({profile.get('output_type', 'unknown')})")
    
    # Step 3.5: Convert V1 to V2 format
    print(f"   Converting to V2 format...")
    v2_template_config = []
    for v1_profile in v1_template_config:
        v2_profile = convert_v1_to_v2(v1_profile)
        v2_template_config.append(v2_profile)
        print(f"      ✅ Converted: {v2_profile.get('id_profile')} -> V2")
    
    template_config = v2_template_config
    
    # Step 4: Use local video file path
    video_path = "/Users/quang/Documents/skl-workspace/transcode/media-transcode/app_local/videos/input/video2.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return
    
    print(f"\n📁 Input video: {video_path}")
    file_size = os.path.getsize(video_path)
    print(f"   File size: {file_size / 1024 / 1024:.2f} MB")
    
    # Step 5: Create transcode task
    print(f"\n" + "="*60)
    task_id = create_transcode_task_with_file(template_config, video_path)
    
    if not task_id:
        return
    
    # Step 5: Monitor task
    print(f"\n" + "="*60)
    final_result = monitor_task(task_id, max_wait_time=180)  # 3 minutes max
    
    if final_result:
        print(f"\n📊 Final Result:")
        print(json.dumps(final_result, indent=2))
    
    return task_id

if __name__ == "__main__":
    print("🚀 Starting transcode API test...")
    task_id = test_local_video_transcode()
    
    if task_id:
        print(f"\n✅ Test completed. Task ID: {task_id}")
        print(f"💡 You can also check logs and status manually:")
        print(f"   GET http://192.168.0.234:8087/tasks/{task_id}")
    else:
        print(f"\n❌ Test failed!")