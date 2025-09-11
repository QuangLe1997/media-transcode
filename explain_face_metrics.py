#!/usr/bin/env python3
"""
Face Detection Metrics Explanation Tool
"""

def explain_face_metrics(metrics):
    """
    Provide human-readable explanations of face detection metrics
    
    Args:
        metrics (dict): Face detection metrics dictionary
        
    Returns:
        dict: Explanations for each metric
    """
    explanations = {}
    
    # Distance metrics (face similarity)
    if 'mean_distance' in metrics:
        distance = metrics['mean_distance']
        if distance < 0.01:
            explanations['face_similarity'] = "Very consistent face appearance (likely same person)"
        elif distance < 0.1:
            explanations['face_similarity'] = "Moderately consistent face appearance"
        else:
            explanations['face_similarity'] = "Variable face appearance (possibly different people)"
    
    # Age variance
    if 'age_variance' in metrics:
        age_var = metrics['age_variance']
        if age_var == 0:
            explanations['age_consistency'] = "Very consistent age prediction"
        elif age_var < 5:
            explanations['age_consistency'] = "Consistent age prediction"
        else:
            explanations['age_consistency'] = "Variable age prediction (lighting or angle changes)"
    
    # Temporal spread
    if 'temporal_spread' in metrics:
        spread = metrics['temporal_spread']
        if spread == 0:
            explanations['temporal_presence'] = "Face appears in single frame only"
        elif spread < 30:
            explanations['temporal_presence'] = f"Face appears across {spread} frames (brief appearance)"
        else:
            explanations['temporal_presence'] = f"Face appears across {spread} frames (sustained presence)"
    
    # Pose analysis
    if 'pose_avg_yaw' in metrics:
        yaw = metrics['pose_avg_yaw']
        if abs(yaw) < 10:
            explanations['head_direction'] = "Looking straight ahead"
        elif yaw < -10:
            explanations['head_direction'] = f"Head turned left ({abs(yaw):.1f}°)"
        else:
            explanations['head_direction'] = f"Head turned right ({yaw:.1f}°)"
    
    if 'pose_avg_pitch' in metrics:
        pitch = metrics['pose_avg_pitch']
        if abs(pitch) < 10:
            explanations['head_tilt'] = "Looking straight ahead"
        elif pitch < -10:
            explanations['head_tilt'] = f"Looking down ({abs(pitch):.1f}°)"
        else:
            explanations['head_tilt'] = f"Looking up ({pitch:.1f}°)"
    
    # Frontality score
    if 'pose_avg_frontality' in metrics:
        frontality = metrics['pose_avg_frontality']
        if frontality > 0.8:
            explanations['face_angle'] = "Excellent frontal view"
        elif frontality > 0.6:
            explanations['face_angle'] = "Good frontal view"
        elif frontality > 0.4:
            explanations['face_angle'] = "Moderate frontal view"
        elif frontality > 0.2:
            explanations['face_angle'] = "Poor frontal view (partially turned away)"
        else:
            explanations['face_angle'] = "Very poor frontal view (mostly profile)"
    
    # Overall quality
    if 'pose_quality_score' in metrics:
        quality = metrics['pose_quality_score']
        if quality > 0.8:
            explanations['overall_quality'] = "Excellent quality for face recognition"
        elif quality > 0.6:
            explanations['overall_quality'] = "Good quality for face recognition"
        elif quality > 0.4:
            explanations['overall_quality'] = "Moderate quality for face recognition"
        else:
            explanations['overall_quality'] = "Poor quality for face recognition"
    
    # Pose variance (consistency)
    if 'pose_yaw_variance' in metrics and 'pose_pitch_variance' in metrics:
        yaw_var = metrics['pose_yaw_variance']
        pitch_var = metrics['pose_pitch_variance']
        
        if yaw_var == 0 and pitch_var == 0:
            explanations['pose_consistency'] = "Very consistent head pose (single image or stable pose)"
        elif yaw_var < 5 and pitch_var < 5:
            explanations['pose_consistency'] = "Consistent head pose across frames"
        else:
            explanations['pose_consistency'] = "Variable head pose (head movement detected)"
    
    return explanations

def format_explanation(metrics):
    """
    Format metrics explanation for display
    
    Args:
        metrics (dict): Face detection metrics dictionary
        
    Returns:
        str: Formatted explanation text
    """
    explanations = explain_face_metrics(metrics)
    
    output = []
    output.append("=== Face Detection Metrics Explanation ===\n")
    
    for category, explanation in explanations.items():
        category_name = category.replace('_', ' ').title()
        output.append(f"{category_name}: {explanation}")
    
    return "\n".join(output)

# Example usage
if __name__ == "__main__":
    # Example metrics from your question
    example_metrics = {
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
    
    print(format_explanation(example_metrics))
    
    print("\n=== Raw Metrics ===")
    import json
    print(json.dumps(example_metrics, indent=2))