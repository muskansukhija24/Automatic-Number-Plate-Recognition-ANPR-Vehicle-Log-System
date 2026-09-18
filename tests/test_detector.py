"""
Unit Tests for Module 1: PlateDetector & Preprocessing Helpers.
"""

import os
import numpy as np
import pytest

from src.detector import PlateDetector, PlateDetectionResult
from src.utils import four_point_transform, load_image, order_points, resize_image


@pytest.fixture
def detector():
    """Fixture returning a PlateDetector instance."""
    return PlateDetector()


@pytest.fixture
def sample_image_dir():
    """Path to sample test images directory."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample_images")


class TestPlateDetector:
    """Test suite for PlateDetector classical CV pipeline."""

    def test_init_defaults(self, detector):
        """Test default parameter initialization."""
        assert detector.min_aspect_ratio == 1.8
        assert detector.max_aspect_ratio == 7.5
        assert detector.canonical_width == 800

    def test_detect_standard_plate(self, detector, sample_image_dir):
        """Test plate localization on standard front car scene."""
        img_path = os.path.join(sample_image_dir, "plate_standard_01.jpg")
        if not os.path.exists(img_path):
            pytest.skip("Sample test image not found.")

        result = detector.detect(img_path)
        assert isinstance(result, PlateDetectionResult)
        assert result.is_detected is True
        assert result.plate_crop is not None
        assert result.bbox is not None
        x, y, w, h = result.bbox
        assert w > 0 and h > 0
        assert detector.min_aspect_ratio <= result.aspect_ratio <= detector.max_aspect_ratio
        assert result.confidence > 0.50

    def test_detect_angled_plate(self, detector, sample_image_dir):
        """Test plate localization on perspective-skewed car scene."""
        img_path = os.path.join(sample_image_dir, "plate_angled_skew.jpg")
        if not os.path.exists(img_path):
            pytest.skip("Sample test image not found.")

        result = detector.detect(img_path)
        assert isinstance(result, PlateDetectionResult)
        assert result.is_detected is True
        assert result.plate_crop is not None
        assert result.polygon is not None

    def test_detect_no_plate_scenery(self, detector, sample_image_dir):
        """Test negative control image without plate degrades gracefully."""
        img_path = os.path.join(sample_image_dir, "no_plate_scenery.jpg")
        if not os.path.exists(img_path):
            pytest.skip("Sample test image not found.")

        result = detector.detect(img_path)
        assert isinstance(result, PlateDetectionResult)
        assert result.is_detected is False
        assert result.plate_crop is None
        assert "No plate found" in result.message

    def test_detect_nonexistent_file(self, detector):
        """Test non-existent file path returns graceful failure without crashing."""
        result = detector.detect("non_existent_file_xyz_123.jpg")
        assert isinstance(result, PlateDetectionResult)
        assert result.is_detected is False
        assert "Invalid image input" in result.message

    def test_detect_empty_array(self, detector):
        """Test empty numpy array input degrades gracefully."""
        empty = np.array([], dtype=np.uint8)
        result = detector.detect(empty)
        assert isinstance(result, PlateDetectionResult)
        assert result.is_detected is False


class TestUtils:
    """Test suite for geometric and utility helpers."""

    def test_resize_image_proportional(self):
        """Test image resizing maintains aspect ratio."""
        img = np.zeros((400, 800, 3), dtype=np.uint8)
        resized, scale = resize_image(img, width=400)
        assert resized.shape == (200, 400, 3)
        assert scale == 0.5

    def test_order_points(self):
        """Test 4-point coordinate ordering: [TL, TR, BR, BL]."""
        pts = np.array([[100, 200], [0, 0], [100, 0], [0, 200]], dtype="float32")
        ordered = order_points(pts)
        np.testing.assert_array_equal(ordered[0], [0, 0])      # TL
        np.testing.assert_array_equal(ordered[1], [100, 0])    # TR
        np.testing.assert_array_equal(ordered[2], [100, 200])  # BR
        np.testing.assert_array_equal(ordered[3], [0, 200])    # BL

    def test_four_point_transform(self):
        """Test perspective warping flattens tilted quad."""
        img = np.full((300, 400, 3), 128, dtype=np.uint8)
        pts = np.array([[20, 20], [380, 40], [360, 180], [40, 160]], dtype="float32")
        warped = four_point_transform(img, pts)
        assert warped is not None
        assert warped.shape[0] > 0 and warped.shape[1] > 0
