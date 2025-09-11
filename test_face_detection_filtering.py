#!/usr/bin/env python3
"""
Test script to verify face detection result filtering
"""

import json
from services.callback_service import CallbackService
from db.models import TranscodeTaskDB

# Mock task with face detection results
mock_task = TranscodeTaskDB()
mock_task.task_id = "test-task-123"
mock_task.face_detection_results = {
    "faces": [
        {
            "name": "face_000001_00",
            "index": 0,
            "bounding_box": [100.5, 200.3, 300.7, 400.1],
            "detector": 0.95,
            "landmarker": 0.89,
            "gender": 1,
            "age": 25,
            "group_size": 1,
            "avatar": "base64_encoded_image_data_here...",  # This should be filtered out
            "normed_embedding": [0.1, 0.2, 0.3, 0.4],  # This should be filtered out
            "metrics": {
                "mean_distance": 1.1920928955078125e-7,
                "std_distance": 0,
                "max_distance": 1.1920928955078125e-7,
                "min_distance": 1.1920928955078125e-7,
                "age_variance": 0,
                "temporal_spread": 0,
                "pose_yaw_variance": 0,
                "pose_pitch_variance": 0,
                "pose_avg_yaw": -21.5737842859835,
                "pose_avg_pitch": 48.14617762924372,
                "pose_avg_frontality": 0.3123495428535533,
                "pose_min_frontality": 0.3123495428535533,
                "pose_max_frontality": 0.3123495428535533,
                "pose_quality_score": 0.7249398171414213
            }
        }
    ],
    "is_change_index": False
}

# Test the filtering
def test_face_detection_filtering():
    print("Testing face detection result filtering...")
    
    # Prepare callback data
    callback_data = CallbackService._prepare_callback_data(mock_task)
    
    # Check that face detection results are present
    assert "face_detection_results" in callback_data
    assert callback_data["face_detection_results"] is not None
    
    # Check that faces are present
    faces = callback_data["face_detection_results"]["faces"]
    assert len(faces) == 1
    
    face = faces[0]
    print("\nFiltered face data:")
    print(json.dumps(face, indent=2))
    
    # Verify that sensitive data is filtered out
    assert "avatar" not in face, "Avatar should be filtered out from callback"
    assert "normed_embedding" not in face, "Normed embedding should be filtered out from callback"
    
    # Verify that important data is preserved
    assert "name" in face
    assert "index" in face
    assert "bounding_box" in face
    assert "detector" in face
    assert "landmarker" in face
    assert "gender" in face
    assert "age" in face
    assert "metrics" in face
    
    # Verify metrics are complete
    metrics = face["metrics"]
    expected_metrics = [
        "mean_distance", "std_distance", "max_distance", "min_distance",
        "age_variance", "temporal_spread", "pose_yaw_variance", "pose_pitch_variance",
        "pose_avg_yaw", "pose_avg_pitch", "pose_avg_frontality", 
        "pose_min_frontality", "pose_max_frontality", "pose_quality_score"
    ]
    
    for metric in expected_metrics:
        assert metric in metrics, f"Metric '{metric}' should be present"
    
    print("\n✅ All tests passed!")
    print("✅ Avatar and normed_embedding are filtered out")
    print("✅ All important face data is preserved")
    print("✅ All metrics are included")

if __name__ == "__main__":
    test_face_detection_filtering()