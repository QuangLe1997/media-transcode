#!/usr/bin/env python3
"""
End-to-end test for V2 system
Tests the complete flow from API to Worker to Result processing
"""

import json
import requests
import time
import os
import sys
from typing import Dict, List

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

class V2SystemTester:
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        
    def test_webp_conversion_flow(self):
        """Test complete WebP conversion flow"""
        print("🧪 Testing V2 WebP Conversion Flow...")
        
        # 1. Create transcode task with v2 format
        request_data = {
            "media_url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
            "profiles": [
                {
                    "id_profile": "webp_360p_test",
                    "input_type": "video",
                    "output_filename": "test_preview_360p",
                    "config": {
                        "output_format": "webp",
                        "width": 360,
                        "height": None,
                        "quality": 80,
                        "fps": 12,
                        "duration": 5.0,
                        "start_time": 0,
                        "animated": True,
                        "lossless": False,
                        "method": 4,
                        "loop": 0,
                        "verbose": True
                    }
                }
            ],
            "s3_output_config": {
                "bucket": "your-test-bucket",
                "base_path": "v2-test-outputs",
                "folder_structure": "{task_id}/profiles/{profile_id}",
                "cleanup_temp_files": True
            }
        }
        
        response = self._make_api_request("POST", "/transcode", request_data)
        
        if response.status_code != 200:
            print(f"❌ Task creation failed: {response.status_code}")
            print(response.text)
            return False
            
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✅ Task created: {task_id}")
        print(f"   Profiles count: {task_data['profiles_count']}")
        print(f"   Status: {task_data['status']}")
        
        # 2. Monitor task progress
        print("⏳ Monitoring task progress...")
        completed = self._wait_for_task_completion(task_id, timeout=300)
        
        if not completed:
            print(f"❌ Task {task_id} did not complete within timeout")
            return False
            
        # 3. Verify final results
        final_status = self._get_task_status(task_id)
        print(f"✅ Task completed with status: {final_status['status']}")
        
        if final_status["status"] == "completed":
            outputs = final_status.get("outputs", {})
            print(f"   Outputs generated: {len(outputs)}")
            for profile_id, output_list in outputs.items():
                print(f"     {profile_id}: {len(output_list) if output_list else 0} files")
                if output_list:
                    for output in output_list:
                        if isinstance(output, dict) and 'url' in output:
                            print(f"       URL: {output['url']}")
                            metadata = output.get('metadata', {})
                            if metadata:
                                print(f"       Metadata: {metadata}")
            return True
        else:
            print(f"❌ Task failed: {final_status.get('error_message', 'Unknown error')}")
            return False
    
    def test_multiple_formats_flow(self):
        """Test conversion to multiple formats (WebP, JPG, MP4)"""
        print("🧪 Testing V2 Multiple Formats Flow...")
        
        request_data = {
            "media_url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
            "profiles": [
                {
                    "id_profile": "webp_preview",
                    "input_type": "video",
                    "output_filename": "preview",
                    "config": {
                        "output_format": "webp",
                        "width": 480,
                        "quality": 85,
                        "fps": 15,
                        "duration": 3.0,
                        "animated": True
                    }
                },
                {
                    "id_profile": "jpg_thumbnail",
                    "input_type": "video",
                    "output_filename": "thumbnail",
                    "config": {
                        "output_format": "jpg",
                        "width": 300,
                        "height": 300,
                        "jpeg_quality": 90,
                        "optimize": True
                    }
                },
                {
                    "id_profile": "mp4_compressed",
                    "input_type": "video",
                    "output_filename": "compressed",
                    "config": {
                        "output_format": "mp4",
                        "width": 854,
                        "height": 480,
                        "fps": 24,
                        "codec": "h264",
                        "crf": 28,
                        "mp4_preset": "fast"
                    }
                }
            ],
            "s3_output_config": {
                "bucket": "your-test-bucket",
                "base_path": "v2-multi-format-test",
                "cleanup_temp_files": True
            }
        }
        
        response = self._make_api_request("POST", "/transcode", request_data)
        
        if response.status_code != 200:
            print(f"❌ Multi-format task creation failed: {response.status_code}")
            return False
            
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✅ Multi-format task created: {task_id}")
        print(f"   Expected profiles: {task_data['profiles_count']}")
        
        # Monitor progress
        print("⏳ Monitoring multi-format task...")
        completed = self._wait_for_task_completion(task_id, timeout=600)
        
        if not completed:
            print(f"❌ Multi-format task did not complete")
            return False
            
        # Check results
        final_status = self._get_task_status(task_id)
        print(f"✅ Multi-format task status: {final_status['status']}")
        
        if final_status["status"] == "completed":
            outputs = final_status.get("outputs", {})
            expected_profiles = ["webp_preview", "jpg_thumbnail", "mp4_compressed"]
            
            success = True
            for profile_id in expected_profiles:
                if profile_id in outputs and outputs[profile_id]:
                    print(f"   ✅ {profile_id}: Generated")
                else:
                    print(f"   ❌ {profile_id}: Missing")
                    success = False
                    
            return success
        else:
            print(f"❌ Multi-format task failed: {final_status.get('error_message')}")
            return False
    
    def test_error_handling(self):
        """Test error handling with invalid configurations"""
        print("🧪 Testing V2 Error Handling...")
        
        # Test 1: V1 format should be rejected
        print("   Testing V1 format rejection...")
        v1_request = {
            "media_url": "https://example.com/test.mp4",
            "profiles": [
                {
                    "id_profile": "old_profile",
                    "output_type": "webp",  # V1 format
                    "webp_config": {"width": 360}  # V1 format
                }
            ],
            "s3_output_config": {"bucket": "test"}
        }
        
        response = self._make_api_request("POST", "/transcode", v1_request)
        if response.status_code == 400 and "missing 'config' field" in response.text:
            print("   ✅ V1 format correctly rejected")
        else:
            print(f"   ❌ V1 format not rejected properly: {response.status_code}")
            return False
        
        # Test 2: Invalid output format
        print("   Testing invalid output format...")
        invalid_format_request = {
            "media_url": "https://example.com/test.mp4",
            "profiles": [
                {
                    "id_profile": "invalid_format",
                    "config": {
                        "output_format": "gif",  # Not supported in v2
                        "width": 360
                    }
                }
            ],
            "s3_output_config": {"bucket": "test"}
        }
        
        response = self._make_api_request("POST", "/transcode", invalid_format_request)
        if response.status_code == 400:
            print("   ✅ Invalid format correctly rejected")
        else:
            print(f"   ❌ Invalid format not rejected: {response.status_code}")
            return False
            
        # Test 3: Missing required fields
        print("   Testing missing required fields...")
        missing_config_request = {
            "media_url": "https://example.com/test.mp4",
            "profiles": [
                {
                    "id_profile": "no_config"
                    # Missing 'config' field
                }
            ],
            "s3_output_config": {"bucket": "test"}
        }
        
        response = self._make_api_request("POST", "/transcode", missing_config_request)
        if response.status_code == 400:
            print("   ✅ Missing config field correctly rejected")
            return True
        else:
            print(f"   ❌ Missing config not rejected: {response.status_code}")
            return False
    
    def test_task_management_endpoints(self):
        """Test task management endpoints with v2 data"""
        print("🧪 Testing V2 Task Management...")
        
        # 1. Create a simple task
        request_data = {
            "media_url": "https://sample-videos.com/zip/10/mp4/SampleVideo_360x240_1mb.mp4",
            "profiles": [
                {
                    "id_profile": "management_test",
                    "config": {
                        "output_format": "webp",
                        "width": 240,
                        "quality": 70,
                        "duration": 2.0,
                        "animated": True
                    }
                }
            ],
            "s3_output_config": {
                "bucket": "test-bucket",
                "base_path": "management-test"
            }
        }
        
        response = self._make_api_request("POST", "/transcode", request_data)
        
        if response.status_code != 200:
            print(f"❌ Management test task creation failed")
            return False
            
        task_id = response.json()["task_id"]
        print(f"✅ Management test task created: {task_id}")
        
        # 2. Test task status endpoint
        status = self._get_task_status(task_id)
        if status:
            print(f"   ✅ Task status retrieved: {status['status']}")
            print(f"      Profiles count: {status.get('profiles_count', 0)}")
            print(f"      Expected profiles: {status.get('expected_profiles', 0)}")
        else:
            print("   ❌ Failed to get task status")
            return False
        
        # 3. Test task list endpoint
        list_response = self._make_api_request("GET", "/tasks?limit=5")
        if list_response.status_code == 200:
            tasks = list_response.json()["tasks"]
            print(f"   ✅ Task list retrieved: {len(tasks)} tasks")
            
            # Find our task
            our_task = next((t for t in tasks if t["task_id"] == task_id), None)
            if our_task:
                print(f"      Our task found in list with status: {our_task['status']}")
            else:
                print("      Our task not found in list")
        else:
            print("   ❌ Failed to get task list")
            return False
        
        # 4. Test task result endpoint
        result_response = self._make_api_request("GET", f"/task/{task_id}/result")
        if result_response.status_code == 200:
            result = result_response.json()
            print(f"   ✅ Task result retrieved")
            print(f"      Expected profiles: {result.get('expected_profiles', 0)}")
            print(f"      Completed profiles: {result.get('completed_profiles', 0)}")
        else:
            print("   ❌ Failed to get task result")
            return False
            
        return True
    
    def _make_api_request(self, method: str, endpoint: str, data: Dict = None):
        """Make API request with proper formatting"""
        url = f"{self.api_base_url}{endpoint}"
        
        if method == "POST" and data:
            # Convert to form data format for API
            form_data = {}
            if "media_url" in data:
                form_data["media_url"] = data["media_url"]
            if "profiles" in data:
                form_data["profiles"] = json.dumps(data["profiles"])
            if "s3_output_config" in data:
                form_data["s3_output_config"] = json.dumps(data["s3_output_config"])
            if "face_detection_config" in data:
                form_data["face_detection_config"] = json.dumps(data["face_detection_config"])
                
            return requests.post(url, data=form_data)
        else:
            return requests.get(url)
    
    def _get_task_status(self, task_id: str) -> Dict:
        """Get task status"""
        response = self._make_api_request("GET", f"/task/{task_id}")
        if response.status_code == 200:
            return response.json()
        return None
    
    def _wait_for_task_completion(self, task_id: str, timeout: int = 300) -> bool:
        """Wait for task to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self._get_task_status(task_id)
            
            if not status:
                print(f"   ❌ Could not get status for task {task_id}")
                return False
                
            current_status = status["status"]
            progress = status.get("completion_percentage", 0)
            
            print(f"   📊 Status: {current_status}, Progress: {progress}%")
            
            if current_status in ["completed", "failed"]:
                return current_status == "completed"
                
            time.sleep(5)  # Check every 5 seconds
            
        return False


def main():
    """Run all V2 system tests"""
    print("🚀 Starting V2 System End-to-End Tests")
    print("=" * 60)
    
    tester = V2SystemTester()
    
    # Check if API is running
    try:
        health_response = requests.get(f"{tester.api_base_url}/health")
        if health_response.status_code != 200:
            print("❌ API is not running or not healthy")
            print("   Please start the transcode service first")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API")
        print("   Please start the transcode service first")
        return False
    
    print("✅ API is running and healthy")
    print()
    
    # Run tests
    tests = [
        ("Error Handling", tester.test_error_handling),
        ("Task Management", tester.test_task_management_endpoints),
        ("WebP Conversion", tester.test_webp_conversion_flow),
        ("Multiple Formats", tester.test_multiple_formats_flow),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
        
        print()
    
    # Summary
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All V2 system tests passed!")
        return True
    else:
        print("💥 Some tests failed. Check the logs above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)