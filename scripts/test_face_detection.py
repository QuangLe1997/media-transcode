#!/usr/bin/env python3
"""
Test script for face detection worker
Demonstrates automatic model download and health checking
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_model_download():
    """Test automatic model downloading"""
    logger.info("🧪 Testing model download functionality...")
    
    try:
        from services.model_downloader import get_model_downloader
        
        models_dir = project_root / "models_faces"
        downloader = get_model_downloader(str(models_dir))
        
        # Test downloading all models
        results = downloader.download_all_models(force_download=False)
        
        print("\n📊 Model Download Results:")
        for model_name, success in results.items():
            status = "✅" if success else "❌"
            print(f"{status} {model_name}")
        
        return all(results.values())
        
    except Exception as e:
        logger.error(f"❌ Model download test failed: {e}")
        return False

def test_face_detection_worker():
    """Test face detection worker initialization and health check"""
    logger.info("🧪 Testing face detection worker...")
    
    try:
        from consumer.face_detect_worker import FaceDetectionWorker
        
        # Initialize worker (this will auto-download models)
        worker = FaceDetectionWorker()
        
        # Perform health check
        health_status = worker.health_check()
        
        print("\n🏥 Worker Health Check:")
        print(f"Status: {health_status['status']}")
        print(f"Timestamp: {health_status['timestamp']}")
        print(f"Temp Directory: {health_status['temp_dir']}")
        
        print("\n🤖 Models Status:")
        for model_name, model_info in health_status['models'].items():
            status = "✅" if model_info['available'] and model_info['valid'] else "❌"
            print(f"{status} {model_name}: available={model_info['available']}, valid={model_info['valid']}")
        
        print("\n📦 Dependencies Status:")
        for dep_name, dep_info in health_status['dependencies'].items():
            status = "✅" if dep_info['available'] else "❌"
            print(f"{status} {dep_name}: {dep_info['version']}")
        
        return health_status['status'] in ['healthy', 'degraded']
        
    except Exception as e:
        logger.error(f"❌ Worker test failed: {e}")
        return False

def test_face_detection_processing():
    """Test face detection processing with a sample image"""
    logger.info("🧪 Testing face detection processing...")
    
    try:
        from services.face_detect_service import FaceProcessor
        import cv2
        import numpy as np
        
        # Create a simple test image with a face-like pattern
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[200:280, 270:370] = [200, 150, 100]  # Face area
        test_image[220:230, 290:300] = [255, 255, 255]  # Left eye
        test_image[220:230, 340:350] = [255, 255, 255]  # Right eye
        test_image[250:260, 310:330] = [100, 100, 100]  # Nose
        test_image[270:275, 300:340] = [150, 100, 100]  # Mouth
        
        # Save test image
        test_image_path = project_root / "test_face_image.jpg"
        cv2.imwrite(str(test_image_path), test_image)
        
        # Initialize processor
        processor_config = {
            "face_detector_size": "640x640",
            "face_detector_score_threshold": 0.3,  # Lower threshold for test
            "avatar_size": 112,
            "output_path": str(project_root / "test_output")
        }
        
        processor = FaceProcessor(processor_config)
        
        # Process image
        result = processor.process_image(str(test_image_path))
        
        print("\n👤 Face Detection Results:")
        print(f"Change Index: {result['is_change_index']}")
        print(f"Faces Found: {len(result['faces'])}")
        
        for i, face in enumerate(result['faces']):
            print(f"  Face {i+1}:")
            print(f"    Bounding Box: {face['bounding_box']}")
            print(f"    Detector Score: {face['detector']:.3f}")
            print(f"    Gender: {face['gender']}")
            print(f"    Age: {face['age']}")
        
        # Cleanup
        if test_image_path.exists():
            test_image_path.unlink()
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Face detection processing test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Face Detection Worker Test Suite")
    print("=" * 50)
    
    tests = [
        ("Model Download", test_model_download),
        ("Worker Initialization", test_face_detection_worker),
        ("Face Detection Processing", test_face_detection_processing),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name}...")
        success = test_func()
        results.append((test_name, success))
        
        if success:
            logger.info(f"✅ {test_name} passed")
        else:
            logger.error(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Face detection worker is ready.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the logs.")
        return 1

if __name__ == "__main__":
    sys.exit(main())