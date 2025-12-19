"""Object Tracking Module - Maintains object position between detections.

This module provides object tracking using OpenCV trackers, designed to
maintain smooth tracking between ML detection frames.

Features:
- Multiple tracker algorithms (KCF, CSRT, MOSSE)
- State machine for tracking lifecycle
- Automatic re-detection on tracking loss
- IoU-based detection matching
- Tracking confidence estimation

Tracking Pipeline:
    1. ObjectDetector finds objects (every N frames)
    2. ObjectTracker maintains position (every frame)
    3. On tracking loss, triggers re-detection
    4. New detections matched to existing tracks via IoU

Usage:
    tracker = ObjectTracker(method="KCF")
    tracker.initialize(frame, detection.bbox)

    while True:
        success, bbox = tracker.update(frame)
        if not success:
            # Trigger re-detection
            break
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

import cv2
import numpy as np

from .detector import BoundingBox, Detection

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class TrackerMethod(Enum):
    """Available OpenCV tracker algorithms."""

    KCF = "KCF"  # Kernelized Correlation Filters - fast, good accuracy
    CSRT = "CSRT"  # Discriminative Correlation Filter - most accurate, slower
    MOSSE = "MOSSE"  # Minimum Output Sum of Squared Error - fastest
    MIL = "MIL"  # Multiple Instance Learning - robust to partial occlusion


class TrackingState(Enum):
    """State of the tracking system."""

    IDLE = auto()  # No object being tracked
    ACQUIRING = auto()  # Waiting for initial detection
    TRACKING = auto()  # Successfully tracking object
    LOST = auto()  # Object lost, searching
    SEARCHING = auto()  # Actively searching for lost object


@dataclass
class TrackingStats:
    """Statistics for tracking performance."""

    frames_tracked: int = 0
    frames_lost: int = 0
    redetection_count: int = 0
    total_tracking_time_ms: float = 0.0
    last_tracking_time_ms: float = 0.0

    @property
    def tracking_ratio(self) -> float:
        """Ratio of frames successfully tracked."""
        total = self.frames_tracked + self.frames_lost
        if total == 0:
            return 0.0
        return self.frames_tracked / total

    @property
    def average_tracking_time_ms(self) -> float:
        """Average tracking time per frame."""
        if self.frames_tracked == 0:
            return 0.0
        return self.total_tracking_time_ms / self.frames_tracked


@dataclass
class TrackedObject:
    """A tracked object with state and history.

    Attributes:
        id: Unique identifier for this track.
        class_id: COCO class ID of the object.
        label: Human-readable class label.
        bbox: Current bounding box.
        confidence: Last known detection confidence.
        state: Current tracking state.
        frames_since_detection: Frames since last ML detection.
        frames_lost: Consecutive frames where tracking failed.
        velocity: Estimated velocity (dx, dy) in normalized coordinates.
    """

    id: int
    class_id: int
    label: str
    bbox: BoundingBox
    confidence: float = 0.0
    state: TrackingState = TrackingState.TRACKING
    frames_since_detection: int = 0
    frames_lost: int = 0
    velocity: tuple[float, float] = (0.0, 0.0)
    _last_center: tuple[float, float] = field(default=(0.0, 0.0), repr=False)

    def update_velocity(self) -> None:
        """Update velocity estimate based on position change."""
        current_center = self.bbox.center
        if self._last_center != (0.0, 0.0):
            dx = current_center[0] - self._last_center[0]
            dy = current_center[1] - self._last_center[1]
            # Smooth velocity estimate
            alpha = 0.3
            self.velocity = (
                alpha * dx + (1 - alpha) * self.velocity[0],
                alpha * dy + (1 - alpha) * self.velocity[1],
            )
        self._last_center = current_center


@dataclass
class ObjectTracker:
    """Object tracker using OpenCV tracking algorithms.

    Maintains object position between ML detection frames using fast
    OpenCV trackers. Supports multiple tracker algorithms with different
    speed/accuracy tradeoffs.

    Attributes:
        method: Tracker algorithm to use.
        iou_threshold: Minimum IoU to match detection with track.
        max_frames_lost: Frames before declaring object lost.
        redetect_on_loss: Whether to trigger re-detection on loss.
    """

    method: TrackerMethod | str = TrackerMethod.KCF
    iou_threshold: float = 0.3
    max_frames_lost: int = 30
    redetect_on_loss: bool = True

    # Internal state
    _tracker: object = field(default=None, repr=False)
    _tracked_object: TrackedObject | None = field(default=None, repr=False)
    _next_track_id: int = field(default=1, repr=False)
    _stats: TrackingStats = field(default_factory=TrackingStats, repr=False)
    _state: TrackingState = field(default=TrackingState.IDLE, repr=False)

    def __post_init__(self) -> None:
        """Initialize the tracker."""
        # Convert string to enum if needed
        if isinstance(self.method, str):
            try:
                self.method = TrackerMethod(self.method.upper())
            except ValueError:
                logger.warning(f"Unknown tracker method: {self.method}, using KCF")
                self.method = TrackerMethod.KCF

    def _create_tracker(self) -> object:
        """Create an OpenCV tracker instance.

        Returns:
            OpenCV tracker object.
        """
        if self.method == TrackerMethod.KCF:
            return cv2.TrackerKCF_create()
        elif self.method == TrackerMethod.CSRT:
            return cv2.TrackerCSRT_create()
        elif self.method == TrackerMethod.MOSSE:
            return cv2.legacy.TrackerMOSSE_create()
        elif self.method == TrackerMethod.MIL:
            return cv2.TrackerMIL_create()
        else:
            logger.warning(f"Unknown tracker method: {self.method}, using KCF")
            return cv2.TrackerKCF_create()

    @property
    def state(self) -> TrackingState:
        """Get the current tracking state."""
        return self._state

    @property
    def stats(self) -> TrackingStats:
        """Get tracking statistics."""
        return self._stats

    @property
    def tracked_object(self) -> TrackedObject | None:
        """Get the currently tracked object."""
        return self._tracked_object

    @property
    def is_tracking(self) -> bool:
        """Check if actively tracking an object."""
        return self._state == TrackingState.TRACKING

    @property
    def needs_detection(self) -> bool:
        """Check if re-detection is needed."""
        if self._state in (TrackingState.IDLE, TrackingState.ACQUIRING):
            return True
        if self._state == TrackingState.LOST and self.redetect_on_loss:
            return True
        return False

    def initialize(
        self,
        frame: "NDArray[np.uint8]",
        bbox: BoundingBox,
        class_id: int = 0,
        label: str = "object",
        confidence: float = 1.0,
    ) -> bool:
        """Initialize tracking on an object.

        Args:
            frame: Current frame (BGR).
            bbox: Bounding box of the object to track.
            class_id: COCO class ID.
            label: Human-readable class label.
            confidence: Detection confidence.

        Returns:
            True if initialization succeeded.
        """
        height, width = frame.shape[:2]
        opencv_bbox = bbox.to_opencv(width, height)

        # Validate bounding box
        x, y, w, h = opencv_bbox
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > width or y + h > height:
            logger.warning(f"Invalid bounding box: {opencv_bbox}")
            return False

        # Create new tracker
        self._tracker = self._create_tracker()

        try:
            success = self._tracker.init(frame, opencv_bbox)
        except Exception as e:
            logger.error(f"Tracker initialization failed: {e}")
            return False

        if not success:
            logger.warning("Tracker initialization returned False")
            return False

        # Create tracked object
        self._tracked_object = TrackedObject(
            id=self._next_track_id,
            class_id=class_id,
            label=label,
            bbox=bbox,
            confidence=confidence,
            state=TrackingState.TRACKING,
        )
        self._next_track_id += 1
        self._state = TrackingState.TRACKING

        logger.debug(
            f"Initialized tracking: id={self._tracked_object.id}, "
            f"label={label}, bbox={opencv_bbox}"
        )

        return True

    def initialize_from_detection(
        self, frame: "NDArray[np.uint8]", detection: Detection
    ) -> bool:
        """Initialize tracking from a Detection object.

        Args:
            frame: Current frame (BGR).
            detection: Detection to track.

        Returns:
            True if initialization succeeded.
        """
        return self.initialize(
            frame=frame,
            bbox=detection.bbox,
            class_id=detection.class_id,
            label=detection.label,
            confidence=detection.confidence,
        )

    def update(
        self, frame: "NDArray[np.uint8]"
    ) -> tuple[bool, BoundingBox | None]:
        """Update tracker with a new frame.

        Args:
            frame: Current frame (BGR).

        Returns:
            Tuple of (success, bbox). bbox is None if tracking failed.
        """
        if self._tracker is None or self._tracked_object is None:
            return False, None

        height, width = frame.shape[:2]
        start_time = time.perf_counter()

        try:
            success, opencv_bbox = self._tracker.update(frame)
        except Exception as e:
            logger.error(f"Tracker update failed: {e}")
            success = False
            opencv_bbox = (0, 0, 0, 0)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._stats.last_tracking_time_ms = elapsed_ms

        if success:
            # Convert back to normalized coordinates
            x, y, w, h = [int(v) for v in opencv_bbox]

            # Validate bounds
            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            w = max(1, min(w, width - x))
            h = max(1, min(h, height - y))

            bbox = BoundingBox(
                x1=x / width,
                y1=y / height,
                x2=(x + w) / width,
                y2=(y + h) / height,
                normalized=True,
            )

            # Update tracked object
            self._tracked_object.bbox = bbox
            self._tracked_object.frames_since_detection += 1
            self._tracked_object.frames_lost = 0
            self._tracked_object.state = TrackingState.TRACKING
            self._tracked_object.update_velocity()

            self._state = TrackingState.TRACKING
            self._stats.frames_tracked += 1
            self._stats.total_tracking_time_ms += elapsed_ms

            return True, bbox

        else:
            # Tracking failed
            self._tracked_object.frames_lost += 1
            self._stats.frames_lost += 1

            if self._tracked_object.frames_lost >= self.max_frames_lost:
                self._tracked_object.state = TrackingState.LOST
                self._state = TrackingState.LOST
                logger.info(
                    f"Object lost after {self._tracked_object.frames_lost} frames"
                )
            else:
                self._tracked_object.state = TrackingState.SEARCHING
                self._state = TrackingState.SEARCHING

            return False, self._tracked_object.bbox

    def update_with_detection(
        self,
        frame: "NDArray[np.uint8]",
        detection: Detection,
    ) -> bool:
        """Update tracker with a new detection.

        Reinitializes the tracker if the detection matches the tracked object,
        or if tracking was lost.

        Args:
            frame: Current frame (BGR).
            detection: New detection to potentially use.

        Returns:
            True if tracker was updated with the detection.
        """
        if self._tracked_object is None:
            # Not tracking anything, initialize with detection
            return self.initialize_from_detection(frame, detection)

        # Check if detection matches current tracked object
        if detection.class_id != self._tracked_object.class_id:
            return False

        # Check IoU overlap
        iou = detection.bbox.iou(self._tracked_object.bbox)

        if iou >= self.iou_threshold or self._state in (
            TrackingState.LOST,
            TrackingState.SEARCHING,
        ):
            # Detection matches or we lost the object - reinitialize
            height, width = frame.shape[:2]
            opencv_bbox = detection.bbox.to_opencv(width, height)

            self._tracker = self._create_tracker()
            try:
                success = self._tracker.init(frame, opencv_bbox)
            except Exception as e:
                logger.error(f"Tracker reinitialization failed: {e}")
                return False

            if success:
                self._tracked_object.bbox = detection.bbox
                self._tracked_object.confidence = detection.confidence
                self._tracked_object.frames_since_detection = 0
                self._tracked_object.frames_lost = 0
                self._tracked_object.state = TrackingState.TRACKING
                self._state = TrackingState.TRACKING
                self._stats.redetection_count += 1

                logger.debug(f"Tracker reinitialized with detection (IoU={iou:.2f})")
                return True

        return False

    def reset(self) -> None:
        """Reset the tracker to idle state."""
        self._tracker = None
        self._tracked_object = None
        self._state = TrackingState.IDLE
        logger.debug("Tracker reset")

    def predict_position(self, frames_ahead: int = 1) -> BoundingBox | None:
        """Predict future position based on velocity.

        Args:
            frames_ahead: Number of frames to predict ahead.

        Returns:
            Predicted bounding box, or None if not tracking.
        """
        if self._tracked_object is None:
            return None

        bbox = self._tracked_object.bbox
        vx, vy = self._tracked_object.velocity

        # Simple linear prediction
        dx = vx * frames_ahead
        dy = vy * frames_ahead

        return BoundingBox(
            x1=bbox.x1 + dx,
            y1=bbox.y1 + dy,
            x2=bbox.x2 + dx,
            y2=bbox.y2 + dy,
            normalized=bbox.normalized,
        )

    def get_search_region(self, scale: float = 2.0) -> BoundingBox | None:
        """Get expanded search region around last known position.

        Useful for limiting detection search area after tracking loss.

        Args:
            scale: How much to expand the bounding box.

        Returns:
            Expanded bounding box, or None if not tracking.
        """
        if self._tracked_object is None:
            return None

        bbox = self._tracked_object.bbox
        cx, cy = bbox.center
        w = bbox.width * scale
        h = bbox.height * scale

        return BoundingBox(
            x1=max(0.0, cx - w / 2),
            y1=max(0.0, cy - h / 2),
            x2=min(1.0, cx + w / 2),
            y2=min(1.0, cy + h / 2),
            normalized=True,
        )

    def draw_tracking(
        self,
        frame: "NDArray[np.uint8]",
        color: tuple[int, int, int] | None = None,
        thickness: int = 2,
    ) -> "NDArray[np.uint8]":
        """Draw tracking visualization on frame.

        Args:
            frame: BGR image to draw on (modified in place).
            color: BGR color for drawing. Auto-selected based on state if None.
            thickness: Line thickness.

        Returns:
            The modified frame.
        """
        if self._tracked_object is None:
            return frame

        height, width = frame.shape[:2]
        bbox = self._tracked_object.bbox

        # Auto-select color based on state
        if color is None:
            if self._state == TrackingState.TRACKING:
                color = (0, 255, 0)  # Green
            elif self._state == TrackingState.SEARCHING:
                color = (0, 255, 255)  # Yellow
            else:
                color = (0, 0, 255)  # Red

        x1, y1, w, h = bbox.to_opencv(width, height)
        x2, y2 = x1 + w, y1 + h

        # Draw bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

        # Draw center crosshair
        cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
        cv2.drawMarker(
            frame, (cx, cy), color, cv2.MARKER_CROSS, 10, thickness
        )

        # Draw label and state
        label = f"{self._tracked_object.label} [{self._state.name}]"
        cv2.putText(
            frame,
            label,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            thickness,
        )

        # Draw velocity vector if moving
        vx, vy = self._tracked_object.velocity
        if abs(vx) > 0.001 or abs(vy) > 0.001:
            scale = 100  # Scale velocity for visualization
            vx_px = int(vx * width * scale)
            vy_px = int(vy * height * scale)
            cv2.arrowedLine(
                frame,
                (cx, cy),
                (cx + vx_px, cy + vy_px),
                (255, 0, 255),  # Magenta
                2,
            )

        return frame


def create_tracker_from_config(config: dict) -> ObjectTracker:
    """Create an ObjectTracker from configuration dictionary.

    Args:
        config: Configuration dictionary with 'tracking' section.

    Returns:
        Configured ObjectTracker.
    """
    tracking_config = config.get("tracking", {})

    return ObjectTracker(
        method=tracking_config.get("method", "KCF"),
        iou_threshold=tracking_config.get("iouThreshold", 0.3),
        max_frames_lost=tracking_config.get("maxTrackingLoss", 30),
        redetect_on_loss=tracking_config.get("redetectOnLoss", True),
    )
