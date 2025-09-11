# Face Detection Metrics Documentation

## Overview
When face detection is enabled and faces are detected, the system provides detailed metrics about the quality and characteristics of detected faces. These metrics help evaluate the reliability and usability of the face detection results.

## Face Detection Results Structure

```json
{
  "face_detection_results": {
    "faces": [
      {
        "name": "face_group_name",
        "index": 0,
        "bounding_box": [x1, y1, x2, y2],
        "detector": 0.95,
        "landmarker": 0.89,
        "gender": 1,
        "age": 25,
        "group_size": 5,
        "metrics": {
          "mean_distance": 1.1920928955078125e-7,
          "std_distance": 0,
          "max_distance": 1.1920928955078125e-7,
          "min_distance": 1.1920928955078125e-7,
          "age_variance": 0,
          "temporal_spread": 0,
          "pose_yaw_variance": 0,
          "pose_pitch_variance": 0,
          "pose_avg_yaw": -21.57,
          "pose_avg_pitch": 48.15,
          "pose_avg_frontality": 0.31,
          "pose_min_frontality": 0.31,
          "pose_max_frontality": 0.31,
          "pose_quality_score": 0.72
        }
      }
    ],
    "is_change_index": false
  }
}
```

## Basic Face Data

### `name`
- **Type**: String
- **Description**: Generated identifier for the face group
- **Example**: `"000001_00"` (frame_000001, group_00)

### `index`
- **Type**: Integer
- **Description**: Sequential index of the face group
- **Range**: 0, 1, 2, etc.

### `bounding_box`
- **Type**: Array of 4 floats
- **Description**: Face location coordinates [x1, y1, x2, y2]
- **Units**: Pixels in original image
- **Example**: `[100.5, 200.3, 300.7, 400.1]`

### `detector`
- **Type**: Float
- **Description**: Face detection confidence score
- **Range**: 0.0 to 1.0
- **Interpretation**: Higher values indicate more confident detection
- **Example**: `0.95` = 95% confidence

### `landmarker`
- **Type**: Float
- **Description**: Facial landmark detection confidence score
- **Range**: 0.0 to 1.0
- **Interpretation**: Higher values indicate more accurate landmark detection
- **Example**: `0.89` = 89% confidence

### `gender`
- **Type**: Integer
- **Description**: Predicted gender
- **Values**: 
  - `0` = Female
  - `1` = Male
- **Example**: `1` = Male

### `age`
- **Type**: Integer
- **Description**: Predicted age in years
- **Range**: Typically 0-100
- **Example**: `25` = 25 years old

### `group_size`
- **Type**: Integer
- **Description**: Number of face instances in this group (for video clustering)
- **Example**: `5` = This face appears in 5 different frames

## Detailed Metrics Explanation

### Distance Metrics (Face Embedding Similarity)

#### `mean_distance`
- **Value**: `1.1920928955078125e-7` (0.0000001192...)
- **Description**: Average cosine distance between face embeddings in the group
- **Interpretation**: 
  - Very small values (close to 0) = faces are very similar
  - Larger values = faces are more different
- **Technical**: Measures consistency of face recognition across frames

#### `std_distance`
- **Value**: `0`
- **Description**: Standard deviation of distances between face embeddings
- **Interpretation**:
  - `0` = All faces in group are identical (single image or very consistent)
  - Higher values = More variation in face appearance across frames

#### `max_distance` / `min_distance`
- **Values**: Both `1.1920928955078125e-7`
- **Description**: Maximum and minimum distances between face embeddings
- **Interpretation**: Since min = max = mean, this indicates a single face instance

### Age Variance

#### `age_variance`
- **Value**: `0`
- **Description**: Variance in predicted age across all faces in the group
- **Interpretation**:
  - `0` = Consistent age prediction (single face or same person)
  - Higher values = Age predictions vary (lighting, angle, or multiple people)

### Temporal Metrics

#### `temporal_spread`
- **Value**: `0`
- **Description**: Time span between first and last appearance of this face
- **Units**: Frame numbers
- **Interpretation**:
  - `0` = Face appears in single frame only
  - Higher values = Face appears across many frames

### Pose Analysis Metrics

#### `pose_yaw_variance` / `pose_pitch_variance`
- **Values**: Both `0`
- **Description**: Variance in head rotation angles
- **Interpretation**:
  - `0` = Consistent head pose (single image or same angle)
  - Higher values = Head moved significantly across frames

#### `pose_avg_yaw`
- **Value**: `-21.57`
- **Description**: Average horizontal head rotation
- **Units**: Degrees
- **Interpretation**:
  - `0°` = Looking straight ahead
  - Negative = Head turned left
  - Positive = Head turned right
  - **Example**: `-21.57°` = Head turned 21.57° to the left

#### `pose_avg_pitch`
- **Value**: `48.15`
- **Description**: Average vertical head rotation
- **Units**: Degrees
- **Interpretation**:
  - `0°` = Looking straight ahead
  - Negative = Looking down
  - Positive = Looking up
  - **Example**: `48.15°` = Head tilted up 48.15°

#### `pose_avg_frontality`
- **Value**: `0.31`
- **Description**: Average frontality score (how directly the face is facing camera)
- **Range**: 0.0 to 1.0
- **Interpretation**:
  - `1.0` = Perfect frontal view
  - `0.0` = Complete profile view
  - **Example**: `0.31` = Partially frontal (face turned away from camera)

#### `pose_min_frontality` / `pose_max_frontality`
- **Values**: Both `0.31`
- **Description**: Minimum and maximum frontality scores
- **Interpretation**: Since min = max = avg, this is a single face instance

### Overall Quality Score

#### `pose_quality_score`
- **Value**: `0.72`
- **Description**: Overall pose quality assessment
- **Range**: 0.0 to 1.0
- **Calculation**: Combines frontality and pose variance
- **Interpretation**:
  - `1.0` = Perfect pose quality (frontal, consistent)
  - `0.0` = Poor pose quality (profile, inconsistent)
  - **Example**: `0.72` = Good quality (reasonably frontal with consistent pose)

## Interpretation Guidelines

### Single Image Results
When processing a single image (like your example):
- All variance metrics will be `0` (std_distance, age_variance, temporal_spread, pose variances)
- Min/max values equal the average values
- `group_size` typically equals the number of detected faces

### Video Results
When processing videos:
- Variance metrics show consistency across frames
- `temporal_spread` shows how long a face appears
- Higher variances may indicate lighting changes, different angles, or multiple people

### Quality Assessment
- **High Quality**: High frontality (>0.7), low pose variance, high detector confidence
- **Medium Quality**: Moderate frontality (0.3-0.7), some pose variation
- **Low Quality**: Low frontality (<0.3), high variance, low confidence scores

## Use Cases

1. **Security Applications**: Use detector confidence and pose quality for access control
2. **Content Analysis**: Use age/gender predictions for demographic analysis
3. **Video Processing**: Use temporal_spread and variances for consistency checking
4. **Face Recognition**: Use distance metrics for identity verification

## Technical Notes

- Face embeddings are 512-dimensional vectors normalized to unit length
- Cosine distance is used for similarity measurement (1 - cosine_similarity)
- Pose angles are calculated using facial landmark geometry
- All metrics are computed from the best representative face in each group