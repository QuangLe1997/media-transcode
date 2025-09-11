#!/usr/bin/env python3
"""
Test script to verify face detection API integration
"""

import requests
import json
import os
import tempfile
from pathlib import Path

# API endpoint
API_URL = "http://localhost:8087"  # Change if different

def create_test_image():
    """Create a simple test image for upload"""
    import cv2
    import numpy as np
    
    # Create a simple test image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[100:380, 100:540] = [100, 150, 200]  # Background
    img[200:280, 270:370] = [200, 150, 100]  # Face area
    img[220:230, 290:300] = [255, 255, 255]  # Left eye
    img[220:230, 340:350] = [255, 255, 255]  # Right eye
    img[250:260, 310:330] = [100, 100, 100]  # Nose
    img[270:275, 300:340] = [150, 100, 100]  # Mouth
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    cv2.imwrite(temp_file.name, img)
    return temp_file.name

def test_face_detection_api():
    """Test the face detection API functionality"""
    
    print("🧪 Testing Face Detection API Integration")
    print("=" * 50)
    
    try:
        # Create test image
        print("📸 Creating test image...")
        test_image_path = create_test_image()
        print(f"✅ Test image created: {test_image_path}")
        
        # Prepare form data
        print("\n📝 Preparing API request...")
        
        # Profiles configuration
        profiles = [
            {
                "id_profile": "test_video",
                "output_type": "video",
                "video_config": {
                    "codec": "libx264",
                    "max_width": 1280,
                    "max_height": 720,
                    "bitrate": "2M"
                }
            }
        ]
        
        # S3 output configuration
        s3_config = {
            "base_path": "test-outputs",
            "folder_structure": "{task_id}/{profile_id}"
        }
        
        # Face detection configuration (matching UI format)
        face_detection_config = {
            "enabled": True,
            "similarity_threshold": 0.6,
            "min_faces_in_group": 3,
            "sample_interval": 5,
            "face_detector_size": "640x640",
            "face_detector_score_threshold": 0.5,
            "save_faces": True,
            "avatar_size": 112,
            "avatar_quality": 85
        }
        
        # Prepare multipart form data
        files = {
            'video': ('test_image.jpg', open(test_image_path, 'rb'), 'image/jpeg')
        }
        
        data = {
            'profiles': json.dumps(profiles),
            's3_output_config': json.dumps(s3_config),
            'face_detection_config': json.dumps(face_detection_config)
        }
        
        print(f"📊 Face detection config: {json.dumps(face_detection_config, indent=2)}")
        
        # Make API request
        print(f"\n🚀 Making API request to {API_URL}/transcode...")
        response = requests.post(
            f"{API_URL}/transcode",
            files=files,
            data=data,
            timeout=30
        )
        
        print(f"📈 Response status: {response.status_code}")
        print(f"📋 Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ API Response: {json.dumps(result, indent=2)}")
            
            task_id = result.get('task_id')
            if task_id:
                print(f"\n🔍 Task created successfully: {task_id}")
                
                # Check task status
                print(f"\n📊 Checking task status...")
                status_response = requests.get(f"{API_URL}/tasks/{task_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"📋 Task status: {json.dumps(status_data, indent=2)}")
                    
                    # Check if face detection is properly configured
                    face_detection_status = status_data.get('face_detection_status')
                    if face_detection_status:
                        print(f"✅ Face detection status: {face_detection_status}")
                    else:
                        print("❌ Face detection status not found in response")
                        
                else:
                    print(f"❌ Failed to get task status: {status_response.status_code}")
                    
            return True
            
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"📋 Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the API server is running on localhost:8087")
        return False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    finally:
        # Cleanup
        if 'test_image_path' in locals():
            try:
                os.unlink(test_image_path)
                print(f"🧹 Cleaned up test image: {test_image_path}")
            except:
                pass

def test_face_detection_validation():
    """Test face detection config validation"""
    
    print("\n🧪 Testing Face Detection Config Validation")
    print("=" * 50)
    
    try:
        # Test invalid face detection config
        print("📝 Testing invalid face detection config...")
        
        profiles = [{"id_profile": "test", "output_type": "video", "video_config": {"codec": "libx264"}}]
        s3_config = {"base_path": "test"}
        
        # Invalid face detection config (missing required fields)
        invalid_face_config = {
            "enabled": True,
            "invalid_field": "should_fail"
        }
        
        data = {
            'media_url': 'https://example.com/test.mp4',
            'profiles': json.dumps(profiles),
            's3_output_config': json.dumps(s3_config),
            'face_detection_config': json.dumps(invalid_face_config)
        }
        
        response = requests.post(f"{API_URL}/transcode", data=data)
        
        if response.status_code == 400:
            print("✅ API properly validated invalid config")
            print(f"📋 Error response: {response.text}")
        else:
            print(f"❌ API should have rejected invalid config, got: {response.status_code}")
            
        return True
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def test_face_detection_disabled():
    """Test API when face detection is disabled"""
    
    print("\n🧪 Testing Face Detection Disabled")
    print("=" * 50)
    
    try:
        profiles = [{"id_profile": "test", "output_type": "video", "video_config": {"codec": "libx264"}}]
        s3_config = {"base_path": "test"}
        
        # Face detection disabled
        face_config = {
            "enabled": False,
            "similarity_threshold": 0.6
        }
        
        data = {
            'media_url': 'https://example.com/test.mp4',
            'profiles': json.dumps(profiles),
            's3_output_config': json.dumps(s3_config),
            'face_detection_config': json.dumps(face_config)
        }
        
        response = requests.post(f"{API_URL}/transcode", data=data)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API accepted disabled face detection config")
            print(f"📋 Task ID: {result.get('task_id')}")
        else:
            print(f"❌ API rejected disabled face detection config: {response.status_code}")
            print(f"📋 Error: {response.text}")
            
        return True
        
    except Exception as e:
        print(f"❌ Disabled test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Face Detection API Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Face Detection API Integration", test_face_detection_api),
        ("Face Detection Config Validation", test_face_detection_validation),
        ("Face Detection Disabled", test_face_detection_disabled)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Face detection API is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the API implementation.")

if __name__ == "__main__":
    main()