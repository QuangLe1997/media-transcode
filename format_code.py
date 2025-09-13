#!/usr/bin/env python3
"""
Code formatting script using Black
Run this script to automatically format all Python files in the src directory
"""

import subprocess
import sys
from pathlib import Path


def run_black():
    """Run Black formatter on src directory"""
    try:
        result = subprocess.run(
            ["black", "src/"], 
            check=True, 
            capture_output=True, 
            text=True
        )
        print("✅ Black formatting completed successfully!")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Black formatting failed: {e}")
        if e.stderr:
            print(e.stderr)
        return False
    except FileNotFoundError:
        print("❌ Black is not installed. Install it with: pip install black")
        return False


def check_black_compliance():
    """Check if all files are Black compliant without making changes"""
    try:
        result = subprocess.run(
            ["black", "--check", "src/"], 
            check=True, 
            capture_output=True, 
            text=True
        )
        print("✅ All files are already properly formatted!")
        return True
    except subprocess.CalledProcessError:
        print("⚠️  Some files need formatting. Run without --check flag to format them.")
        return False
    except FileNotFoundError:
        print("❌ Black is not installed. Install it with: pip install black")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Format Python code with Black")
    parser.add_argument(
        "--check", 
        action="store_true",
        help="Check if files are formatted without making changes"
    )
    
    args = parser.parse_args()
    
    if args.check:
        success = check_black_compliance()
    else:
        success = run_black()
    
    sys.exit(0 if success else 1)