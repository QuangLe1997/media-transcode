#!/usr/bin/env python3
"""
Delete all old templates and create new v2 format templates.
"""

import json
import requests
import os
import sys

def clear_all_templates():
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

def create_v2_templates():
    """Create new v2 format templates."""
    api_url = 'http://192.168.0.234:8087'
    
    # V2 format templates - with 'config' field
    v2_templates = {
        "quick_web_video": {
            "name": "Quick Web Video",
            "description": "Fast web-ready MP4 conversion with good quality",
            "config": [
                {
                    "id_profile": "quick_web_video",
                    "input_type": "video",
                    "config": {
                        "output_format": "mp4",
                        "width": 1280,
                        "height": 720,
                        "codec": "h264",
                        "crf": 23,
                        "mp4_preset": "fast",
                        "profile": "main",
                        "level": "4.0",
                        "pixel_format": "yuv420p",
                        "audio_codec": "aac",
                        "audio_bitrate": "128k",
                        "hardware_accel": True,
                        "verbose": False
                    }
                }
            ]
        },
        "quick_mobile_preview": {
            "name": "Quick Mobile Preview",
            "description": "Fast mobile-friendly WebP animation",
            "config": [
                {
                    "id_profile": "quick_mobile_preview",
                    "input_type": "video",
                    "config": {
                        "output_format": "webp",
                        "width": 640,
                        "height": 360,
                        "quality": 80,
                        "fps": 15,
                        "duration": 5.0,
                        "start_time": 1.0,
                        "animated": True,
                        "lossless": False,
                        "method": 2,
                        "preset": "default",
                        "loop": 0,
                        "target_size": 500,
                        "verbose": False
                    }
                }
            ]
        },
        "quick_thumbnail": {
            "name": "Quick Thumbnail",
            "description": "Fast thumbnail extraction from video",
            "config": [
                {
                    "id_profile": "quick_thumbnail",
                    "input_type": "video",
                    "config": {
                        "output_format": "jpeg",
                        "width": 400,
                        "height": 300,
                        "quality": 85,
                        "start_time": 3.0,
                        "jpeg_quality": 85,
                        "optimize": True,
                        "verbose": False
                    }
                }
            ]
        },
        "quick_gif_preview": {
            "name": "Quick GIF Preview", 
            "description": "Fast GIF creation for social media",
            "config": [
                {
                    "id_profile": "quick_gif_preview",
                    "input_type": "video",
                    "config": {
                        "output_format": "gif",
                        "width": 480,
                        "height": 270,
                        "fps": 12,
                        "duration": 3.0,
                        "start_time": 2.0,
                        "quality": 75,
                        "loop": 0,
                        "verbose": False
                    }
                }
            ]
        },
        "quick_hd_video": {
            "name": "Quick HD Video",
            "description": "High quality MP4 for archival",
            "config": [
                {
                    "id_profile": "quick_hd_video",
                    "input_type": "video",
                    "config": {
                        "output_format": "mp4",
                        "codec": "h264",
                        "crf": 18,
                        "mp4_preset": "slow",
                        "profile": "high",
                        "level": "5.1",
                        "pixel_format": "yuv420p",
                        "audio_codec": "aac",
                        "audio_bitrate": "192k",
                        "hardware_accel": True,
                        "verbose": False
                    }
                }
            ]
        },
        "social_square_video": {
            "name": "Social Square Video",
            "description": "1080x1080 square video for social media",
            "config": [
                {
                    "id_profile": "social_square_video",
                    "input_type": "video",
                    "config": {
                        "output_format": "mp4",
                        "width": 1080,
                        "height": 1080,
                        "codec": "h264",
                        "crf": 25,
                        "mp4_preset": "fast",
                        "profile": "main",
                        "pixel_format": "yuv420p",
                        "audio_codec": "aac",
                        "audio_bitrate": "128k",
                        "verbose": False
                    }
                }
            ]
        },
        "mobile_optimized_video": {
            "name": "Mobile Optimized Video",
            "description": "Small file size for mobile devices",
            "config": [
                {
                    "id_profile": "mobile_optimized_video",
                    "input_type": "video",
                    "config": {
                        "output_format": "mp4",
                        "width": 854,
                        "height": 480,
                        "codec": "h264",
                        "crf": 28,
                        "mp4_preset": "fast",
                        "profile": "baseline",
                        "level": "3.0",
                        "pixel_format": "yuv420p",
                        "audio_codec": "aac",
                        "audio_bitrate": "64k",
                        "hardware_accel": True,
                        "verbose": False
                    }
                }
            ]
        },
        "complete_web_package": {
            "name": "Complete Web Package",
            "description": "MP4 video + WebP preview + Thumbnail in one job",
            "config": [
                {
                    "id_profile": "web_mp4_main",
                    "input_type": "video",
                    "config": {
                        "output_format": "mp4",
                        "width": 1280,
                        "height": 720,
                        "codec": "h264",
                        "crf": 23,
                        "mp4_preset": "fast",
                        "profile": "main",
                        "pixel_format": "yuv420p",
                        "audio_codec": "aac",
                        "audio_bitrate": "128k",
                        "hardware_accel": True,
                        "verbose": False
                    }
                },
                {
                    "id_profile": "web_preview_webp",
                    "input_type": "video",
                    "config": {
                        "output_format": "webp",
                        "width": 640,
                        "height": 360,
                        "quality": 80,
                        "fps": 15,
                        "duration": 4.0,
                        "start_time": 1.0,
                        "animated": True,
                        "loop": 0,
                        "target_size": 500,
                        "verbose": False
                    }
                },
                {
                    "id_profile": "web_thumbnail_jpeg",
                    "input_type": "video",
                    "config": {
                        "output_format": "jpeg",
                        "width": 400,
                        "height": 300,
                        "quality": 85,
                        "start_time": 2.0,
                        "jpeg_quality": 85,
                        "optimize": True,
                        "verbose": False
                    }
                }
            ]
        },
        "image_optimization": {
            "name": "Image Optimization",
            "description": "JPEG optimization for web galleries",
            "config": [
                {
                    "id_profile": "image_optimize_jpeg",
                    "input_type": "image",
                    "config": {
                        "output_format": "jpeg",
                        "width": 1200,
                        "height": 800,
                        "quality": 85,
                        "jpeg_quality": 85,
                        "optimize": True,
                        "progressive": True,
                        "auto_filter": True,
                        "verbose": False
                    }
                }
            ]
        }
    }
    
    print(f"🚀 Creating {len(v2_templates)} V2 format templates...")
    
    success_count = 0
    error_count = 0
    
    for template_key, template_info in v2_templates.items():
        try:
            # Prepare API payload
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
                result = response.json()
                print(f"✅ Created: {template_info['name']} (ID: {result.get('template_id', 'N/A')})")
                success_count += 1
            else:
                print(f"❌ Failed: {template_info['name']} - {response.status_code}: {response.text}")
                error_count += 1
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Connection error - is the API server running at {api_url}?")
            return False
        except Exception as e:
            print(f"❌ Error creating {template_info['name']}: {str(e)}")
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
            print(f"\n🔍 Final Verification - Found {len(templates)} V2 templates:")
            for template in templates:
                print(f"   - {template.get('name', 'Unknown')} (ID: {template.get('template_id', 'N/A')})")
                # Check if it has v2 format
                config = template.get('config', [])
                if config and isinstance(config, list) and len(config) > 0:
                    first_profile = config[0]
                    has_config_field = 'config' in first_profile
                    print(f"     Format: {'V2 ✅' if has_config_field else 'V1 ❌'}")
            return templates
        else:
            print(f"❌ Failed to verify: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Error verifying: {e}")
        return []

if __name__ == "__main__":
    print("🎬 V2 Template Recreation Tool")
    print("Server: http://192.168.0.234:8087")
    print("=" * 50)
    
    # Step 1: Clear existing templates
    print("\n1. Clearing all existing templates...")
    deleted_count = clear_all_templates()
    
    # Step 2: Create new V2 templates
    print("\n2. Creating new V2 format templates...")
    success = create_v2_templates()
    
    # Step 3: Verify final state
    print("\n3. Final verification...")
    final_templates = verify_final_templates()
    
    if success and len(final_templates) > 0:
        print(f"\n🎉 Success!")
        print(f"   🗑️  Deleted {deleted_count} old templates")
        print(f"   ✅ Created {len(final_templates)} new V2 templates")
        print(f"   📍 Ready for API calls with V2 format!")
    else:
        print(f"\n⚠️  Process completed with issues.")