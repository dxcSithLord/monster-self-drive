"""Vision module for image processing, object detection, and tracking.

This module provides:
- ObjectDetector: ML-based object detection with Coral TPU support
- ObjectTracker: OpenCV-based object tracking between detections
- TPUDelegate: Hardware abstraction for Google Coral Edge TPU
- BoundingBox, Detection: Data structures for detection results

Phase 2 Implementation (ADR-005):
- Primary: Coral TPU for hardware-accelerated inference (25-30 fps)
- Fallback: CPU TFLite inference (3-5 fps)
- Tracking: OpenCV KCF/CSRT for smooth position maintenance

Usage:
    from src.vision import ObjectDetector, ObjectTracker, Detection

    # Create detector (auto-detects Coral TPU)
    detector = ObjectDetector(
        model_path="models/ssd_mobilenet_v2_coco_quant_postprocess_edgetpu.tflite",
        target_classes=["person"]
    )

    # Create tracker
    tracker = ObjectTracker(method="KCF")

    # Detection loop
    detections = detector.detect(frame)
    if detections:
        tracker.initialize_from_detection(frame, detections[0])

    # Tracking loop (between detections)
    success, bbox = tracker.update(frame)
"""

from .detector import (
    BoundingBox,
    Detection,
    DetectionStatus,
    ObjectDetector,
    create_detector_from_config,
    COCO_LABELS,
)
from .tracker import (
    ObjectTracker,
    TrackedObject,
    TrackerMethod,
    TrackingState,
    TrackingStats,
    create_tracker_from_config,
)
from .tpu_delegate import (
    TPUBackend,
    TPUDelegate,
    TPUStats,
    get_tpu_delegate,
    is_coral_available,
)

__all__ = [
    # Detector
    "ObjectDetector",
    "Detection",
    "DetectionStatus",
    "BoundingBox",
    "COCO_LABELS",
    "create_detector_from_config",
    # Tracker
    "ObjectTracker",
    "TrackedObject",
    "TrackerMethod",
    "TrackingState",
    "TrackingStats",
    "create_tracker_from_config",
    # TPU Delegate
    "TPUDelegate",
    "TPUBackend",
    "TPUStats",
    "get_tpu_delegate",
    "is_coral_available",
]
