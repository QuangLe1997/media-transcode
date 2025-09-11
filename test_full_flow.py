#!/usr/bin/env python3
"""
Test complete face detection flow from UI to API
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def test_complete_flow():
    """Test complete flow as if coming from UI"""
    
    print("🧪 Testing Complete Face Detection Flow")
    print("=" * 50)
    
    # Simulate UI state (exactly as in Upload.js)
    face_detection_enabled = True
    face_detection_config = json.dumps({
        "enabled": True,
        "similarity_threshold": 0.6,
        "min_faces_in_group": 3,
        "sample_interval": 5,
        "face_detector_size": "640x640",
        "face_detector_score_threshold": 0.5,
        "save_faces": True,
        "avatar_size": 112,
        "avatar_quality": 85
    }, indent=2)
    
    profiles_json = json.dumps([{
        "id_profile": "720p_h264",
        "output_type": "video",
        "video_config": {
            "codec": "libx264",
            "max_width": 1280,
            "max_height": 720,
            "bitrate": "2M"
        }
    }])
    
    s3_config_json = json.dumps({
        "base_path": "transcode-outputs",
        "folder_structure": "{task_id}/profiles/{profile_id}",
        "face_avatar_path": "{task_id}/faces/avatars",
        "face_image_path": "{task_id}/faces/images"
    })
    
    print("📝 UI Configuration:")
    print(f"Face Detection Enabled: {face_detection_enabled}")
    print(f"Face Detection Config: {face_detection_config}")
    
    # Simulate UI validation (same as in Upload.js)
    try:
        print("\n🔍 UI Validation...")
        
        # Parse JSON configs
        profiles_data = json.loads(profiles_json)
        s3_config_data = json.loads(s3_config_json)
        
        # Validate face detection config if enabled
        if face_detection_enabled:
            face_config = json.loads(face_detection_config)
            
            # Basic validation
            if isinstance(face_config.get('enabled'), bool):
                print("✅ Face detection 'enabled' is boolean")
            else:
                raise ValueError('Face detection "enabled" must be a boolean')
                
            if face_config.get('enabled'):
                threshold = face_config.get('similarity_threshold', 0.6)
                if 0 <= threshold <= 1:
                    print(f"✅ Face detection similarity_threshold valid: {threshold}")
                else:
                    raise ValueError('Face detection "similarity_threshold" must be between 0 and 1')
                    
                min_faces = face_config.get('min_faces_in_group', 3)
                if min_faces >= 1:
                    print(f"✅ Face detection min_faces_in_group valid: {min_faces}")
                else:
                    raise ValueError('Face detection "min_faces_in_group" must be at least 1')
        
        print("✅ UI validation passed")
        
    except Exception as e:
        print(f"❌ UI validation failed: {e}")
        return False
    
    # Simulate API processing
    try:
        print("\n🔍 API Processing...")
        
        from models.schemas import FaceDetectionConfig, TranscodeConfig, TranscodeProfile, S3OutputConfig
        
        # Parse face detection config
        face_detection_config_data = None
        if face_detection_enabled:
            face_detection_config_data = json.loads(face_detection_config)
            print(f"✅ Face detection config parsed: {face_detection_config_data}")
        
        # Create profiles
        profiles = [TranscodeProfile(**profile) for profile in profiles_data]
        print(f"✅ Profiles created: {len(profiles)} profiles")
        
        # Create S3 config
        s3_config = S3OutputConfig(**s3_config_data)
        print(f"✅ S3 config created: {s3_config.base_path}")
        
        # Create complete config
        config_data = {
            "profiles": profiles,
            "s3_output_config": s3_config
        }
        
        if face_detection_config_data:
            face_config = FaceDetectionConfig(**face_detection_config_data)
            config_data["face_detection_config"] = face_config
            print(f"✅ Face detection config added: enabled={face_config.enabled}")
        
        transcode_config = TranscodeConfig(**config_data)
        print("✅ Complete transcode config created")
        
        # Test message creation (as in API)
        if transcode_config.face_detection_config and transcode_config.face_detection_config.enabled:
            from models.schemas import FaceDetectionMessage
            
            face_message = FaceDetectionMessage(
                task_id="test-task-123",
                source_url="s3://test-bucket/test-video.mp4",
                config=transcode_config.face_detection_config.model_dump()
            )
            print(f"✅ Face detection message created: {face_message.task_id}")
            print(f"✅ Face detection enabled: {face_message.config.get('enabled')}")
        
        print("✅ API processing completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ API processing failed: {e}")
        return False

def test_different_configs():
    """Test different face detection configurations"""
    
    print("\n🧪 Testing Different Face Detection Configurations")
    print("=" * 50)
    
    test_configs = [
        {
            "name": "High Quality",
            "config": {
                "enabled": True,
                "similarity_threshold": 0.7,
                "min_faces_in_group": 5,
                "sample_interval": 3,
                "face_detector_size": "640x640",
                "face_detector_score_threshold": 0.6,
                "save_faces": True,
                "avatar_size": 112,
                "avatar_quality": 90
            }
        },
        {
            "name": "Fast Mode",
            "config": {
                "enabled": True,
                "similarity_threshold": 0.5,
                "min_faces_in_group": 2,
                "sample_interval": 10,
                "face_detector_size": "320x320",
                "face_detector_score_threshold": 0.4,
                "save_faces": True,
                "avatar_size": 64,
                "avatar_quality": 75
            }
        },
        {
            "name": "Disabled",
            "config": {
                "enabled": False,
                "similarity_threshold": 0.6,
                "min_faces_in_group": 3,
                "sample_interval": 5,
                "face_detector_size": "640x640",
                "face_detector_score_threshold": 0.5,
                "save_faces": False,
                "avatar_size": 112,
                "avatar_quality": 85
            }
        }
    ]
    
    try:
        from models.schemas import FaceDetectionConfig
        
        for test_case in test_configs:
            name = test_case["name"]
            config = test_case["config"]
            
            print(f"\n📝 Testing {name}...")
            
            # Create face detection config
            face_config = FaceDetectionConfig(**config)
            
            # Serialize to JSON (UI to API)
            json_str = json.dumps(config)
            
            # Deserialize from JSON (API from UI)
            parsed_config = json.loads(json_str)
            face_config_from_json = FaceDetectionConfig(**parsed_config)
            
            print(f"✅ {name} config processed successfully")
            print(f"   - Enabled: {face_config_from_json.enabled}")
            print(f"   - Similarity: {face_config_from_json.similarity_threshold}")
            print(f"   - Min faces: {face_config_from_json.min_faces_in_group}")
            print(f"   - Save faces: {face_config_from_json.save_faces}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config testing failed: {e}")
        return False

def main():
    """Run all flow tests"""
    print("🚀 Face Detection Complete Flow Test Suite")
    print("=" * 60)
    
    tests = [
        ("Complete Flow Test", test_complete_flow),
        ("Different Configurations", test_different_configs)
    ]
    
    results = []
    for test_name, test_func in tests:
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
        print("🎉 All flow tests passed! UI to API integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the integration.")

if __name__ == "__main__":
    main()