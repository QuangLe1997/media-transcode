#!/usr/bin/env python3
"""
Test S3 fix with local API server.
"""

import json
import requests
import os
import time

def test_s3_fix_locally():
    """Test the S3 fix with local API server."""
    api_url = 'http://localhost:8086'
    
    print("🔧 Testing S3 Fix Locally")
    print("=" * 40)
    
    # Use smaller template for quick test
    quick_template = [
        {
            "id_profile": "test_thumbnail",
            "input_type": "video",
            "config": {
                "output_format": "jpeg",
                "width": 200,
                "height": 150,
                "quality": 80,
                "start_time": 2.0,
                "verbose": False
            }
        }
    ]
    
    # Simple S3 config
    s3_config = {
        "bucket_name": "dev-facefusion-media",
        "base_path": "test-outputs",
        "folder_structure": "{task_id}/profiles/{profile_id}",
        "cleanup_on_task_reset": True,
        "cleanup_temp_files": True,
        "upload_timeout": 60,
        "max_retries": 2
    }
    
    # Prepare small test video
    video_path = "/Users/quang/Documents/skl-workspace/transcode/media-transcode/app_local/videos/input/video3.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ Test video not found: {video_path}")
        return False
    
    print(f"📁 Using test video: {os.path.basename(video_path)}")
    print(f"   Size: {os.path.getsize(video_path) / 1024:.1f} KB")
    
    # Prepare request
    form_data = {
        'profiles': json.dumps(quick_template),
        's3_output_config': json.dumps(s3_config)
    }
    
    files = {'video': (os.path.basename(video_path), open(video_path, 'rb'), 'video/mp4')}
    
    try:
        print(f"\n🚀 Testing transcode API...")
        response = requests.post(f"{api_url}/transcode", data=form_data, files=files)
        
        files['video'][1].close()  # Close file handle
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            print(f"✅ Task created successfully!")
            print(f"   Task ID: {task_id}")
            print(f"   Status: {result.get('status', 'unknown')}")
            
            # Wait a bit and check status
            print(f"\n⏳ Waiting 5 seconds...")
            time.sleep(5)
            
            status_response = requests.get(f"{api_url}/tasks/{task_id}")
            if status_response.status_code == 200:
                status_result = status_response.json()
                print(f"📊 Task Status: {status_result.get('status', 'unknown')}")
                
                if status_result.get('status') == 'FAILED':
                    print(f"   Error: {status_result.get('error_message', 'No details')}")
                    return False
                elif status_result.get('status') == 'COMPLETED':
                    outputs = status_result.get('outputs', {})
                    print(f"   ✅ Completed with {len(outputs)} outputs!")
                    
            return True
        else:
            print(f"❌ Failed to create task: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        if 'files' in locals() and files.get('video') and files['video'][1]:
            files['video'][1].close()
        return False

if __name__ == "__main__":
    success = test_s3_fix_locally()
    if success:
        print(f"\n🎉 S3 Fix test passed!")
    else:
        print(f"\n❌ S3 Fix test failed!")