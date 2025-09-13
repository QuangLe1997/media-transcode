#!/usr/bin/env python3
"""
Test runner for V2 system
Runs unit tests and end-to-end tests
"""

import subprocess
import sys
import os

def run_unit_tests():
    """Run unit tests for v2 system"""
    print("🧪 Running V2 Unit Tests...")
    print("=" * 50)
    
    # Run API tests
    print("Testing V2 API...")
    result_api = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/test_api_v2.py", 
        "-v", "--tb=short"
    ], cwd=os.getcwd())
    
    # Run Worker tests
    print("\nTesting V2 Workers...")
    result_worker = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/test_worker_v2.py", 
        "-v", "--tb=short"
    ], cwd=os.getcwd())
    
    return result_api.returncode == 0 and result_worker.returncode == 0

def run_integration_tests():
    """Run integration tests"""
    print("\n🔗 Running V2 Integration Tests...")
    print("=" * 50)
    
    result = subprocess.run([
        sys.executable, "test_v2_system.py"
    ], cwd=os.getcwd())
    
    return result.returncode == 0

def main():
    """Run all tests"""
    print("🚀 V2 SYSTEM TEST RUNNER")
    print("=" * 60)
    
    # Check dependencies
    try:
        import pytest
    except ImportError:
        print("❌ pytest is required. Install with: pip install pytest")
        return False
    
    # Run unit tests
    unit_tests_passed = run_unit_tests()
    
    if not unit_tests_passed:
        print("\n❌ Unit tests failed. Fix issues before running integration tests.")
        return False
    
    print("\n✅ Unit tests passed!")
    
    # Ask if user wants to run integration tests
    print("\n" + "=" * 60)
    response = input("Run integration tests? (requires running API service) [y/N]: ")
    
    if response.lower() in ['y', 'yes']:
        integration_passed = run_integration_tests()
        
        if integration_passed:
            print("\n🎉 ALL TESTS PASSED!")
            print("V2 system is working correctly.")
            return True
        else:
            print("\n💥 Integration tests failed.")
            return False
    else:
        print("\nSkipping integration tests.")
        print("To run them manually: python test_v2_system.py")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)