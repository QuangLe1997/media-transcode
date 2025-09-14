#!/usr/bin/env python3
"""
Convert v1 format profiles to v2 format for API compatibility.
"""

def convert_v1_to_v2(v1_profile):
    """Convert a v1 profile to v2 format."""
    v2_profile = {
        "id_profile": v1_profile["id_profile"],
        "input_type": v1_profile.get("input_type", "video")
    }
    
    # Convert config based on output_type
    output_type = v1_profile["output_type"]
    config = {}
    
    if output_type == "video":
        # Extract from video_config
        video_config = v1_profile.get("video_config", {})
        config = {
            "output_format": "mp4",
            "codec": video_config.get("codec", "libx264"),
            "width": video_config.get("max_width"),
            "height": video_config.get("max_height"), 
            "crf": video_config.get("crf"),
            "mp4_preset": video_config.get("preset", "fast"),
            "profile": video_config.get("profile", "main"),
            "level": video_config.get("level"),
            "pixel_format": video_config.get("pixel_format", "yuv420p"),
            "audio_codec": video_config.get("audio_codec"),
            "audio_bitrate": video_config.get("audio_bitrate"),
            "fps": video_config.get("fps"),
            "duration": video_config.get("duration"),
            "start_time": video_config.get("start_time", 0),
            "verbose": False
        }
        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}
        
    elif output_type == "webp":
        # Extract from webp_config
        webp_config = v1_profile.get("webp_config", {})
        config = {
            "output_format": "webp",
            "width": webp_config.get("width"),
            "height": webp_config.get("height"),
            "quality": webp_config.get("quality", 80),
            "fps": webp_config.get("fps", 15),
            "duration": webp_config.get("duration", 5.0),
            "start_time": webp_config.get("start_time", 1.0),
            "animated": webp_config.get("animated", True),
            "lossless": webp_config.get("lossless", False),
            "method": webp_config.get("method", 2),
            "preset": webp_config.get("preset", "default"),
            "loop": webp_config.get("loop", 0),
            "verbose": False
        }
        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}
        
    elif output_type == "image":
        # Extract from image_config
        image_config = v1_profile.get("image_config", {})
        config = {
            "output_format": image_config.get("format", "jpeg"),
            "width": image_config.get("max_width"),
            "height": image_config.get("max_height"),
            "quality": image_config.get("quality", 85),
            "start_time": image_config.get("start_time", 3.0),
            "jpeg_quality": image_config.get("quality", 85),
            "optimize": image_config.get("progressive", True),
            "progressive": image_config.get("progressive", True),
            "verbose": False
        }
        # Remove None values  
        config = {k: v for k, v in config.items() if v is not None}
        
    elif output_type == "gif":
        # Extract from gif_config
        gif_config = v1_profile.get("gif_config", {})
        config = {
            "output_format": "gif",
            "width": gif_config.get("width"),
            "height": gif_config.get("height"),
            "fps": gif_config.get("fps", 12),
            "duration": gif_config.get("duration", 3.0),
            "start_time": gif_config.get("start_time", 2.0),
            "quality": gif_config.get("quality", 75),
            "loop": gif_config.get("loop", 0),
            "verbose": False
        }
        # Remove None values
        config = {k: v for k, v in config.items() if v is not None}
    
    v2_profile["config"] = config
    return v2_profile

def test_conversion():
    """Test the conversion with sample data."""
    v1_sample = {
        "id_profile": "quick_web_video",
        "output_type": "video",
        "input_type": "video",
        "video_config": {
            "codec": "libx264",
            "max_width": 1280,
            "max_height": 720,
            "crf": 23,
            "preset": "fast",
            "profile": "main",
            "level": "4.0",
            "pixel_format": "yuv420p",
            "audio_codec": "aac",
            "audio_bitrate": "128k"
        }
    }
    
    v2_result = convert_v1_to_v2(v1_sample)
    
    print("🔄 V1 to V2 Conversion Test")
    print("=" * 40)
    print("V1 Input:")
    print(json.dumps(v1_sample, indent=2))
    print("\nV2 Output:")
    print(json.dumps(v2_result, indent=2))

if __name__ == "__main__":
    import json
    test_conversion()