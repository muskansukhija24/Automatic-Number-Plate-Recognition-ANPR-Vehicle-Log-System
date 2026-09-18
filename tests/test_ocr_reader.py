"""
Unit Tests for Module 2: OCRReader, Text Cleaning & Positional Disambiguation.
"""

import numpy as np
import pytest

from src.ocr_reader import OCRReader, OCRResult


@pytest.fixture
def ocr():
    """Fixture returning an OCRReader instance in fallback / auto mode."""
    return OCRReader(preferred_engine="fallback")


class TestOCRReader:
    """Test suite for OCR extraction, cleaning, and regex validation."""

    def test_clean_plate_text_basic(self, ocr):
        """Test stripping of whitespace, punctuation, and casing normalization."""
        raw = " dl - 01 - ab - 1234 "
        cleaned = ocr.clean_plate_text(raw)
        assert cleaned == "DL01AB1234"

    def test_clean_plate_positional_disambiguation(self, ocr):
        """
        Test correction of common OCR letter/digit confusions based on
        known standard license plate syntax: [AA][00][AA][0000].
        """
        # State letters confused with digits ('0' -> 'O', '1' -> 'I')
        # Number digits confused with letters ('O' -> '0', 'B' -> '8')
        corrupted = "0L01AB123B"  # '0' in state prefix, 'B' at end of 4 digits
        corrected = ocr.clean_plate_text(corrupted)
        assert corrected == "OL01AB1238"

    def test_regex_strict_matching(self, ocr):
        """Test standard plate format validation against strict Indian HSRP regex."""
        valid_plates = ["DL01AB1234", "MH12DE1433", "KA05NB9876", "HR26BR5555"]
        for p in valid_plates:
            assert bool(ocr.STRICT_PLATE_REGEX.match(p)) is True

        invalid_plates = ["1234", "ABC", "DL01", "INVALID_PLATE_STRING"]
        for p in invalid_plates:
            assert bool(ocr.STRICT_PLATE_REGEX.match(p)) is False

    def test_read_plate_none_or_empty(self, ocr):
        """Test that passing None or an empty crop returns UNREADABLE gracefully."""
        res_none = ocr.read_plate(None)
        assert isinstance(res_none, OCRResult)
        assert res_none.clean_text == "UNREADABLE"
        assert res_none.confidence == 0.0
        assert res_none.is_valid is False
        assert res_none.status == "UNREADABLE"

        empty_array = np.array([], dtype=np.uint8)
        res_empty = ocr.read_plate(empty_array)
        assert res_empty.status == "UNREADABLE"

    def test_preprocess_plate_variants(self, ocr):
        """Test that preprocessing generates multiple image threshold variants."""
        sample_crop = np.full((60, 240, 3), 200, dtype=np.uint8)
        variants = ocr.preprocess_plate(sample_crop)
        assert len(variants) == 4
        # Resized height should match target 120px
        assert variants[0].shape[0] == 120
