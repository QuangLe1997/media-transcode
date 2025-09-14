#!/usr/bin/env python3
"""
Script to insert quick transcode templates into the database via API.
"""

import json
import requests
import os
import sys

def load_templates_to_db():
    """Load API-compatible templates and insert via API."""
    
    api_url = 'http://192.168.0.234:8087'  # Remote server
    
    # Load API compatible templates
    template_file = '/Users/quang/Documents/skl-workspace/transcode/media-transcode/config/api_compatible_templates.json'
    
    all_templates = []
    
    # Load templates
    try:
        with open(template_file, 'r') as f:
            template_data = json.load(f)
        print(f"📁 Loaded API compatible templates file")
        
        for template_key, template_info in template_data['templates'].items():
            all_templates.append(template_info)
            
    except Exception as e:
        print(f"❌ Error loading templates: {e}")
        return False
    
    print(f"🚀 Inserting {len(all_templates)} templates into database...")
    
    success_count = 0
    error_count = 0
    
    for template in all_templates:
        try:
            # Prepare API payload
            payload = {
                'name': template['name'],
                'config': template['config']
            }
            
            # Add description if available
            if 'description' in template:
                payload['description'] = template['description']
            
            # Make API request
            response = requests.post(f"{api_url}/config-templates", json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Created: {template['name']} (ID: {result.get('template_id', 'N/A')})")
                success_count += 1
            else:
                print(f"❌ Failed: {template['name']} - {response.status_code}: {response.text}")
                error_count += 1
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error - is the API server running at {api_url}?")
            return False
        except Exception as e:
            print(f"❌ Error creating {template['name']}: {str(e)}")
            error_count += 1
    
    print(f"\n📊 Summary:")
    print(f"   ✅ Successfully created: {success_count}")
    print(f"   ❌ Failed: {error_count}")
    print(f"   📁 Total templates: {len(all_templates)}")
    
    return error_count == 0

def verify_templates():
    """Verify templates were created by fetching them."""
    api_url = 'http://192.168.0.234:8087'  # Remote server
    
    try:
        response = requests.get(f"{api_url}/config-templates")
        if response.status_code == 200:
            result = response.json()
            templates = result.get('templates', [])
            print(f"\n🔍 Verification - Found {len(templates)} templates in database:")
            for template in templates:
                print(f"   - {template.get('name', 'Unknown')} (ID: {template.get('template_id', 'N/A')})")
            return templates
        else:
            print(f"❌ Failed to verify: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error verifying: {e}")
        return []

if __name__ == "__main__":
    print("🎬 Quick Template Database Loader")
    print("=" * 40)
    
    # Load templates
    success = load_templates_to_db()
    
    if success:
        print("\n🎉 All templates loaded successfully!")
        
        # Verify
        verify_templates()
        
        print("\n💡 Templates are now available at GET /config-templates")
        print("   You can use them in the web interface!")
    else:
        print("\n⚠️ Some templates failed to load.")