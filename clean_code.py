#!/usr/bin/env python3
"""
Comprehensive code cleanup script
Automatically fixes imports, removes unused code, and formats everything
"""

import subprocess
import sys
from pathlib import Path


def run_command(command, description=""):
    """Run a command and return success status"""
    try:
        print(f"🔧 {description}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e}")
        if e.stderr:
            print(e.stderr)
        return False


def clean_code(target_dir="src/"):
    """Run comprehensive code cleanup"""
    print("🚀 Starting comprehensive code cleanup...")
    print("=" * 60)
    
    steps = [
        # Step 1: Remove unused imports and variables
        {
            "command": f"autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive {target_dir}",
            "description": "Removing unused imports and variables with autoflake"
        },
        
        # Step 2: Sort and organize imports
        {
            "command": f"isort {target_dir} --profile black --line-length 100",
            "description": "Sorting imports with isort"
        },
        
        # Step 3: Fix PEP8 issues
        {
            "command": f"autopep8 --in-place --aggressive --aggressive --recursive {target_dir}",
            "description": "Fixing PEP8 issues with autopep8"
        },
        
        # Step 4: Final Black formatting
        {
            "command": f"black {target_dir}",
            "description": "Applying Black code formatting"
        }
    ]
    
    success_count = 0
    for i, step in enumerate(steps, 1):
        print(f"\n📍 Step {i}/{len(steps)}: {step['description']}")
        if run_command(step["command"], step["description"]):
            success_count += 1
            print("✅ Success!")
        else:
            print("❌ Failed!")
    
    print("\n" + "=" * 60)
    print(f"🎯 Cleanup completed: {success_count}/{len(steps)} steps successful")
    
    if success_count == len(steps):
        print("🎉 All code cleanup steps completed successfully!")
        return True
    else:
        print("⚠️  Some steps failed. Please check the output above.")
        return False


def check_code_quality(target_dir="src/"):
    """Check code quality with pylint"""
    print("\n🔍 Checking code quality...")
    
    command = f"pylint {target_dir} --disable=missing-module-docstring,missing-class-docstring,missing-function-docstring,invalid-name,duplicate-code"
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout
        
        # Extract score
        if "Your code has been rated at" in output:
            score_line = [line for line in output.split('\n') if "Your code has been rated at" in line][-1]
            print(f"📊 {score_line}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to check code quality: {e}")
        return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean and format Python code automatically")
    parser.add_argument(
        "--target", 
        default="src/",
        help="Target directory to clean (default: src/)"
    )
    parser.add_argument(
        "--check-only", 
        action="store_true",
        help="Only check code quality without making changes"
    )
    
    args = parser.parse_args()
    
    target_dir = args.target
    
    if not Path(target_dir).exists():
        print(f"❌ Target directory '{target_dir}' does not exist")
        sys.exit(1)
    
    if args.check_only:
        success = check_code_quality(target_dir)
    else:
        success = clean_code(target_dir)
        if success:
            check_code_quality(target_dir)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()