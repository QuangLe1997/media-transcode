#!/usr/bin/env python3
"""
Script to load quick transcode templates into the database via API.
Run this script to populate the config templates with ready-to-use profiles.
"""

import json
import requests
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_templates():
    """Load quick templates from JSON file and create them via API."""
    
    # Default API URL - can be changed via environment variable
    api_url = os.getenv('TRANSCODE_API_URL', 'http://localhost:8000')
    
    # Load templates from JSON file
    template_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'quick_transcode_templates.json')
    
    try:
        with open(template_file, 'r') as f:
            template_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Template file not found: {template_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in template file: {e}")
        return False
    
    templates = template_data.get('templates', {})
    print(f"🚀 Loading {len(templates)} quick templates...")
    
    success_count = 0
    error_count = 0
    
    for template_key, template_info in templates.items():
        try:
            # Prepare the API request
            payload = {
                'name': template_info['name'],
                'config': template_info['config']
            }
            
            # Add description if available
            if 'description' in template_info:
                payload['description'] = template_info['description']
            
            # Make API request
            response = requests.post(f"{api_url}/config-templates", json=payload)
            
            if response.status_code == 200:
                print(f"✅ Created template: {template_info['name']}")
                success_count += 1
            else:
                print(f"❌ Failed to create {template_info['name']}: {response.status_code} - {response.text}")
                error_count += 1
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error - is the API server running at {api_url}?")
            error_count += 1
        except Exception as e:
            print(f"❌ Error creating {template_info['name']}: {str(e)}")
            error_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   ✅ Successfully created: {success_count}")
    print(f"   ❌ Failed: {error_count}")
    print(f"   📁 Total templates: {len(templates)}")
    
    return error_count == 0

def check_existing_templates():
    """Check what templates already exist."""
    api_url = os.getenv('TRANSCODE_API_URL', 'http://localhost:8000')
    
    try:
        response = requests.get(f"{api_url}/config-templates")
        if response.status_code == 200:
            existing = response.json().get('templates', [])
            print(f"📋 Found {len(existing)} existing templates:")
            for template in existing[:5]:  # Show first 5
                print(f"   - {template.get('name', 'Unknown')}")
            if len(existing) > 5:
                print(f"   ... and {len(existing) - 5} more")
            return existing
        else:
            print(f"❌ Failed to fetch existing templates: {response.status_code}")
            return []
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error - is the API server running at {api_url}?")
        return []
    except Exception as e:
        print(f"❌ Error checking existing templates: {str(e)}")
        return []

if __name__ == "__main__":
    print("🎬 Quick Transcode Template Loader")
    print("=" * 40)
    
    # Check if API server is accessible
    print("\n1. Checking existing templates...")
    existing_templates = check_existing_templates()
    
    # Load new templates
    print("\n2. Loading quick templates...")
    success = load_templates()
    
    if success:
        print("\n🎉 All templates loaded successfully!")
        print("   You can now use these templates in the web interface.")
    else:
        print("\n⚠️  Some templates failed to load.")
        print("   Check the API server and try again.")
    
    print("\n💡 Usage tips:")
    print("   - Templates are optimized for fast processing")
    print("   - Use 'Quick Web Video' for general web content")
    print("   - Use 'Quick Mobile Preview' for social media")
    print("   - Use 'Quick Thumbnail' for video previews")