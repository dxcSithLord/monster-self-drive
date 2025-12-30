"""Object Detection Module - ML-based object detection with Coral TPU support.

This module provides object detection using TensorFlow Lite models, with
hardware acceleration via Google Coral Edge TPU when available.

Features:
- Coral TPU acceleration (25-30 fps on RPi)
- CPU fallback using TFLite runtime (3-5 fps on RPi)
- COCO dataset support (90 object classes)
- Configurable confidence thresholds
- Class filtering (track only specific objects)

Supported Models:
- MobileNet SSD v2 (COCO) - General purpose, fast
- EfficientDet-Lite0 - Higher accuracy
- Custom TFLite models

Usage:
    detector = ObjectDetector(
        model_path="models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite",
        labels_path="models/coco_labels.txt"
    )

    # Detect objects in a frame
    detections = detector.detect(frame)

    for det in detections:
        print(f"{det.label}: {det.confidence:.2f} at {det.bbox}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

from .tpu_delegate import TPUBackend, TPUDelegate, get_tpu_delegate

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


# COCO dataset class labels (80 classes + background)
COCO_LABELS = {
    0: "background",
    1: "person",
    2: "bicycle",
    3: "car",
    4: "motorcycle",
    5: "airplane",
    6: "bus",
    7: "train",
    8: "truck",
    9: "boat",
    10: "traffic light",
    11: "fire hydrant",
    13: "stop sign",
    14: "parking meter",
    15: "bench",
    16: "bird",
    17: "cat",
    18: "dog",
    19: "horse",
    20: "sheep",
    21: "cow",
    22: "elephant",
    23: "bear",
    24: "zebra",
    25: "giraffe",
    27: "backpack",
    28: "umbrella",
    31: "handbag",
    32: "tie",
    33: "suitcase",
    34: "frisbee",
    35: "skis",
    36: "snowboard",
    37: "sports ball",
    38: "kite",
    39: "baseball bat",
    40: "baseball glove",
    41: "skateboard",
    42: "surfboard",
    43: "tennis racket",
    44: "bottle",
    46: "wine glass",
    47: "cup",
    48: "fork",
    49: "knife",
    50: "spoon",
    51: "bowl",
    52: "banana",
    53: "apple",
    54: "sandwich",
    55: "orange",
    56: "broccoli",
    57: "carrot",
    58: "hot dog",
    59: "pizza",
    60: "donut",
    61: "cake",
    62: "chair",
    63: "couch",
    64: "potted plant",
    65: "bed",
    67: "dining table",
    70: "toilet",
    72: "tv",
    73: "laptop",
    74: "mouse",
    75: "remote",
    76: "keyboard",
    77: "cell phone",
    78: "microwave",
    79: "oven",
    80: "toaster",
    81: "sink",
    82: "refrigerator",
    84: "book",
    85: "clock",
    86: "vase",
    87: "scissors",
    88: "teddy bear",
    89: "hair drier",
    90: "toothbrush",
}


class DetectionStatus(Enum):
    """Status of the detection system."""

    READY = auto()  # Detector initialized and ready
    NO_MODEL = auto()  # Model file not found
    NO_BACKEND = auto()  # No inference backend available
    ERROR = auto()  # Initialization error


@dataclass
class BoundingBox:
    """Bounding box in normalized coordinates (0-1) or pixel coordinates.

    Attributes:
        x1: Left edge (0-1 normalized or pixels)
        y1: Top edge (0-1 normalized or pixels)
        x2: Right edge (0-1 normalized or pixels)
        y2: Bottom edge (0-1 normalized or pixels)
        normalized: Whether coordinates are normalized (0-1)
    """

    x1: float
    y1: float
    x2: float
    y2: float
    normalized: bool = True

    @property
    def width(self) -> float:
        """Width of the bounding box."""
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        """Height of the bounding box."""
        return self.y2 - self.y1

    @property
    def center(self) -> tuple[float, float]:
        """Center point of the bounding box."""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def area(self) -> float:
        """Area of the bounding box."""
        return self.width * self.height

    def to_pixels(self, frame_width: int, frame_height: int) -> "BoundingBox":
        """Convert to pixel coordinates.

        Args:
            frame_width: Width of the frame in pixels.
            frame_height: Height of the frame in pixels.

        Returns:
            New BoundingBox in pixel coordinates.
        """
        if not self.normalized:
            return self
        return BoundingBox(
            x1=self.x1 * frame_width,
            y1=self.y1 * frame_height,
            x2=self.x2 * frame_width,
            y2=self.y2 * frame_height,
            normalized=False,
        )

    def to_normalized(self, frame_width: int, frame_height: int) -> "BoundingBox":
        """Convert to normalized coordinates.

        Args:
            frame_width: Width of the frame in pixels.
            frame_height: Height of the frame in pixels.

        Returns:
            New BoundingBox in normalized coordinates.
        """
        if self.normalized:
            return self
        return BoundingBox(
            x1=self.x1 / frame_width,
            y1=self.y1 / frame_height,
            x2=self.x2 / frame_width,
            y2=self.y2 / frame_height,
            normalized=True,
        )

    def to_xywh(self) -> tuple[float, float, float, float]:
        """Convert to (x, y, width, height) format.

        Returns:
            Tuple of (x, y, width, height).
        """
        return (self.x1, self.y1, self.width, self.height)

    def to_opencv(self, frame_width: int, frame_height: int) -> tuple[int, int, int, int]:
        """Convert to OpenCV format (x, y, w, h) in pixels.

        Args:
            frame_width: Width of the frame in pixels.
            frame_height: Height of the frame in pixels.

        Returns:
            Tuple of (x, y, width, height) as integers.
        """
        pixel_box = self.to_pixels(frame_width, frame_height)
        return (
            int(pixel_box.x1),
            int(pixel_box.y1),
            int(pixel_box.width),
            int(pixel_box.height),
        )

    def iou(self, other: "BoundingBox") -> float:
        """Calculate Intersection over Union with another box.

        Args:
            other: Another bounding box.

        Returns:
            IoU score between 0 and 1.
        """
        # Calculate intersection
        x1 = max(self.x1, other.x1)
        y1 = max(self.y1, other.y1)
        x2 = min(self.x2, other.x2)
        y2 = min(self.y2, other.y2)

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        union = self.area + other.area - intersection

        if union <= 0:
            return 0.0

        return intersection / union


@dataclass
class Detection:
    """A detected object in a frame.

    Attributes:
        class_id: COCO class ID of the detected object.
        label: Human-readable label for the class.
        confidence: Detection confidence score (0-1).
        bbox: Bounding box of the detection.
    """

    class_id: int
    label: str
    confidence: float
    bbox: BoundingBox

    def __repr__(self) -> str:
        return (
            f"Detection({self.label}, conf={self.confidence:.2f}, "
            f"bbox=({self.bbox.x1:.2f}, {self.bbox.y1:.2f}, "
            f"{self.bbox.x2:.2f}, {self.bbox.y2:.2f}))"
        )


@dataclass
class ObjectDetector:
    """ML-based object detector with Coral TPU support.

    Provides object detection using TensorFlow Lite models, with automatic
    hardware acceleration via Google Coral Edge TPU when available.

    Attributes:
        model_path: Path to the TFLite model file.
        labels_path: Path to the labels file (optional).
        confidence_threshold: Minimum confidence for detections (0-1).
        target_classes: List of class names to detect (None = all).
        max_detections: Maximum number of detections to return.
        input_size: Model input size (width, height).
        force_cpu: Force CPU inference even if TPU is available.
    """

    model_path: str | Path
    labels_path: str | Path | None = None
    confidence_threshold: float = 0.5
    target_classes: list[str] | None = None
    max_detections: int = 10
    input_size: tuple[int, int] = (300, 300)
    force_cpu: bool = False

    # Internal state
    _delegate: TPUDelegate = field(default=None, repr=False)  # type: ignore
    _interpreter: object = field(default=None, repr=False)
    _labels: dict[int, str] = field(default_factory=dict, repr=False)
    _target_class_ids: set[int] = field(default_factory=set, repr=False)
    _status: DetectionStatus = field(default=DetectionStatus.NO_MODEL, repr=False)
    _input_details: list = field(default_factory=list, repr=False)
    _output_details: list = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        """Initialize the detector."""
        self._delegate = get_tpu_delegate()
        self._load_labels()
        self._initialize_model()

    def _load_labels(self) -> None:
        """Load class labels from file or use defaults."""
        if self.labels_path:
            labels_path = Path(self.labels_path)
            if labels_path.exists():
                try:
                    with open(labels_path) as f:
                        # Handle different label file formats
                        self._labels = {}
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            # Format: "id label" or just "label"
                            parts = line.split(maxsplit=1)
                            if len(parts) == 2 and parts[0].isdigit():
                                self._labels[int(parts[0])] = parts[1]
                            else:
                                # Assume sequential IDs starting from 0
                                self._labels[len(self._labels)] = line
                    logger.info(f"Loaded {len(self._labels)} labels from {labels_path}")
                except Exception as e:
                    logger.warning(f"Error loading labels: {e}")
                    self._labels = COCO_LABELS.copy()
            else:
                logger.info(f"Labels file not found: {labels_path}, using COCO defaults")
                self._labels = COCO_LABELS.copy()
        else:
            self._labels = COCO_LABELS.copy()

        # Build target class ID set
        if self.target_classes:
            self._target_class_ids = set()
            for class_name in self.target_classes:
                class_name_lower = class_name.lower()
                for class_id, label in self._labels.items():
                    if label.lower() == class_name_lower:
                        self._target_class_ids.add(class_id)
                        break
            logger.info(f"Target classes: {self.target_classes} -> IDs: {self._target_class_ids}")

    def _initialize_model(self) -> None:
        """Initialize the TFLite model and interpreter."""
        model_path = Path(self.model_path)

        if not model_path.exists():
            logger.warning(f"Model not found: {model_path}")
            self._status = DetectionStatus.NO_MODEL
            return

        if not self._delegate.is_available():
            logger.warning("No inference backend available")
            self._status = DetectionStatus.NO_BACKEND
            return

        try:
            # Use CPU if force_cpu is True, otherwise let delegate decide
            use_tpu = None if not self.force_cpu else False
            if self.force_cpu:
                logger.info("Forcing CPU inference (force_cpu=True)")

            self._interpreter = self._delegate.make_interpreter(model_path, use_tpu=use_tpu)
            self._input_details = self._delegate.get_input_details()
            self._output_details = self._delegate.get_output_details()

            # Update input size from model
            if self._input_details:
                shape = self._input_details[0]["shape"]
                # Shape is typically [1, height, width, channels]
                if len(shape) >= 3:
                    self.input_size = (shape[2], shape[1])  # (width, height)

            self._status = DetectionStatus.READY
            logger.info(
                f"Detector initialized: backend={self._delegate.get_backend().name}, "
                f"input_size={self.input_size}"
            )
        except Exception as e:
            logger.exception(f"Error initializing detector: {e}")
            self._status = DetectionStatus.ERROR

    @property
    def status(self) -> DetectionStatus:
        """Get the detector status."""
        return self._status

    @property
    def is_ready(self) -> bool:
        """Check if the detector is ready for inference."""
        return self._status == DetectionStatus.READY

    @property
    def backend(self) -> TPUBackend:
        """Get the current inference backend."""
        return self._delegate.stats.backend

    def detect(self, frame: "NDArray[np.uint8]") -> list[Detection]:
        """Detect objects in a frame.

        Args:
            frame: BGR image as numpy array (OpenCV format).

        Returns:
            List of Detection objects, sorted by confidence (highest first).
        """
        if not self.is_ready:
            return []

        # Preprocess frame
        input_tensor = self._preprocess(frame)

        # Set input tensor
        self._set_input(input_tensor)

        # Run inference
        inference_time = self._delegate.invoke(self._interpreter)
        logger.debug(f"Inference time: {inference_time:.1f}ms")

        # Parse output
        detections = self._parse_output()

        # Filter by target classes
        if self._target_class_ids:
            detections = [d for d in detections if d.class_id in self._target_class_ids]

        # Sort by confidence and limit
        detections.sort(key=lambda d: d.confidence, reverse=True)
        return detections[: self.max_detections]

    def _preprocess(self, frame: "NDArray[np.uint8]") -> "NDArray[np.uint8]":
        """Preprocess frame for model input.

        Args:
            frame: BGR image as numpy array.

        Returns:
            Preprocessed image tensor.
        """
        # Resize to model input size
        resized = cv2.resize(frame, self.input_size)

        # Convert BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        # Add batch dimension
        return np.expand_dims(rgb, axis=0).astype(np.uint8)

    def _set_input(self, input_tensor: "NDArray[np.uint8]") -> None:
        """Set the input tensor on the interpreter.

        Args:
            input_tensor: Preprocessed input tensor.
        """
        input_index = self._input_details[0]["index"]
        self._interpreter.set_tensor(input_index, input_tensor)

    def _parse_output(self) -> list[Detection]:
        """Parse model output into Detection objects.

        Returns:
            List of Detection objects with normalized bounding boxes.
        """
        detections = []

        # Get output tensors
        # Standard SSD output format:
        # - boxes: [1, num_detections, 4] - normalized [y1, x1, y2, x2]
        # - classes: [1, num_detections]
        # - scores: [1, num_detections]
        # - num_detections: scalar

        try:
            boxes = self._interpreter.get_tensor(self._output_details[0]["index"])[0]
            classes = self._interpreter.get_tensor(self._output_details[1]["index"])[0]
            scores = self._interpreter.get_tensor(self._output_details[2]["index"])[0]

            # Some models have num_detections as 4th output
            if len(self._output_details) > 3:
                num_dets = int(
                    self._interpreter.get_tensor(self._output_details[3]["index"])[0]
                )
            else:
                num_dets = len(scores)

            for i in range(min(num_dets, len(scores))):
                score = float(scores[i])
                if score < self.confidence_threshold:
                    continue

                class_id = int(classes[i])
                label = self._labels.get(class_id, f"class_{class_id}")

                # Boxes are in [y1, x1, y2, x2] format, normalized
                y1, x1, y2, x2 = boxes[i]
                bbox = BoundingBox(
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                    normalized=True,
                )

                detections.append(
                    Detection(
                        class_id=class_id,
                        label=label,
                        confidence=score,
                        bbox=bbox,
                    )
                )

        except Exception as e:
            logger.error(f"Error parsing detection output: {e}")

        return detections

    def get_stats(self) -> dict:
        """Get detector statistics.

        Returns:
            Dictionary of performance statistics.
        """
        return {
            "status": self._status.name,
            "backend": self._delegate.get_backend().name,
            "model_path": str(self.model_path),
            "input_size": self.input_size,
            "inference_count": self._delegate.stats.inference_count,
            "avg_inference_ms": self._delegate.stats.average_inference_time_ms,
            "estimated_fps": self._delegate.stats.estimated_fps,
        }

    def draw_detections(
        self,
        frame: "NDArray[np.uint8]",
        detections: list[Detection],
        color: tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> "NDArray[np.uint8]":
        """Draw detection boxes and labels on a frame.

        Args:
            frame: BGR image to draw on (modified in place).
            detections: List of detections to draw.
            color: BGR color for boxes and text.
            thickness: Line thickness in pixels.

        Returns:
            The modified frame.
        """
        height, width = frame.shape[:2]

        for det in detections:
            # Get pixel coordinates
            x1, y1, w, h = det.bbox.to_opencv(width, height)
            x2, y2 = x1 + w, y1 + h

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

            # Draw label background
            label = f"{det.label}: {det.confidence:.2f}"
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            cv2.rectangle(
                frame,
                (x1, y1 - text_height - baseline - 5),
                (x1 + text_width, y1),
                color,
                -1,
            )

            # Draw label text
            cv2.putText(
                frame,
                label,
                (x1, y1 - baseline - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
            )

        return frame


def create_detector_from_config(config: dict) -> ObjectDetector | None:
    """Create an ObjectDetector from configuration dictionary.

    Args:
        config: Configuration dictionary with 'detection' section.

    Returns:
        Configured ObjectDetector, or None if disabled.
    """
    detection_config = config.get("detection", {})

    if not detection_config.get("enabled", True):
        logger.info("Object detection disabled in config")
        return None

    # Resolve model path relative to project root
    model_path = detection_config.get(
        "modelPath", "models/ssd_mobilenet_v2_coco_quant_postprocess.tflite"
    )
    labels_path = detection_config.get("labelsPath", "models/coco_labels.txt")

    # Determine if we should force CPU inference
    # Backend options: 'auto', 'coral', 'cpu', 'opencv', 'color'
    backend = detection_config.get("backend", "auto").lower()
    force_cpu = backend == "cpu"

    if backend == "cpu":
        logger.info("Backend set to 'cpu' - forcing CPU inference")
    elif backend == "coral":
        logger.info("Backend set to 'coral' - will attempt TPU inference")
    elif backend == "auto":
        logger.info("Backend set to 'auto' - will use best available")

    detector = ObjectDetector(
        model_path=model_path,
        labels_path=labels_path,
        confidence_threshold=detection_config.get("confidenceThreshold", 0.5),
        target_classes=detection_config.get("targetClasses"),
        max_detections=detection_config.get("maxDetections", 10),
        input_size=(
            detection_config.get("inputWidth", 300),
            detection_config.get("inputHeight", 300),
        ),
        force_cpu=force_cpu,
    )

    return detector
