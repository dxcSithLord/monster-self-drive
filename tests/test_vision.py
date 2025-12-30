"""Tests for the vision module - object detection and tracking.

These tests verify the core functionality of the object detection and
tracking system, with mocked hardware dependencies for CI/CD compatibility.
"""

import numpy as np
import pytest

from src.vision.detector import BoundingBox, Detection, COCO_LABELS
from src.vision.tracker import ObjectTracker, TrackerMethod, TrackingState
from src.vision.tpu_delegate import TPUBackend, TPUDelegate


class TestBoundingBox:
    """Tests for BoundingBox data class."""

    def test_creation_normalized(self):
        """Test creating a normalized bounding box."""
        bbox = BoundingBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6, normalized=True)
        assert bbox.normalized is True
        assert bbox.width == pytest.approx(0.4)
        assert bbox.height == pytest.approx(0.4)

    def test_creation_pixels(self):
        """Test creating a pixel bounding box."""
        bbox = BoundingBox(x1=100, y1=200, x2=300, y2=400, normalized=False)
        assert bbox.normalized is False
        assert bbox.width == 200
        assert bbox.height == 200

    def test_center(self):
        """Test center point calculation."""
        bbox = BoundingBox(x1=0.0, y1=0.0, x2=1.0, y2=1.0)
        cx, cy = bbox.center
        assert cx == pytest.approx(0.5)
        assert cy == pytest.approx(0.5)

    def test_area(self):
        """Test area calculation."""
        bbox = BoundingBox(x1=0.0, y1=0.0, x2=0.5, y2=0.5)
        assert bbox.area == pytest.approx(0.25)

    def test_to_pixels(self):
        """Test conversion to pixel coordinates."""
        bbox = BoundingBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6, normalized=True)
        pixel_bbox = bbox.to_pixels(640, 480)

        assert pixel_bbox.normalized is False
        assert pixel_bbox.x1 == pytest.approx(64)
        assert pixel_bbox.y1 == pytest.approx(96)
        assert pixel_bbox.x2 == pytest.approx(320)
        assert pixel_bbox.y2 == pytest.approx(288)

    def test_to_normalized(self):
        """Test conversion to normalized coordinates."""
        bbox = BoundingBox(x1=64, y1=96, x2=320, y2=288, normalized=False)
        norm_bbox = bbox.to_normalized(640, 480)

        assert norm_bbox.normalized is True
        assert norm_bbox.x1 == pytest.approx(0.1)
        assert norm_bbox.y1 == pytest.approx(0.2)
        assert norm_bbox.x2 == pytest.approx(0.5)
        assert norm_bbox.y2 == pytest.approx(0.6)

    def test_to_opencv(self):
        """Test conversion to OpenCV format (x, y, w, h)."""
        bbox = BoundingBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6, normalized=True)
        x, y, w, h = bbox.to_opencv(640, 480)

        assert x == 64
        assert y == 96
        assert w == 256
        assert h == 192

    def test_iou_identical(self):
        """Test IoU of identical boxes."""
        bbox1 = BoundingBox(x1=0.1, y1=0.1, x2=0.5, y2=0.5)
        bbox2 = BoundingBox(x1=0.1, y1=0.1, x2=0.5, y2=0.5)
        assert bbox1.iou(bbox2) == pytest.approx(1.0)

    def test_iou_no_overlap(self):
        """Test IoU of non-overlapping boxes."""
        bbox1 = BoundingBox(x1=0.0, y1=0.0, x2=0.3, y2=0.3)
        bbox2 = BoundingBox(x1=0.5, y1=0.5, x2=0.8, y2=0.8)
        assert bbox1.iou(bbox2) == pytest.approx(0.0)

    def test_iou_partial_overlap(self):
        """Test IoU of partially overlapping boxes."""
        bbox1 = BoundingBox(x1=0.0, y1=0.0, x2=0.5, y2=0.5)
        bbox2 = BoundingBox(x1=0.25, y1=0.25, x2=0.75, y2=0.75)

        # Intersection: 0.25 * 0.25 = 0.0625
        # Union: 0.25 + 0.25 - 0.0625 = 0.4375
        # IoU: 0.0625 / 0.4375 ≈ 0.143
        assert bbox1.iou(bbox2) == pytest.approx(0.143, rel=0.01)


class TestDetection:
    """Tests for Detection data class."""

    def test_creation(self):
        """Test creating a detection."""
        bbox = BoundingBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6)
        det = Detection(class_id=1, label="person", confidence=0.95, bbox=bbox)

        assert det.class_id == 1
        assert det.label == "person"
        assert det.confidence == 0.95
        assert det.bbox == bbox

    def test_repr(self):
        """Test string representation."""
        bbox = BoundingBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6)
        det = Detection(class_id=1, label="person", confidence=0.95, bbox=bbox)

        repr_str = repr(det)
        assert "person" in repr_str
        assert "0.95" in repr_str


class TestCOCOLabels:
    """Tests for COCO label constants."""

    def test_person_label(self):
        """Test that person class is defined."""
        assert COCO_LABELS.get(1) == "person"

    def test_common_classes(self):
        """Test common COCO classes are present."""
        assert "car" in COCO_LABELS.values()
        assert "dog" in COCO_LABELS.values()
        assert "cat" in COCO_LABELS.values()


class TestTPUDelegate:
    """Tests for TPU delegate - mocked for CI/CD."""

    def test_creation(self):
        """Test TPUDelegate can be created."""
        delegate = TPUDelegate()
        assert delegate is not None

    def test_backend_detection(self):
        """Test backend detection doesn't crash."""
        delegate = TPUDelegate()
        backend = delegate.get_backend()
        assert backend in TPUBackend

    def test_is_available(self):
        """Test availability check."""
        delegate = TPUDelegate()
        # May or may not be available depending on environment
        result = delegate.is_available()
        assert isinstance(result, bool)

    def test_stats_initial(self):
        """Test initial stats are zero."""
        delegate = TPUDelegate()
        assert delegate.stats.inference_count == 0
        assert delegate.stats.total_inference_time_ms == 0.0

    def test_list_tpus(self):
        """Test listing TPUs doesn't crash."""
        delegate = TPUDelegate()
        tpus = delegate.list_tpus()
        assert isinstance(tpus, list)


class TestObjectTracker:
    """Tests for ObjectTracker."""

    @pytest.fixture
    def sample_frame(self):
        """Create a sample frame for testing."""
        return np.zeros((480, 640, 3), dtype=np.uint8)

    @pytest.fixture
    def sample_bbox(self):
        """Create a sample bounding box."""
        return BoundingBox(x1=0.2, y1=0.2, x2=0.4, y2=0.4, normalized=True)

    def test_creation_default(self):
        """Test creating tracker with defaults."""
        tracker = ObjectTracker()
        assert tracker.method == TrackerMethod.KCF
        assert tracker.state == TrackingState.IDLE

    def test_creation_csrt(self):
        """Test creating CSRT tracker."""
        tracker = ObjectTracker(method="CSRT")
        assert tracker.method == TrackerMethod.CSRT

    def test_creation_from_enum(self):
        """Test creating tracker from enum."""
        tracker = ObjectTracker(method=TrackerMethod.MOSSE)
        assert tracker.method == TrackerMethod.MOSSE

    def test_initial_state(self):
        """Test initial tracker state."""
        tracker = ObjectTracker()
        assert tracker.state == TrackingState.IDLE
        assert tracker.tracked_object is None
        assert not tracker.is_tracking

    def test_needs_detection_initial(self):
        """Test needs_detection is True initially."""
        tracker = ObjectTracker()
        assert tracker.needs_detection is True

    def test_initialize(self, sample_frame, sample_bbox):
        """Test tracker initialization."""
        tracker = ObjectTracker()
        success = tracker.initialize(
            frame=sample_frame,
            bbox=sample_bbox,
            class_id=1,
            label="person",
            confidence=0.9,
        )

        assert success is True
        assert tracker.state == TrackingState.TRACKING
        assert tracker.tracked_object is not None
        assert tracker.tracked_object.label == "person"

    def test_initialize_from_detection(self, sample_frame, sample_bbox):
        """Test initialization from Detection object."""
        detection = Detection(
            class_id=1, label="person", confidence=0.9, bbox=sample_bbox
        )
        tracker = ObjectTracker()
        success = tracker.initialize_from_detection(sample_frame, detection)

        assert success is True
        assert tracker.is_tracking is True

    def test_update_after_init(self, sample_frame, sample_bbox):
        """Test update after initialization."""
        tracker = ObjectTracker()
        tracker.initialize(sample_frame, sample_bbox, 1, "person", 0.9)

        success, bbox = tracker.update(sample_frame)
        # With a blank frame, tracking may succeed or fail
        assert isinstance(success, bool)

    def test_reset(self, sample_frame, sample_bbox):
        """Test tracker reset."""
        tracker = ObjectTracker()
        tracker.initialize(sample_frame, sample_bbox, 1, "person", 0.9)
        tracker.reset()

        assert tracker.state == TrackingState.IDLE
        assert tracker.tracked_object is None

    def test_stats_tracking(self, sample_frame, sample_bbox):
        """Test stats are updated during tracking."""
        tracker = ObjectTracker()
        tracker.initialize(sample_frame, sample_bbox, 1, "person", 0.9)
        tracker.update(sample_frame)

        stats = tracker.stats
        assert stats.frames_tracked >= 0
        assert stats.frames_lost >= 0

    def test_predict_position(self, sample_frame, sample_bbox):
        """Test position prediction."""
        tracker = ObjectTracker()
        tracker.initialize(sample_frame, sample_bbox, 1, "person", 0.9)

        predicted = tracker.predict_position(frames_ahead=5)
        assert predicted is not None
        assert predicted.normalized is True

    def test_get_search_region(self, sample_frame, sample_bbox):
        """Test search region expansion."""
        tracker = ObjectTracker()
        tracker.initialize(sample_frame, sample_bbox, 1, "person", 0.9)

        region = tracker.get_search_region(scale=2.0)
        assert region is not None
        assert region.width > sample_bbox.width
        assert region.height > sample_bbox.height

    def test_invalid_bbox_rejected(self, sample_frame):
        """Test that invalid bounding boxes are rejected."""
        tracker = ObjectTracker()

        # Zero-size box
        bad_bbox = BoundingBox(x1=0.5, y1=0.5, x2=0.5, y2=0.5)
        success = tracker.initialize(sample_frame, bad_bbox, 1, "person", 0.9)
        assert success is False

    def test_draw_tracking(self, sample_frame, sample_bbox):
        """Test drawing doesn't crash."""
        tracker = ObjectTracker()
        tracker.initialize(sample_frame, sample_bbox, 1, "person", 0.9)

        result = tracker.draw_tracking(sample_frame.copy())
        assert result.shape == sample_frame.shape


class TestTrackerFromConfig:
    """Tests for creating tracker from config."""

    def test_create_from_empty_config(self):
        """Test creating tracker from empty config."""
        from src.vision.tracker import create_tracker_from_config

        tracker = create_tracker_from_config({})
        assert tracker is not None
        assert tracker.method == TrackerMethod.KCF

    def test_create_from_config(self):
        """Test creating tracker from config dict."""
        from src.vision.tracker import create_tracker_from_config

        config = {
            "tracking": {
                "method": "CSRT",
                "iouThreshold": 0.5,
                "maxTrackingLoss": 60,
                "redetectOnLoss": False,
            }
        }
        tracker = create_tracker_from_config(config)

        assert tracker.method == TrackerMethod.CSRT
        assert tracker.iou_threshold == 0.5
        assert tracker.max_frames_lost == 60
        assert tracker.redetect_on_loss is False
