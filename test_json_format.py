#!/usr/bin/env python3
"""
Test JSON format compatibility between UI and API
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def test_json_format():
    """Test if UI JSON format matches API expectations"""
    
    print("🧪 Testing JSON Format Compatibility")
    print("=" * 50)
    
    # UI face detection config (from frontend)
    ui_face_config = {
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
    
    print("📝 UI Face Detection Config:")
    print(json.dumps(ui_face_config, indent=2))
    
    try:
        # Import API schemas to validate
        from models.schemas import FaceDetectionConfig, TranscodeConfig
        
        print("\n🔍 Validating against API schema...")
        
        # Validate face detection config
        face_config = FaceDetectionConfig(**ui_face_config)
        print("✅ Face detection config validation passed")
        
        # Test complete transcode config
        complete_config = {
            "profiles": [
                {
                    "id_profile": "test_720p",
                    "output_type": "video",
                    "video_config": {
                        "codec": "libx264",
                        "max_width": 1280,
                        "max_height": 720,
                        "bitrate": "2M"
                    }
                }
            ],
            "s3_output_config": {
                "base_path": "test-outputs",
                "folder_structure": "{task_id}/{profile_id}"
            },
            "face_detection_config": ui_face_config
        }
        
        transcode_config = TranscodeConfig(**complete_config)
        print("✅ Complete transcode config validation passed")
        
        # Test serialization/deserialization
        serialized = transcode_config.model_dump()
        print("✅ Serialization successful")
        
        # Verify face detection is properly included
        if serialized.get('face_detection_config'):
            fd_config = serialized['face_detection_config']
            print(f"✅ Face detection included: enabled={fd_config.get('enabled')}")
            print(f"✅ Similarity threshold: {fd_config.get('similarity_threshold')}")
            print(f"✅ Save faces: {fd_config.get('save_faces')}")
        else:
            print("❌ Face detection config not found in serialized data")
            
        return True
        
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False

def test_api_compatibility():
    """Test API parameter compatibility"""
    
    print("\n🧪 Testing API Parameter Compatibility")
    print("=" * 50)
    
    try:
        # Test different config combinations
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
        
        from models.schemas import FaceDetectionConfig
        
        for test_case in test_configs:
            name = test_case["name"]
            config = test_case["config"]
            
            print(f"\n📝 Testing {name} configuration...")
            
            # Validate
            face_config = FaceDetectionConfig(**config)
            print(f"✅ {name} config validation passed")
            
            # Test JSON serialization/deserialization
            json_str = json.dumps(config)
            parsed_config = json.loads(json_str)
            face_config_from_json = FaceDetectionConfig(**parsed_config)
            print(f"✅ {name} JSON round-trip successful")
            
        return True
        
    except Exception as e:
        print(f"❌ API compatibility test failed: {e}")
        return False

def main():
    """Run all compatibility tests"""
    print("🚀 JSON Format Compatibility Test Suite")
    print("=" * 60)
    
    tests = [
        ("JSON Format Validation", test_json_format),
        ("API Parameter Compatibility", test_api_compatibility)
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
        print("🎉 All compatibility tests passed! UI and API are compatible.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()