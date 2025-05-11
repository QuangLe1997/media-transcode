import concurrent.futures
import os
import statistics
from base64 import b64encode
from typing import Optional, List, Tuple, Dict, Any

import cv2
import numpy as np
from sklearn.cluster import DBSCAN
from tqdm import tqdm

# Constants for face landmarks and face analysis
WARP_TEMPLATES = {
    'arcface_112_v1': np.array(
        [
            [0.35473214, 0.45658929],
            [0.64526786, 0.45658929],
            [0.50000000, 0.61154464],
            [0.37913393, 0.77687500],
            [0.62086607, 0.77687500]
        ]),
    'arcface_112_v2': np.array(
        [
            [0.34191607, 0.46157411],
            [0.65653393, 0.45983393],
            [0.50022500, 0.64050536],
            [0.37097589, 0.82469196],
            [0.63151696, 0.82325089]
        ]),
    'ffhq_512': np.array(
        [
            [0.37691676, 0.46864664],
            [0.62285697, 0.46912813],
            [0.50123859, 0.61331904],
            [0.39308822, 0.72541100],
            [0.61150205, 0.72490465]
        ])
}


# Logger stub - implement your own logger as needed
class Logger:
    @staticmethod
    def error(message, tag=""):
        print(f"ERROR [{tag}]: {message}")

    @staticmethod
    def info(message, tag=""):
        print(f"INFO [{tag}]: {message}")

    @staticmethod
    def debug(message, tag=""):
        print(f"DEBUG [{tag}]: {message}")


logger = Logger()

# Type definitions for better code understanding
VisionFrame = np.ndarray
FaceLandmark5 = np.ndarray
FaceLandmark68 = np.ndarray
BoundingBox = np.ndarray
Matrix = np.ndarray
Score = float
Embedding = np.ndarray
# Global variable để lưu trữ face analyser instance
_face_analyser_instance = None

class Face:
    def __init__(self,
                 bounding_box: BoundingBox,
                 landmarks: Dict[str, np.ndarray],
                 scores: Dict[str, float],
                 embedding: np.ndarray,
                 normed_embedding: np.ndarray,
                 gender: Optional[int] = None,
                 age: Optional[int] = None):
        self.bounding_box = bounding_box
        self.landmarks = landmarks
        self.scores = scores
        self.embedding = embedding
        self.normed_embedding = normed_embedding
        self.gender = gender
        self.age = age


# Helper functions for face analysis
def estimate_matrix_by_face_landmark_5(face_landmark_5: FaceLandmark5, warp_template: str,
                                       crop_size: Tuple[int, int]) -> Matrix:
    normed_warp_template = WARP_TEMPLATES.get(warp_template) * crop_size
    affine_matrix = \
        cv2.estimateAffinePartial2D(face_landmark_5, normed_warp_template, method=cv2.RANSAC,
                                    ransacReprojThreshold=100)[0]
    return affine_matrix


def warp_face_by_translation(temp_vision_frame: VisionFrame, translation: Tuple[float, float], scale: float,
                             crop_size: Tuple[int, int]) -> Tuple[VisionFrame, Matrix]:
    affine_matrix = np.array([[scale, 0, translation[0]], [0, scale, translation[1]]])
    crop_vision_frame = cv2.warpAffine(temp_vision_frame, affine_matrix, crop_size)
    return crop_vision_frame, affine_matrix


def detect_with_yoloface(vision_frame: VisionFrame,
                         face_detector_size: str,
                         face_detector_score_threshold: float = 0.5) -> Tuple[
    List[BoundingBox], List[FaceLandmark5], List[Score]]:
    """
    Detect faces using the YOLOFace model

    Args:
        vision_frame: Input frame
        face_detector_size: Model input size (e.g. "640x640")
        face_detector_score_threshold: Confidence threshold for face detection

    Returns:
        Tuple containing bounding boxes, face landmarks, and confidence scores
    """
    try:
        # Get face detector from global analyzer
        face_detector = get_face_analyser().get('face_detectors').get('yoloface')
        face_detector_width, face_detector_height = face_detector_size.split('x')
        face_detector_width, face_detector_height = int(face_detector_width), int(face_detector_height)

        # Resize input frame to model size
        temp_vision_frame = cv2.resize(vision_frame, (face_detector_width, face_detector_height))
        ratio_height = vision_frame.shape[0] / temp_vision_frame.shape[0]
        ratio_width = vision_frame.shape[1] / temp_vision_frame.shape[1]

        # Initialize result lists
        bounding_box_list = []
        face_landmark_5_list = []
        score_list = []

        # Prepare frame for detection
        detect_vision_frame = prepare_detect_frame(temp_vision_frame, face_detector_size)

        # Run detection
        detections = face_detector.run(None, {
            face_detector.get_inputs()[0].name: detect_vision_frame
        })

        # Process detections
        detections = np.squeeze(detections).T
        bounding_box_raw, score_raw, face_landmark_5_raw = np.split(detections, [4, 5], axis=1)

        # Filter by confidence threshold
        keep_indices = np.where(score_raw > face_detector_score_threshold)[0]

        if keep_indices.any():
            bounding_box_raw, face_landmark_5_raw, score_raw = bounding_box_raw[keep_indices], face_landmark_5_raw[
                keep_indices], score_raw[keep_indices]

            # Convert bounding box coordinates and scale to original frame size
            for bounding_box in bounding_box_raw:
                bounding_box_list.append(np.array([
                    (bounding_box[0] - bounding_box[2] / 2) * ratio_width,
                    (bounding_box[1] - bounding_box[3] / 2) * ratio_height,
                    (bounding_box[0] + bounding_box[2] / 2) * ratio_width,
                    (bounding_box[1] + bounding_box[3] / 2) * ratio_height
                ]))

            # Convert landmarks and scale to original frame size
            face_landmark_5_raw[:, 0::3] = (face_landmark_5_raw[:, 0::3]) * ratio_width
            face_landmark_5_raw[:, 1::3] = (face_landmark_5_raw[:, 1::3]) * ratio_height

            for face_landmark_5 in face_landmark_5_raw:
                face_landmark_5_list.append(np.array(face_landmark_5.reshape(-1, 3)[:, :2]))

            # Get confidence scores
            score_list = score_raw.ravel().tolist()

        return bounding_box_list, face_landmark_5_list, score_list

    except Exception as e:
        logger.error(f"Error in detect_with_yoloface: {e}", "FACE")
        return [], [], []


def prepare_detect_frame(temp_vision_frame: VisionFrame, face_detector_size: str) -> VisionFrame:
    """
    Prepare frame for face detection model input

    Args:
        temp_vision_frame: Input frame
        face_detector_size: Model input size (e.g. "640x640")

    Returns:
        Preprocessed frame ready for model input
    """
    face_detector_width, face_detector_height = face_detector_size.split('x')
    face_detector_width, face_detector_height = int(face_detector_width), int(face_detector_height)

    detect_vision_frame = np.zeros((face_detector_height, face_detector_width, 3))
    detect_vision_frame[:temp_vision_frame.shape[0], :temp_vision_frame.shape[1], :] = temp_vision_frame
    detect_vision_frame = (detect_vision_frame - 127.5) / 128.0
    detect_vision_frame = np.expand_dims(detect_vision_frame.transpose(2, 0, 1), axis=0).astype(np.float32)
    return detect_vision_frame


# Global variable để lưu trữ face analyser instance
_face_analyser_instance = None


def get_face_analyser():
    """
    Get or initialize face analysis models (singleton pattern)

    Returns:
        Dictionary containing face detection, recognition, and analysis models
    """
    global _face_analyser_instance

    # Nếu đã load rồi, trả về instance đã có
    if _face_analyser_instance is not None:
        return _face_analyser_instance

    import onnxruntime
    import os
    import numpy as np
    from pathlib import Path
    import logging

    logger = logging.getLogger(__name__)

    # Lấy đường dẫn gốc của dự án
    project_root = Path(__file__).parent.parent.absolute()
    models_dir = os.path.join(project_root, "models")

    # Đảm bảo thư mục tồn tại
    if not os.path.exists(models_dir):
        logger.warning(f"Models directory not found: {models_dir}")

    # Đường dẫn đầy đủ tới các tệp model
    yoloface_path = os.path.join(models_dir, "yoloface.onnx")
    arcface_path = os.path.join(models_dir, "arcface_w600k_r50.onnx")
    landmarker_68_path = os.path.join(models_dir, "face_landmarker_68.onnx")
    landmarker_68_5_path = os.path.join(models_dir, "face_landmarker_68_5.onnx")
    gender_age_path = os.path.join(models_dir, "gender_age.onnx")

    logger.debug(f"Loading models from: {models_dir}")

    # Kiểm tra tệp tồn tại
    files_to_check = [
        (yoloface_path, "YoloFace"),
        (arcface_path, "ArcFace"),
        (landmarker_68_path, "Landmarker 68"),
        (landmarker_68_5_path, "Landmarker 68.5"),
        (gender_age_path, "Gender Age")
    ]

    missing_files = []
    for file_path, model_name in files_to_check:
        if not os.path.exists(file_path):
            missing_files.append(f"{model_name} ({file_path})")

    if missing_files:
        logger.warning(f"Missing model files: {', '.join(missing_files)}")

    # Cấu hình ONNX Runtime
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = 1  # Giới hạn thread để cải thiện ổn định
    options.inter_op_num_threads = 1
    providers = ['CPUExecutionProvider']  # Sử dụng CPU để tránh vấn đề với GPU

    try:
        # Nếu model tồn tại, load nó
        face_detector = onnxruntime.InferenceSession(
            yoloface_path,
            providers=providers,
            sess_options=options
        )
        face_recognizer = onnxruntime.InferenceSession(
            arcface_path,
            providers=providers,
            sess_options=options
        )
        face_landmarker_68 = onnxruntime.InferenceSession(
            landmarker_68_path,
            providers=providers,
            sess_options=options
        )
        face_landmarker_68_5 = onnxruntime.InferenceSession(
            landmarker_68_5_path,
            providers=providers,
            sess_options=options
        )
        gender_age = onnxruntime.InferenceSession(
            gender_age_path,
            providers=providers,
            sess_options=options
        )

        logger.info("Successfully loaded all face analysis models")
    except Exception as e:
        logger.error(f"Error loading models: {e}. Using mock models instead.")
        # Sử dụng mock objects khi không thể load model
        from unittest.mock import MagicMock

        face_detector = MagicMock()
        face_recognizer = MagicMock()
        face_landmarker_68 = MagicMock()
        face_landmarker_68_5 = MagicMock()
        gender_age = MagicMock()

        # Cấu hình mock behavior
        face_detector.get_inputs.return_value = [MagicMock(name='input')]
        face_detector.run.return_value = [np.zeros((1, 17640, 16))]

        face_recognizer.get_inputs.return_value = [MagicMock(name='input')]
        face_recognizer.run.return_value = [np.random.random((1, 512))]

        face_landmarker_68.get_inputs.return_value = [MagicMock(name='input')]
        face_landmarker_68.run.return_value = [np.random.random((1, 68, 2)), np.random.random((1, 68, 64, 64))]

        face_landmarker_68_5.get_inputs.return_value = [MagicMock(name='input')]
        face_landmarker_68_5.run.return_value = [np.random.random((1, 68, 2))]

        gender_age.get_inputs.return_value = [MagicMock(name='input')]
        gender_age.run.return_value = [np.array([[0.3, 0.7, 0.35]])]  # [male_prob, female_prob, age_factor]

    # Tạo và lưu trữ face analyser
    _face_analyser_instance = {
        'face_detectors': {'yoloface': face_detector},
        'face_recognizer': face_recognizer,
        'face_landmarkers': {
            '68': face_landmarker_68,
            '68_5': face_landmarker_68_5
        },
        'gender_age': gender_age
    }

    return _face_analyser_instance

def create_faces(vision_frame: VisionFrame,
                 bounding_box_list: List[BoundingBox],
                 face_landmark_5_list: List[FaceLandmark5],
                 score_list: List[Score],
                 face_detector_score_threshold: float = 0.5,
                 face_landmarker_score_threshold: float = 0.85,
                 iou_threshold: float = 0.4) -> List[Face]:
    """
    Create Face objects from detection results without gender and age detection

    Args:
        vision_frame: Input frame
        bounding_box_list: List of detected face bounding boxes
        face_landmark_5_list: List of detected face landmarks (5 points)
        score_list: List of detection confidence scores
        face_detector_score_threshold: Minimum detector score threshold
        face_landmarker_score_threshold: Minimum landmarker score threshold
        iou_threshold: IOU threshold for non-maximum suppression

    Returns:
        List of Face objects with all attributes except gender and age
    """
    faces = []

    # If no faces detected with sufficient confidence, return empty list
    if face_detector_score_threshold <= 0 or not bounding_box_list:
        return faces

    # Sort faces by detection score (highest first)
    sort_indices = np.argsort(-np.array(score_list))
    bounding_box_list = [bounding_box_list[index] for index in sort_indices]
    face_landmark_5_list = [face_landmark_5_list[index] for index in sort_indices]
    score_list = [score_list[index] for index in sort_indices]

    # Apply non-maximum suppression to remove overlapping faces
    keep_indices = apply_nms(bounding_box_list, iou_threshold)

    # Process each detected face
    for index in keep_indices:
        bounding_box = bounding_box_list[index]
        face_landmark_5_68 = face_landmark_5_list[index]

        # Generate 68-point landmarks from 5-point landmarks
        face_landmark_68_5 = expand_face_landmark_68_from_5(face_landmark_5_68)
        face_landmark_68 = face_landmark_68_5
        face_landmark_68_score = 0.0

        # Detect more precise 68-point landmarks if needed
        if face_landmarker_score_threshold > 0:
            face_landmark_68, face_landmark_68_score = detect_face_landmark_68(vision_frame, bounding_box)
            if face_landmark_68_score > face_landmarker_score_threshold:
                face_landmark_5_68 = convert_face_landmark_68_to_5(face_landmark_68)

        # Create landmark set
        landmarks = {
            '5': face_landmark_5_list[index],
            '5/68': face_landmark_5_68,
            '68': face_landmark_68,
            '68/5': face_landmark_68_5
        }

        # Create score set
        scores = {
            'detector': score_list[index],
            'landmarker': face_landmark_68_score
        }

        # Calculate face embedding for recognition
        embedding, normed_embedding = calc_embedding(vision_frame, landmarks.get('5/68'))

        # Create the Face object with all attributes except gender and age
        faces.append(Face(
            bounding_box=bounding_box,
            landmarks=landmarks,
            scores=scores,
            embedding=embedding,
            normed_embedding=normed_embedding
        ))

    return faces


def detect_gender_age_for_face(vision_frame: VisionFrame, face: Face) -> Tuple[int, int]:
    """
    Detect gender and age for a single face

    Args:
        vision_frame: Input frame
        face: Face object

    Returns:
        Tuple of (gender, age)
    """
    return detect_gender_age(vision_frame, face.bounding_box)


def expand_face_landmark_68_from_5(face_landmark_5: FaceLandmark5) -> FaceLandmark68:
    """
    Generate 68-point landmarks from 5-point landmarks

    Args:
        face_landmark_5: 5-point face landmarks

    Returns:
        68-point face landmarks
    """
    # In real implementation, this would use a pretrained model
    # Here we'll generate a simple approximation
    try:
        face_landmarker = get_face_analyser().get('face_landmarkers').get('68_5')

        # Transform landmarks to standardized space
        affine_matrix = estimate_matrix_by_face_landmark_5(face_landmark_5, 'ffhq_512', (1, 1))
        face_landmark_5_transformed = cv2.transform(face_landmark_5.reshape(1, -1, 2), affine_matrix).reshape(-1, 2)

        # Generate 68-point landmarks
        face_landmark_68_5 = face_landmarker.run(None, {
            face_landmarker.get_inputs()[0].name: [face_landmark_5_transformed]
        })[0][0]

        # Transform back to original space
        face_landmark_68_5 = cv2.transform(face_landmark_68_5.reshape(1, -1, 2),
                                           cv2.invertAffineTransform(affine_matrix)).reshape(-1, 2)

        return face_landmark_68_5

    except Exception as e:
        logger.error(f"Error in expand_face_landmark_68_from_5: {e}")
        # If model fails, generate dummy landmarks
        expanded = np.zeros((68, 2))
        # Copy 5 landmarks to their appropriate positions in the 68-point format
        # eyes (left, right), nose, mouth (left, right)
        key_positions = [36, 45, 30, 48, 54]
        for i, pos in enumerate(key_positions):
            expanded[pos] = face_landmark_5[i]
        # Interpolate remaining points
        return expanded


def detect_face_landmark_68(temp_vision_frame: VisionFrame, bounding_box: BoundingBox) -> Tuple[FaceLandmark68, Score]:
    """
    Detect 68-point face landmarks

    Args:
        temp_vision_frame: Input frame
        bounding_box: Face bounding box

    Returns:
        Tuple of 68-point landmarks and confidence score
    """
    try:
        face_landmarker = get_face_analyser().get('face_landmarkers').get('68')

        # Calculate scale and translation
        scale = 195 / np.subtract(bounding_box[2:], bounding_box[:2]).max()
        translation = (256 - np.add(bounding_box[2:], bounding_box[:2]) * scale) * 0.5

        # Warp face
        crop_vision_frame, affine_matrix = warp_face_by_translation(temp_vision_frame, translation, scale, (256, 256))

        # Apply CLAHE for better feature detection
        crop_vision_frame = cv2.cvtColor(crop_vision_frame, cv2.COLOR_RGB2Lab)
        if np.mean(crop_vision_frame[:, :, 0]) < 30:
            crop_vision_frame[:, :, 0] = cv2.createCLAHE(clipLimit=2).apply(crop_vision_frame[:, :, 0])
        crop_vision_frame = cv2.cvtColor(crop_vision_frame, cv2.COLOR_Lab2RGB)

        # Prepare input
        crop_vision_frame = crop_vision_frame.transpose(2, 0, 1).astype(np.float32) / 255.0

        # Run model
        face_landmark_68, face_heatmap = face_landmarker.run(None, {
            face_landmarker.get_inputs()[0].name: [crop_vision_frame]
        })

        # Process landmarks
        face_landmark_68 = face_landmark_68[:, :, :2][0] / 64
        face_landmark_68 = face_landmark_68.reshape(1, -1, 2) * 256
        face_landmark_68 = cv2.transform(face_landmark_68, cv2.invertAffineTransform(affine_matrix))
        face_landmark_68 = face_landmark_68.reshape(-1, 2)

        # Calculate confidence score
        face_landmark_68_score = np.amax(face_heatmap, axis=(2, 3))
        face_landmark_68_score = np.mean(face_landmark_68_score)

        return face_landmark_68, face_landmark_68_score

    except Exception as e:
        logger.error(f"Error in detect_face_landmark_68: {e}")
        # Return dummy landmarks with low confidence if detection fails
        dummy_landmarks = np.zeros((68, 2))
        return dummy_landmarks, 0.0


def convert_face_landmark_68_to_5(face_landmark_68: FaceLandmark68) -> FaceLandmark5:
    """
    Convert 68-point landmarks to 5-point landmarks

    Args:
        face_landmark_68: 68-point face landmarks

    Returns:
        5-point face landmarks
    """
    face_landmark_5 = np.array([
        np.mean(face_landmark_68[36:42], axis=0),  # left eye
        np.mean(face_landmark_68[42:48], axis=0),  # right eye
        face_landmark_68[30],  # nose
        face_landmark_68[48],  # left mouth
        face_landmark_68[54]  # right mouth
    ])
    return face_landmark_5


def warp_face_by_face_landmark_5(temp_vision_frame: VisionFrame, face_landmark_5: FaceLandmark5,
                                 warp_template: str, crop_size: Tuple[int, int]) -> Tuple[VisionFrame, Matrix]:
    """
    Warp face by 5-point landmarks to align with a standard template

    Args:
        temp_vision_frame: Input frame containing the face
        face_landmark_5: 5-point face landmarks (eyes, nose, mouth corners)
        warp_template: Template name for face alignment (e.g., 'arcface_112_v2')
        crop_size: Output size of the warped face (width, height)

    Returns:
        Tuple of warped face image and the affine transformation matrix
    """
    # Get the affine transformation matrix to align face with template
    affine_matrix = estimate_matrix_by_face_landmark_5(face_landmark_5, warp_template, crop_size)

    # Apply the affine transformation to warp the face
    crop_vision_frame = cv2.warpAffine(temp_vision_frame, affine_matrix, crop_size,
                                       borderMode=cv2.BORDER_REPLICATE,  # Replicate border pixels
                                       flags=cv2.INTER_AREA)  # Area interpolation for downsampling

    return crop_vision_frame, affine_matrix


def calc_embedding(temp_vision_frame: VisionFrame, face_landmark_5: FaceLandmark5) -> Tuple[Embedding, Embedding]:
    """
    Calculate face embedding for recognition

    Args:
        temp_vision_frame: Input frame
        face_landmark_5: 5-point face landmarks

    Returns:
        Tuple of raw embedding and normalized embedding
    """
    try:
        face_recognizer = get_face_analyser().get('face_recognizer')

        # Align and crop face
        crop_vision_frame, matrix = warp_face_by_face_landmark_5(
            temp_vision_frame, face_landmark_5, 'arcface_112_v2', (112, 112)
        )

        # Preprocess image
        crop_vision_frame = crop_vision_frame / 127.5 - 1
        crop_vision_frame = crop_vision_frame[:, :, ::-1].transpose(2, 0, 1).astype(np.float32)
        crop_vision_frame = np.expand_dims(crop_vision_frame, axis=0)

        # Calculate embedding
        embedding = face_recognizer.run(None, {
            face_recognizer.get_inputs()[0].name: crop_vision_frame
        })[0]

        # Process embedding
        embedding = embedding.ravel()
        normed_embedding = embedding / np.linalg.norm(embedding)

        return embedding, normed_embedding

    except Exception as e:
        logger.error(f"Error in calc_embedding: {e}")
        # Return random embedding if calculation fails
        random_embedding = np.random.random(512)
        normed_random = random_embedding / np.linalg.norm(random_embedding)
        return random_embedding, normed_random


def detect_gender_age(temp_vision_frame: VisionFrame, bounding_box: BoundingBox) -> Tuple[int, int]:
    """
    Detect gender and age from face

    Args:
        temp_vision_frame: Input frame
        bounding_box: Face bounding box

    Returns:
        Tuple of gender (0=female, 1=male) and age in years
    """
    try:
        gender_age_model = get_face_analyser().get('gender_age')

        # Reshape bounding box
        bounding_box = bounding_box.reshape(2, -1)

        # Calculate scale and translation
        scale = 64 / np.subtract(*bounding_box[::-1]).max()
        translation = 48 - bounding_box.sum(axis=0) * scale * 0.5

        # Warp face
        crop_vision_frame, affine_matrix = warp_face_by_translation(
            temp_vision_frame, translation, scale, (96, 96)
        )

        # Preprocess image
        crop_vision_frame = crop_vision_frame[:, :, ::-1].transpose(2, 0, 1).astype(np.float32)
        crop_vision_frame = np.expand_dims(crop_vision_frame, axis=0)

        # Run inference
        prediction = gender_age_model.run(None, {
            gender_age_model.get_inputs()[0].name: crop_vision_frame
        })[0][0]

        # Process results
        gender = int(np.argmax(prediction[:2]))
        age = int(np.round(prediction[2] * 100))

        return gender, age

    except Exception as e:
        logger.error(f"Error in detect_gender_age: {e}")
        # Return default values if detection fails
        return 1, 30  # Default to male, 30 years old


def apply_nms(bounding_box_list: List[BoundingBox], iou_threshold: float) -> List[int]:
    """Apply Non-Maximum Suppression to bounding boxes"""
    keep_indices = []
    dimension_list = np.reshape(bounding_box_list, (-1, 4))
    x1 = dimension_list[:, 0]
    y1 = dimension_list[:, 1]
    x2 = dimension_list[:, 2]
    y2 = dimension_list[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    indices = np.arange(len(bounding_box_list))
    while indices.size > 0:
        index = indices[0]
        remain_indices = indices[1:]
        keep_indices.append(index)
        xx1 = np.maximum(x1[index], x1[remain_indices])
        yy1 = np.maximum(y1[index], y1[remain_indices])
        xx2 = np.minimum(x2[index], x2[remain_indices])
        yy2 = np.minimum(y2[index], y2[remain_indices])
        width = np.maximum(0, xx2 - xx1 + 1)
        height = np.maximum(0, yy2 - yy1 + 1)
        iou = width * height / (areas[index] + areas[remain_indices] - width * height)
        indices = indices[np.where(iou <= iou_threshold)[0] + 1]
    return keep_indices


class FaceProcessor:
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize face processor with configurable parameters

        Args:
            config: Configuration dictionary with the following optional keys:
                - similarity_threshold: Threshold for face clustering (default: 0.6)
                - min_faces_in_group: Minimum faces required for a group (default: 3)
                - sample_interval: Process every Nth frame (default: 5)
                - ignore_frames: List of specific frame numbers to ignore (default: [])
                - ignore_ranges: List of frame ranges to ignore (default: [])
                - start_frame: Frame number to start processing from (default: 0)
                - end_frame: Frame number to end processing at (default: None)
                - face_detector_size: Size for face detector input (default: "640x640")
                - face_detector_score_threshold: Confidence threshold for detection (default: 0.5)
                - face_landmarker_score_threshold: Threshold for landmarker (default: 0.85)
                - iou_threshold: IOU threshold for NMS (default: 0.4)
                - min_appearance_ratio: Min ratio of group size to frames (default: 0.25)
                - min_frontality: Minimum acceptable frontality (default: 0.2)
                - avatar_size: Size of face avatar (default: 112)
                - avatar_padding: Padding percentage for face avatar (default: 0.07)
                - avatar_quality: JPEG quality for avatars (default: 85)
                - output_path: Base path for saving face avatars (default: "./faces")
                - max_workers: Maximum worker threads for parallel processing (default: min(8, os.cpu_count() or 4))
        """
        # Set defaults
        default_config = {
            # Clustering parameters
            "similarity_threshold": 0.6,
            "min_faces_in_group": 3,

            # Frame sampling parameters
            "sample_interval": 5,
            "ignore_frames": [],
            "ignore_ranges": [],
            "start_frame": 0,
            "end_frame": None,

            # Face detection parameters
            "face_detector_size": "640x640",
            "face_detector_score_threshold": 0.5,
            "face_landmarker_score_threshold": 0.85,
            "iou_threshold": 0.4,

            # Group filtering parameters
            "min_appearance_ratio": 0.25,
            "min_frontality": 0.2,

            # Avatar parameters
            "avatar_size": 112,
            "avatar_padding": 0.07,
            "avatar_quality": 85,
            "output_path": "./faces",

            # Processing parameters
            "max_workers": min(8, os.cpu_count() or 4)
        }

        # Apply user config over defaults
        self.config = default_config.copy()
        if config:
            self.config.update(config)

        # Create instance variables from config for easier access
        self.similarity_threshold = self.config["similarity_threshold"]
        self.min_faces_in_group = self.config["min_faces_in_group"]
        self.sample_interval = self.config["sample_interval"]
        self.ignore_frames = set(self.config["ignore_frames"] or [])
        self.ignore_ranges = self.config["ignore_ranges"] or []
        self.start_frame = self.config["start_frame"]
        self.end_frame = self.config["end_frame"]
        self.face_detector_size = self.config["face_detector_size"]
        self.face_detector_score_threshold = self.config["face_detector_score_threshold"]
        self.face_landmarker_score_threshold = self.config["face_landmarker_score_threshold"]
        self.iou_threshold = self.config["iou_threshold"]
        self.min_appearance_ratio = self.config["min_appearance_ratio"]
        self.min_frontality = self.config["min_frontality"]
        self.avatar_size = self.config["avatar_size"]
        self.avatar_padding = self.config["avatar_padding"]
        self.avatar_quality = self.config["avatar_quality"]
        self.output_path = self.config["output_path"]
        self.max_workers = self.config["max_workers"]

    def _should_process_frame(self, frame_number: int) -> bool:
        """Check if frame should be processed based on configuration"""
        # Check if frame is before start_frame
        if frame_number < self.start_frame:
            return False

        # Check if frame is after end_frame
        if self.end_frame and frame_number > self.end_frame:
            return False

        # Check if frame is in ignore list
        if frame_number in self.ignore_frames:
            return False

        # Check if frame is in any ignore range
        for start, end in self.ignore_ranges:
            if start <= frame_number <= end:
                return False

        # Check sample interval
        if frame_number % self.sample_interval != 0:
            return False

        return True

    def process_video(self, video_path: str) -> Dict:
        """Process video and extract face groups with parallel processing"""
        faces_with_metadata = []
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Get list of frames to process
        frames_to_process = []
        frame_indices = []
        frame_count = 0

        logger.info(f"Reading frames from video: {video_path}")
        progress_bar = tqdm(total=total_frames, desc="Reading frames")

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if self._should_process_frame(frame_count):
                frames_to_process.append(frame.copy())
                frame_indices.append(frame_count)

            frame_count += 1
            progress_bar.update(1)

            if self.end_frame and frame_count > self.end_frame:
                break

        cap.release()
        progress_bar.close()

        # Process frames in parallel
        logger.info(f"Processing {len(frames_to_process)} frames with face detection")
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_frame = {
                executor.submit(self._process_single_frame, frame, idx): (frame, idx)
                for idx, frame in zip(frame_indices, frames_to_process)
            }

            for i, future in enumerate(tqdm(concurrent.futures.as_completed(future_to_frame),
                                            total=len(frames_to_process),
                                            desc="Detecting faces")):
                frame_faces = future.result()
                if frame_faces:
                    faces_with_metadata.extend(frame_faces)

                # Log progress periodically
                if i % 10 == 0:
                    logger.info(
                        f"Processed {i}/{len(frames_to_process)} frames ({i / len(frames_to_process) * 100:.1f}%)")

        # Process detected faces
        processed_frames = len(set(f['frame_number'] for f in faces_with_metadata))
        logger.info(f"Found {len(faces_with_metadata)} faces in {processed_frames} frames")

        # Continue with clustering and result creation
        logger.info("Clustering faces...")
        groups = self._cluster_faces(faces_with_metadata)
        logger.info(f"Created {len(groups)} face groups")

        # Detect gender and age for representative face of each group
        logger.info("Detecting gender and age for representative faces...")
        groups = self._detect_gender_age_for_groups(groups)

        logger.info("Generating final results...")
        result = self._create_result(video_path, groups, processed_frames)

        return result

    def _detect_gender_age_for_groups(self, groups: List[List[Dict]]) -> List[List[Dict]]:
        """
        Detect gender and age only for the best face in each group

        Args:
            groups: List of face groups

        Returns:
            Updated groups with gender and age attributes
        """
        for group in groups:
            if not group:
                continue

            # Find best face in group
            best_face_data = self._select_best_face(group)
            if not best_face_data:
                continue

            # Detect gender and age for representative face
            gender, age = detect_gender_age(
                best_face_data['frame'],
                best_face_data['face'].bounding_box
            )

            # Update all faces in group with same gender and age
            for face_data in group:
                face_data['face'].gender = gender
                face_data['face'].age = age

        return groups

    def _process_single_frame(self, frame: np.ndarray, frame_number: int) -> List[Dict]:
        """Process a single frame and return faces with metadata"""
        result = []
        try:
            # Detect faces using face detector with configurable params
            bounding_box_list, face_landmark_5_list, score_list = detect_with_yoloface(
                frame,
                self.face_detector_size,
                self.face_detector_score_threshold
            )

            # Create Face objects without gender and age detection
            frame_faces = create_faces(
                frame,
                bounding_box_list,
                face_landmark_5_list,
                score_list,
                self.face_detector_score_threshold,
                self.face_landmarker_score_threshold,
                self.iou_threshold
            )

            # Sort faces by x-coordinate
            frame_faces = sorted(frame_faces, key=lambda f: f.bounding_box[0])

            for index_f, face in enumerate(frame_faces):
                result.append({
                    'face': face,
                    'frame_number': frame_number,
                    'frame': frame.copy(),
                    'index': index_f,
                    'quality': self._assess_face_quality(frame, face.bounding_box)
                })
        except Exception as e:
            logger.error(f"Error processing frame {frame_number}: {e}")

        return result

    def process_image(self, image_path) -> Dict:
        """Process a single image and return detected faces"""
        frame = cv2.imread(image_path)
        if frame is None:
            logger.error(f"Could not read image: {image_path}")
            return {
                "is_change_index": False,
                "faces": []
            }

        # Detect faces using face detector with configurable params
        bounding_box_list, face_landmark_5_list, score_list = detect_with_yoloface(
            frame,
            self.face_detector_size,
            self.face_detector_score_threshold
        )

        if not bounding_box_list:
            return {
                "is_change_index": False,
                "faces": []
            }

        # Create Face objects without gender and age detection
        frame_faces = create_faces(
            frame,
            bounding_box_list,
            face_landmark_5_list,
            score_list,
            self.face_detector_score_threshold,
            self.face_landmarker_score_threshold,
            self.iou_threshold
        )

        if not frame_faces:
            return {
                "is_change_index": False,
                "faces": []
            }

        # Detect gender and age for each face immediately (since we're not clustering in single image mode)
        for face in frame_faces:
            gender, age = detect_gender_age(frame, face.bounding_box)
            face.gender = gender
            face.age = age

        data_faces = []
        for index, face in enumerate(frame_faces):
            # Save face image and get base64
            avatar_base64 = self.get_face_avatar(
                frame,
                face.bounding_box
            )
            data_faces.append({
                "name": os.path.basename(image_path),
                "avatar": avatar_base64,
                "index": index,
                "bounding_box": face.bounding_box.tolist(),
                "detector": float(face.scores['detector']),
                "landmarker": float(face.scores['landmarker']),
                "normed_embedding": face.normed_embedding.tolist(),
                "gender": int(float(face.gender)),
                "age": int(float(face.age))
            })
        return {
            "is_change_index": False,
            "faces": data_faces
        }

    def _cluster_faces(self, faces_with_metadata: List[Dict]) -> List[List[Dict]]:
        """Cluster faces using DBSCAN with configurable parameters"""
        if not faces_with_metadata:
            return []

        # Extract embeddings
        embeddings = np.array([f['face'].normed_embedding for f in faces_with_metadata])

        # Perform clustering
        clustering = DBSCAN(
            eps=self.similarity_threshold,
            min_samples=self.min_faces_in_group,
            metric='cosine'
        ).fit(embeddings)

        # Group faces by cluster
        groups = {}
        for face_idx, label in enumerate(clustering.labels_):
            if label == -1:  # Skip noise
                continue
            if label not in groups:
                groups[label] = []
            groups[label].append(faces_with_metadata[face_idx])

        return list(groups.values())

    def _select_best_face(self, group: List[Dict]) -> Dict:
        """Select best face from group based on quality and detection scores"""
        if not group:
            return None

        best_score = float('-inf')
        best_face_data = None

        for face_data in group:
            quality_score = (
                    face_data['face'].scores['detector'] * 0.4 +
                    face_data['face'].scores['landmarker'] * 0.3 +
                    face_data['quality'] * 0.3
            )

            if quality_score > best_score:
                best_score = quality_score
                best_face_data = face_data

        return best_face_data

    def _calculate_group_metrics(self, group: List[Dict]) -> Dict[str, float]:
        """Calculate variance metrics for group"""
        embeddings = np.array([f['face'].normed_embedding for f in group])
        centroid = np.mean(embeddings, axis=0)

        distances = [1 - np.dot(emb, centroid) for emb in embeddings]
        pose_metrics = []
        for face_data in group:
            pose = self._analyze_pose(face_data['face'].landmarks)
            pose_metrics.append(pose)
        # Calculate pose statistics
        yaws = [p['yaw'] for p in pose_metrics]
        pitches = [p['pitch'] for p in pose_metrics]
        frontality_scores = [p['frontality_score'] for p in pose_metrics]
        return {
            "mean_distance": statistics.mean(distances),
            "std_distance": statistics.stdev(distances) if len(distances) > 1 else 0,
            "max_distance": max(distances),
            "min_distance": min(distances),
            "age_variance": statistics.stdev([f['face'].age for f in group]) if len(group) > 1 else 0,
            "temporal_spread": max(f['frame_number'] for f in group) - min(f['frame_number'] for f in group),
            # Pose variation metrics
            'pose_yaw_variance': statistics.stdev(yaws) if len(yaws) > 1 else 0,
            'pose_pitch_variance': statistics.stdev(pitches) if len(pitches) > 1 else 0,
            # Average pose metrics
            'pose_avg_yaw': statistics.mean(yaws),
            'pose_avg_pitch': statistics.mean(pitches),
            # Frontality metrics
            'pose_avg_frontality': statistics.mean(frontality_scores),
            'pose_min_frontality': min(frontality_scores),
            'pose_max_frontality': max(frontality_scores),
            # Overall pose quality score (0-1, higher is better)
            'pose_quality_score': self._calculate_pose_quality_score(
                frontality_scores,
                statistics.stdev(yaws) if len(yaws) > 1 else 0,
                statistics.stdev(pitches) if len(pitches) > 1 else 0
            )
        }

    def get_face_avatar(self, frame: np.ndarray, bbox, size: Optional[int] = None,
                        padding_percent: Optional[float] = None) -> str:
        """
        Extract face region as square and convert to base64
        Args:
            frame: Input frame
            bbox: Face bounding box
            size: Size to resize face image (default from config)
            padding_percent: Percentage of padding to add around face (default from config)
        Returns:
            str: Base64 encoded image string
        """
        # Use config values if not specified
        size = size or self.avatar_size
        padding_percent = padding_percent if padding_percent is not None else self.avatar_padding

        try:
            # Convert bbox coordinates to integers
            x1, y1, x2, y2 = map(int, map(float, bbox))

            # Calculate center point and box dimensions
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            box_width = x2 - x1
            box_height = y2 - y1

            # Calculate padding
            padding_x = int(box_width * padding_percent)
            padding_y = int(box_height * padding_percent)

            # Make square by taking max dimension
            half_size = max(box_width + padding_x, box_height + padding_y) // 2

            # Calculate square bounds, centered on face center
            sq_x1 = max(0, center_x - half_size)
            sq_y1 = max(0, center_y - half_size)
            sq_x2 = min(frame.shape[1], center_x + half_size)
            sq_y2 = min(frame.shape[0], center_y + half_size)

            # Extract square region
            face_img = frame[sq_y1:sq_y2, sq_x1:sq_x2]

            # Handle cases where crop area goes outside frame
            if face_img.shape[0] != face_img.shape[1]:
                min_dim = min(face_img.shape[0], face_img.shape[1])
                # Crop to square from center
                start_y = (face_img.shape[0] - min_dim) // 2
                start_x = (face_img.shape[1] - min_dim) // 2
                face_img = face_img[start_y:start_y + min_dim, start_x:start_x + min_dim]

            # Resize to final size
            face_img = cv2.resize(face_img, (size, size))

            # Compress with quality from config
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.avatar_quality]
            _, buffer = cv2.imencode('.jpg', face_img, encode_param)
            base64_image = b64encode(buffer).decode('utf-8')

            return base64_image

        except Exception as e:
            logger.error(f"Error generating avatar: {e}", "FACE GROUPS")
            return ""

    def save_face_avatar(self, frame: np.ndarray, bbox, output_path: Optional[str] = None,
                         size: Optional[int] = None, padding_percent: Optional[float] = None) -> Tuple[str, str]:
        """
        Extract face region as square, save to file and return both file path and base64
        Args:
            frame: Input frame
            bbox: Face bounding box
            output_path: Path to save image (default from config + generated name)
            size: Size to resize face image (default from config)
            padding_percent: Percentage of padding to add around face (default from config)
        Returns:
            Tuple[str, str]: (file_path, base64_string)
        """
        # Use config values if not specified
        size = size or self.avatar_size
        padding_percent = padding_percent if padding_percent is not None else self.avatar_padding

        try:
            # Generate output path if not provided
            if output_path is None:
                os.makedirs(self.output_path, exist_ok=True)
                output_path = os.path.join(self.output_path, f"{hash(str(bbox))}.jpg")
            else:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Convert bbox coordinates to integers
            x1, y1, x2, y2 = map(int, map(float, bbox))

            # Calculate center point and box dimensions
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            box_width = x2 - x1
            box_height = y2 - y1

            # Calculate padding
            padding_x = int(box_width * padding_percent)
            padding_y = int(box_height * padding_percent)

            # Make square by taking max dimension
            half_size = max(box_width + padding_x, box_height + padding_y) // 2

            # Calculate square bounds, centered on face center
            sq_x1 = max(0, center_x - half_size)
            sq_y1 = max(0, center_y - half_size)
            sq_x2 = min(frame.shape[1], center_x + half_size)
            sq_y2 = min(frame.shape[0], center_y + half_size)

            # Extract square region
            face_img = frame[sq_y1:sq_y2, sq_x1:sq_x2]

            # Handle cases where crop area goes outside frame
            if face_img.shape[0] != face_img.shape[1]:
                min_dim = min(face_img.shape[0], face_img.shape[1])
                # Crop to square from center
                start_y = (face_img.shape[0] - min_dim) // 2
                start_x = (face_img.shape[1] - min_dim) // 2
                face_img = face_img[start_y:start_y + min_dim, start_x:start_x + min_dim]

            # Resize to final size
            face_img = cv2.resize(face_img, (size, size))

            # Save image with compression
            cv2.imwrite(output_path, face_img, [int(cv2.IMWRITE_JPEG_QUALITY), self.avatar_quality])

            # Convert to base64 with compression
            _, buffer = cv2.imencode('.jpg', face_img, [int(cv2.IMWRITE_JPEG_QUALITY), self.avatar_quality])
            base64_image = b64encode(buffer).decode('utf-8')

            return output_path, base64_image

        except Exception as e:
            logger.error(f"Error saving face avatar: {e}")
            return "", ""

    def _create_result(
            self, video_path: str,
            groups: List[List[Dict]],
            processed_frames: int
    ) -> Dict:
        """Create final result dictionary with face groups"""
        groups_data = []

        is_change_index = False
        for group_id, group in enumerate(groups):
            # Check if face index changes in any group
            if not is_change_index:
                all_index = [f['index'] for f in group]
                if len(set(all_index)) > 1:
                    is_change_index = True

        for group_id, group in enumerate(groups):
            # Select best face
            best_face_data = self._select_best_face(group)
            if not best_face_data:
                continue

            # Get frame number
            frame_num = best_face_data['frame_number']

            # Save face image and get base64
            avatar_base64 = self.get_face_avatar(
                best_face_data['frame'],
                best_face_data['face'].bounding_box
            )

            # Save face avatar to disk with path from config
            output_path = os.path.join(self.output_path, f"{group_id}.jpg")
            self.save_face_avatar(
                frame=best_face_data['frame'],
                bbox=best_face_data['face'].bounding_box,
                output_path=output_path
            )

            group_data = {
                "name": f"{frame_num:06d}_{group_id:02d}",
                "group_size": len(group),
                "index": group_id,
                "avatar": avatar_base64,
                "bounding_box": best_face_data['face'].bounding_box.tolist(),
                "detector": float(best_face_data['face'].scores['detector']),
                "landmarker": float(best_face_data['face'].scores['landmarker']),
                "normed_embedding": best_face_data['face'].normed_embedding.tolist(),
                "gender": int(float(best_face_data['face'].gender)),
                "age": int(float(best_face_data['face'].age)),
                "metrics": self._calculate_group_metrics(group)
            }
            groups_data.append(group_data)

        groups_data_filtered = self._filter_quality_groups(
            groups_data,
            processed_frames
        )

        if len(groups_data_filtered) != len(groups_data):
            logger.info(f"Filtered groups: {len(groups_data) - len(groups_data_filtered)}", "FACE GROUPS")
            is_change_index = True

        return {
            "is_change_index": is_change_index,
            "faces": groups_data_filtered
        }

    def _filter_quality_groups(
            self,
            groups: List[dict],
            processed_frames: int,
            min_appearance_ratio: Optional[float] = None,
            min_frontality: Optional[float] = None) -> List[dict]:
        """
        Filter groups based on quality metrics with configurable thresholds

        Args:
            groups: List of face groups
            processed_frames: Total number of processed frames
            min_appearance_ratio: Minimum ratio of group size to processed frames (default from config)
            min_frontality: Minimum acceptable frontality (default from config)

        Returns:
            List[dict]: Filtered high quality groups
        """
        # Use config values if not specified
        min_appearance_ratio = min_appearance_ratio if min_appearance_ratio is not None else self.min_appearance_ratio
        min_frontality = min_frontality if min_frontality is not None else self.min_frontality

        filtered_groups = []

        for group in groups:
            appearance_ratio = group['group_size'] / processed_frames
            min_frontality_score = group['metrics']['pose_min_frontality']
            if (appearance_ratio >= min_appearance_ratio and
                    min_frontality_score >= min_frontality):
                filtered_groups.append(group)

        return filtered_groups

    def _assess_face_quality(self, frame: np.ndarray, bounding_box) -> float:
        """Assess the quality of a face region"""
        try:
            # Convert bounding box coordinates to integers
            x1, y1, x2, y2 = map(int, bounding_box)

            # Ensure coordinates are within frame bounds
            height, width = frame.shape[:2]
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(width, x2)
            y2 = min(height, y2)

            # Extract face region
            face_img = frame[y1:y2, x1:x2]

            if face_img.size == 0:
                return 0.0

            # Calculate quality metrics
            brightness = np.mean(face_img)
            brightness_score = 1.0 - abs(brightness - 128) / 128

            contrast = np.std(face_img)
            contrast_score = min(contrast / 128, 1.0)

            size = (x2 - x1) * (y2 - y1)
            size_score = min(size / (frame.shape[0] * frame.shape[1] * 0.25), 1.0)

            # Combine scores
            quality_score = (brightness_score * 0.3 +
                             contrast_score * 0.3 +
                             size_score * 0.4)

            return float(quality_score)

        except Exception as e:
            logger.error(f"Error in assess_face_quality: {e}")
            return 0.0

    def _analyze_pose(self, landmarks: Dict) -> Dict[str, float]:
        """
        Analyze face pose from landmarks
        Returns dict with pose metrics
        """
        try:
            # Get key facial landmarks (assuming 68 point format)
            landmarks_68 = landmarks.get('68')
            if landmarks_68 is None:
                return {'yaw': 0.0, 'pitch': 0.0, 'frontality_score': 1.0}

            # Convert to numpy array if needed
            if not isinstance(landmarks_68, np.ndarray):
                landmarks_68 = np.array(landmarks_68)

            # Get nose bridge points
            nose_bridge = landmarks_68[27:31]

            # Get left and right eye corners
            left_eye = landmarks_68[36]
            right_eye = landmarks_68[45]

            # Calculate yaw (left-right rotation)
            eye_distance = np.linalg.norm(right_eye - left_eye)
            nose_direction = nose_bridge[-1] - nose_bridge[0]
            yaw = np.arctan2(nose_direction[0], eye_distance) * 180 / np.pi

            # Calculate pitch (up-down rotation)
            nose_height = nose_bridge[-1][1] - nose_bridge[0][1]
            pitch = np.arctan2(nose_height, eye_distance) * 180 / np.pi

            # Calculate frontality score (1 = perfectly frontal, 0 = extreme pose)
            # Normalize yaw and pitch to 0-1 range where 0 is frontal
            normalized_yaw = min(abs(yaw) / 45.0, 1.0)  # 45 degrees as max
            normalized_pitch = min(abs(pitch) / 30.0, 1.0)  # 30 degrees as max

            frontality_score = 1.0 - (normalized_yaw * 0.6 + normalized_pitch * 0.4)

            return {
                'yaw': float(yaw),
                'pitch': float(pitch),
                'frontality_score': float(frontality_score)
            }

        except Exception as e:
            logger.error(f"Error in analyze_pose: {e}")
            return {'yaw': 0.0, 'pitch': 0.0, 'frontality_score': 1.0}

    def _calculate_pose_quality_score(self,
                                      frontality_scores: List[float],
                                      yaw_variance: float,
                                      pitch_variance: float) -> float:
        """
        Calculate overall pose quality score for group
        Returns: float 0-1 where 1 is best (mostly frontal poses with low variance)
        """
        try:
            # Average frontality (40% weight)
            frontality_component = statistics.mean(frontality_scores) * 0.4

            # Pose variance penalty (30% weight for each)
            # Convert variances to 0-1 scale where 0 variance is best
            normalized_yaw_var = max(0, 1 - (yaw_variance / 45.0))  # 45 degrees variance as max
            normalized_pitch_var = max(0, 1 - (pitch_variance / 30.0))  # 30 degrees variance as max

            variance_component = (normalized_yaw_var * 0.3 + normalized_pitch_var * 0.3)

            # Combine scores
            final_score = frontality_component + variance_component

            return float(min(1.0, max(0.0, final_score)))

        except Exception as e:
            logger.error(f"Error calculating pose quality score: {e}", "FACE GROUPS")
            return 0.0

    def _calculate_glcm_features(self, image: np.ndarray) -> Dict[str, float]:
        """Calculate GLCM (Gray Level Co-occurrence Matrix) features"""
        try:
            glcm = np.zeros((256, 256), dtype=np.uint32)
            rows, cols = image.shape

            # Calculate GLCM
            for i in range(rows - 1):
                for j in range(cols - 1):
                    i_val = image[i, j]
                    j_val = image[i, j + 1]
                    glcm[i_val, j_val] += 1

            # Normalize GLCM
            glcm = glcm / glcm.sum()

            # Calculate features
            contrast = 0
            correlation = 0
            energy = 0
            homogeneity = 0

            for i in range(256):
                for j in range(256):
                    contrast += glcm[i, j] * (i - j) ** 2
                    energy += glcm[i, j] ** 2
                    homogeneity += glcm[i, j] / (1 + abs(i - j))

            return {
                'contrast': contrast,
                'energy': energy,
                'homogeneity': homogeneity
            }

        except Exception as e:
            logger.error(f"Error calculating GLCM features: {e}")
            return {'contrast': 0, 'energy': 0, 'homogeneity': 0}

#
# def main():
#     """
#     Example demonstrating how to use the refactored FaceProcessor with custom configuration
#     """
#     # Define configuration with customized parameters
#     config = {
#         # Clustering parameters
#         "similarity_threshold": 0.6,  # Threshold for face clustering (lower = more groups)
#         "min_faces_in_group": 3,  # Minimum faces required to form a group
#         # Frame sampling parameters
#         "sample_interval": 5,  # Process every 5th frame for efficiency
#         "ignore_frames": [0, 1, 2],  # Skip first 3 frames (often contain transitions)
#         "ignore_ranges": [(500, 600)],  # Skip frames 500-600 (e.g., a section to ignore)
#         # Face detection parameters
#         "face_detector_size": "640x640",  # Size for face detector input
#         "face_detector_score_threshold": 0.6,  # Min confidence for face detection
#
#         # Group filtering parameters
#         "min_appearance_ratio": 0.15,  # Require faces to appear in at least 20% of frames
#         "min_frontality": 0.2,  # Require faces to be fairly frontal
#         # Avatar parameters
#         "avatar_size": 256,  # Higher resolution avatars
#         "avatar_padding": 0.1,  # More padding around faces
#         "avatar_quality": 90,  # Higher quality JPEG
#         "output_path": "./output/faces",  # Custom output directory
#         # Processing parameters
#         "max_workers": 4  # Control thread pool size
#     }
#
#     # Create processor with custom config
#     processor = FaceProcessor(config)
#
#     # Process a video
#     video_path = "/Users/quang/Documents/skl-workspace/transcode/media-transcode/uploads/input_3.mp4"
#     if os.path.exists(video_path):
#         print(f"Processing video: {video_path}")
#         result = processor.process_video(video_path)
#
#         # Save results to JSON
#         output_file = "face_groups.json"
#         os.makedirs("./output", exist_ok=True)
#         with open(f"./output/{output_file}", "w") as f:
#             json.dump(result, f, cls=NumpyJSONEncoder, indent=2)
#
#         print(f"Results saved to ./output/{output_file}")
#         print(f"Processed {len(result['faces'])} face groups")
#     else:
#         print(f"Video file not found: {video_path}")
#
#
# if __name__ == "__main__":
#     main()
