#!/usr/bin/env python3
"""
Script to clear old templates and insert new quick templates via remote API.
"""

import json
import requests
import os
import sys

def clear_existing_templates():
    """Delete all existing templates."""
    api_url = 'http://192.168.0.234:8087'
    
    try:
        # Get all existing templates
        response = requests.get(f"{api_url}/config-templates")
        if response.status_code == 200:
            existing = response.json().get('templates', [])
            print(f"🗑️  Found {len(existing)} existing templates to delete")
            
            for template in existing:
                template_id = template.get('template_id')
                template_name = template.get('name', 'Unknown')
                
                try:
                    delete_response = requests.delete(f"{api_url}/config-templates/{template_id}")
                    if delete_response.status_code == 200:
                        print(f"   ✅ Deleted: {template_name}")
                    else:
                        print(f"   ❌ Failed to delete: {template_name} - {delete_response.status_code}")
                except Exception as e:
                    print(f"   ❌ Error deleting {template_name}: {e}")
            
            return len(existing)
        else:
            print(f"❌ Failed to fetch existing templates: {response.status_code}")
            return 0
    except Exception as e:
        print(f"❌ Error clearing templates: {e}")
        return 0

def load_new_templates():
    """Load new quick templates."""
    api_url = 'http://192.168.0.234:8087'
    
    # Load API compatible templates
    template_file = '/Users/quang/Documents/skl-workspace/transcode/media-transcode/config/api_compatible_templates.json'
    
    try:
        with open(template_file, 'r') as f:
            template_data = json.load(f)
        print(f"📁 Loaded API compatible templates file")
        
        templates = []
        for template_key, template_info in template_data['templates'].items():
            templates.append(template_info)
            
    except Exception as e:
        print(f"❌ Error loading templates: {e}")
        return False
    
    print(f"🚀 Inserting {len(templates)} new templates...")
    
    success_count = 0
    error_count = 0
    
    for template in templates:
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
    
    return error_count == 0

def verify_final_templates():
    """Verify final template state."""
    api_url = 'http://192.168.0.234:8087'
    
    try:
        response = requests.get(f"{api_url}/config-templates")
        if response.status_code == 200:
            result = response.json()
            templates = result.get('templates', [])
            print(f"\n🔍 Final Verification - Found {len(templates)} templates:")
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
    print("🎬 Template Replacement Tool - Remote API")
    print("Server: http://192.168.0.234:8087")
    print("=" * 50)
    
    # Step 1: Clear existing templates
    print("\n1. Clearing existing templates...")
    deleted_count = clear_existing_templates()
    
    # Step 2: Load new templates
    print("\n2. Loading new quick templates...")
    success = load_new_templates()
    
    # Step 3: Verify final state
    print("\n3. Final verification...")
    final_templates = verify_final_templates()
    
    if success and len(final_templates) > 0:
        print(f"\n🎉 Success!")
        print(f"   🗑️  Deleted {deleted_count} old templates")
        print(f"   ✅ Created {len(final_templates)} new templates")
        print(f"   📍 Available at: http://192.168.0.234:8087/config-templates")
    else:
        print(f"\n⚠️  Process completed with issues.")