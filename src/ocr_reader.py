"""
Module 2: OCR Extraction and Alphanumeric Post-Processing.

This module processes cropped license plate regions:
1. Enhances contrast and binarizes plate crops for optimal OCR readability.
2. Performs text extraction using EasyOCR (primary) or PyTesseract / Contour Fallback.
3. Cleans extracted text, resolving common character confusions (e.g. '0' vs 'O', '1' vs 'I').
4. Validates cleaned strings against standard vehicle plate regex patterns.
5. Computes a composite confidence score (OCR confidence + format compliance).
"""

from dataclasses import dataclass
import re
from typing import List, Optional, Tuple, Union
import cv2
import numpy as np

from src.logger import logger
from src.utils import enhance_plate_contrast, resize_image


@dataclass
class OCRResult:
    """
    Standardized return type for OCR text extraction.

    Attributes:
        raw_text: Unprocessed text directly returned by OCR engine.
        clean_text: Normalized, disambiguated alphanumeric string.
        confidence: Composite confidence score between 0.0 and 1.0.
        is_valid: True if clean_text satisfies a valid license plate pattern.
        status: Status indicator ('DETECTED', 'UNREADABLE', 'FAILED').
        engine_used: Name of the OCR engine that produced the result.
    """
    raw_text: str
    clean_text: str
    confidence: float
    is_valid: bool
    status: str
    engine_used: str = "none"


class OCRReader:
    """
    Multi-engine OCR Reader with Plate Preprocessing and Positional Disambiguation.
    """

    # Positional character confusion maps
    ALPHA_CONFUSIONS = {
        "0": "O",
        "1": "I",
        "8": "B",
        "5": "S",
        "2": "Z",
        "6": "G",
    }
    NUMERIC_CONFUSIONS = {
        "O": "0",
        "D": "0",
        "Q": "0",
        "I": "1",
        "L": "1",
        "T": "1",
        "B": "8",
        "S": "5",
        "Z": "2",
        "A": "4",
        "G": "6",
    }

    # Standard Indian HSRP plate regex: 2 Letters (State), 1-2 Digits (RTO), 1-3 Letters, 4 Digits
    STRICT_PLATE_REGEX = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4}$")
    # Generic international / standard alphanumeric plate regex: 5 to 11 alphanumeric characters
    GENERIC_PLATE_REGEX = re.compile(r"^[A-Z0-9]{5,11}$")

    def __init__(self, preferred_engine: str = "auto", gpu: bool = False):
        """
        Initialize the OCR reader.

        Args:
            preferred_engine: 'auto', 'easyocr', 'tesseract', or 'fallback'.
            gpu: Whether to enable GPU acceleration for EasyOCR (default False for CPU).
        """
        self.preferred_engine = preferred_engine
        self.gpu = gpu
        self._easyocr_reader = None
        self._engine_name = "none"

        self._init_engine()

    def _init_engine(self):
        """Attempt to load the preferred or best available OCR engine."""
        if self.preferred_engine in ("auto", "easyocr"):
            try:
                import easyocr  # type: ignore
                logger.info("Initializing EasyOCR engine (CPU mode)...")
                # Initialize English reader with CPU
                self._easyocr_reader = easyocr.Reader(["en"], gpu=self.gpu, verbose=False)
                self._engine_name = "easyocr"
                logger.info("EasyOCR initialized successfully.")
                return
            except Exception as exc:
                logger.debug(f"EasyOCR not available or failed to load: {exc}")

        if self.preferred_engine in ("auto", "tesseract"):
            try:
                import pytesseract  # type: ignore
                # Test pytesseract binary availability
                _ = pytesseract.get_tesseract_version()
                self._engine_name = "tesseract"
                logger.info("PyTesseract initialized successfully.")
                return
            except Exception as exc:
                logger.debug(f"PyTesseract not available: {exc}")

        # High-precision fallback engine (works completely standalone)
        self._engine_name = "cv_template"
        logger.info("Using standalone Computer Vision OCR engine.")

    def preprocess_plate(self, plate_crop: np.ndarray) -> List[np.ndarray]:
        """
        Prepare cropped plate image with multiple thresholding variants to maximize
        OCR character recognition accuracy under varied lighting.

        Args:
            plate_crop: BGR cropped license plate region.

        Returns:
            List[np.ndarray]: List of preprocessed candidate images (grayscale, Otsu, adaptive).
        """
        if plate_crop is None or plate_crop.size == 0:
            return []

        # Standardize height to 120px for optimal OCR character height
        target_height = 120
        resized, _ = resize_image(plate_crop, height=target_height, inter=cv2.INTER_CUBIC)

        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # Contrast enhancement using CLAHE
        enhanced = enhance_plate_contrast(gray)

        # Variant 1: Bilateral filtered grayscale
        filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)

        # Variant 2: Otsu's thresholding
        _, otsu = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # Variant 3: Adaptive thresholding (handles shadows across plate)
        adaptive = cv2.adaptiveThreshold(
            filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 19, 9
        )

        return [resized, filtered, otsu, adaptive]

    def read_plate(self, plate_crop: Optional[np.ndarray]) -> OCRResult:
        """
        Extract and post-process alphanumeric characters from a cropped plate.

        Args:
            plate_crop: BGR image crop of the plate region.

        Returns:
            OCRResult: Extracted text, cleaned string, and composite confidence score.
        """
        if plate_crop is None or plate_crop.size == 0:
            logger.warning("Empty plate crop provided to OCR reader.")
            return OCRResult(
                raw_text="",
                clean_text="UNREADABLE",
                confidence=0.0,
                is_valid=False,
                status="UNREADABLE",
                engine_used="none",
            )

        preprocessed_variants = self.preprocess_plate(plate_crop)
        if not preprocessed_variants:
            return OCRResult(
                raw_text="",
                clean_text="UNREADABLE",
                confidence=0.0,
                is_valid=False,
                status="UNREADABLE",
                engine_used="none",
            )

        raw_candidates: List[Tuple[str, float]] = []

        # Lazy check if EasyOCR became available
        if self._engine_name != "easyocr" and self.preferred_engine in ("auto", "easyocr"):
            try:
                import easyocr
                self._easyocr_reader = easyocr.Reader(["en"], gpu=self.gpu, verbose=False)
                self._engine_name = "easyocr"
            except Exception:
                pass

        # Try EasyOCR
        if self._engine_name == "easyocr" and self._easyocr_reader is not None:
            raw_candidates = self._run_easyocr(preprocessed_variants)

        # Try PyTesseract if EasyOCR didn't produce a high-confidence match
        if not raw_candidates:
            raw_candidates = self._run_tesseract(preprocessed_variants)

        # Fallback to internal contour segmentation
        if not raw_candidates:
            raw_candidates = self._run_cv_fallback(preprocessed_variants)

        # Evaluate and disambiguate best text candidate
        if not raw_candidates:
            logger.info("OCR engine extracted no alphanumeric characters; marking UNREADABLE.")
            return OCRResult(
                raw_text="",
                clean_text="UNREADABLE",
                confidence=0.0,
                is_valid=False,
                status="UNREADABLE",
                engine_used=self._engine_name,
            )

        # Select highest scoring candidate after cleaning
        best_result = self._select_best_candidate(raw_candidates)
        return best_result

    def _run_easyocr(self, variants: List[np.ndarray]) -> List[Tuple[str, float]]:
        """Run EasyOCR over preprocessed variants."""
        results = []
        for img in variants[:2]:  # Test RGB/Grayscale variants
            try:
                detections = self._easyocr_reader.readtext(
                    img,
                    detail=1,
                    paragraph=False,
                    allowlist="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                )
                if detections:
                    # Combine all detected words on plate
                    full_text = "".join([d[1] for d in detections])
                    avg_conf = float(np.mean([d[2] for d in detections]))
                    if full_text:
                        results.append((full_text, avg_conf))
            except Exception as exc:
                logger.debug(f"EasyOCR iteration error: {exc}")
        return results

    def _run_tesseract(self, variants: List[np.ndarray]) -> List[Tuple[str, float]]:
        """Run PyTesseract over preprocessed variants."""
        results = []
        try:
            import pytesseract  # type: ignore

            config = (
                "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            )
            for img in variants:
                text = pytesseract.image_to_string(img, config=config)
                clean = re.sub(r"[^A-Z0-9]", "", text.upper())
                if clean:
                    data = pytesseract.image_to_data(
                        img, config=config, output_type=pytesseract.Output.DICT
                    )
                    confs = [
                        float(c)
                        for c in data["conf"]
                        if str(c).replace(".", "", 1).isdigit() and float(c) > 0
                    ]
                    avg_conf = (float(np.mean(confs)) / 100.0) if confs else 0.70
                    results.append((clean, avg_conf))
        except Exception:
            pass
        return results

    def _get_templates(self) -> Dict[str, np.ndarray]:
        """
        Generate or retrieve standardized binary templates for characters '0'-'9' and 'A'-'Z'.
        Uses OpenCV font rendering to create high-contrast templates for template matching.
        """
        if hasattr(self, "_char_templates") and self._char_templates:
            return self._char_templates

        templates: Dict[str, np.ndarray] = {}
        target_w, target_h = 32, 48
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        for ch in chars:
            canvas = np.zeros((target_h, target_w), dtype=np.uint8)
            font = cv2.FONT_HERSHEY_DUPLEX
            scale = 1.1
            thickness = 2
            (tw, th), baseline = cv2.getTextSize(ch, font, scale, thickness)
            tx = max(0, int((target_w - tw) / 2))
            ty = max(0, int((target_h + th) / 2) - 2)
            cv2.putText(canvas, ch, (tx, ty), font, scale, 255, thickness, cv2.LINE_AA)
            templates[ch] = canvas

        self._char_templates = templates
        return templates

    def _run_cv_fallback(self, variants: List[np.ndarray]) -> List[Tuple[str, float]]:
        """
        Standalone Computer Vision contour character segmenter and template matcher.
        Extracts individual character bounding boxes left-to-right and matches against
        alphanumeric character glyphs via normalized cross-correlation (TM_CCOEFF_NORMED).
        """
        if len(variants) < 3:
            return []

        # Use Otsu binarization
        otsu = variants[2].copy()
        plate_h, plate_w = otsu.shape[:2]

        # Strip outer border of the plate crop to eliminate outer rectangular border contour
        m_y = max(4, int(plate_h * 0.10))
        m_x = max(6, int(plate_w * 0.05))
        inner = otsu[m_y : plate_h - m_y, m_x : plate_w - m_x]
        inner_h, inner_w = inner.shape[:2]

        # Check border intensity of inner region to determine polarity
        border_pixels = np.concatenate([inner[0, :], inner[-1, :], inner[:, 0], inner[:, -1]])
        if np.mean(border_pixels) > 127:
            binary_chars = cv2.bitwise_not(inner)
        else:
            binary_chars = inner

        # Find character contours
        contours, _ = cv2.findContours(binary_chars, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return []

        char_boxes = []
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            h_ratio = h / float(inner_h)
            ar = w / float(h) if h > 0 else 0
            if 0.30 <= h_ratio <= 0.92 and 0.18 <= ar <= 2.2:
                # Exclude the IND emblem region if present on far left
                if x < 48 and w < 35:
                    continue
                char_boxes.append((x, y, w, h))

        if len(char_boxes) < 4:
            return []

        # Sort characters strictly left-to-right
        char_boxes.sort(key=lambda b: b[0])

        # Filter overlapping boxes (keep wider/larger)
        filtered_boxes = []
        for box in char_boxes:
            if not filtered_boxes:
                filtered_boxes.append(box)
                continue
            prev_x, prev_y, prev_w, prev_h = filtered_boxes[-1]
            curr_x, curr_y, curr_w, curr_h = box
            if curr_x < prev_x + int(prev_w * 0.5):
                if curr_h > prev_h:
                    filtered_boxes[-1] = box
            else:
                filtered_boxes.append(box)

        templates = self._get_templates()
        target_w, target_h = 32, 48
        recognized_chars = []
        confidences = []

        for (bx, by, bw, bh) in filtered_boxes:
            char_roi = binary_chars[by : by + bh, bx : bx + bw]
            if char_roi.size == 0:
                continue

            # Place character ROI into centered template canvas preserving aspect ratio
            canvas = np.zeros((target_h, target_w), dtype=np.uint8)
            scale = min((target_h - 6) / float(bh), (target_w - 6) / float(bw))
            rw, rh = max(1, int(bw * scale)), max(1, int(bh * scale))
            resz = cv2.resize(char_roi, (rw, rh), interpolation=cv2.INTER_AREA)
            off_x = (target_w - rw) // 2
            off_y = (target_h - rh) // 2
            canvas[off_y : off_y + rh, off_x : off_x + rw] = resz

            best_char = "?"
            best_score = -1.0

            for ch, tpl in templates.items():
                res = cv2.matchTemplate(canvas, tpl, cv2.TM_CCOEFF_NORMED)
                score = float(res[0][0])
                if score > best_score:
                    best_score = score
                    best_char = ch

            if best_score > 0.15 and best_char != "?":
                recognized_chars.append(best_char)
                confidences.append(max(0.0, best_score))

        if len(recognized_chars) >= 4:
            full_text = "".join(recognized_chars)
            avg_conf = float(np.mean(confidences)) if confidences else 0.80
            return [(full_text, avg_conf)]

        return []

    def clean_plate_text(self, text: str) -> str:
        """
        Clean raw OCR text: strip spaces, punctuation, lowercase, and symbols.

        Args:
            text: Raw extracted OCR string.

        Returns:
            str: Alphanumeric uppercase cleaned string.
        """
        # Uppercase and keep only alphanumeric
        cleaned = re.sub(r"[^A-Za-z0-9]", "", text).upper()

        # Positional disambiguation for Indian license plate formats
        # Format: [AA] [00] [AA] [0000] -> Positions 0-1: Alpha, 2-3: Num, -4 to end: Num
        if 8 <= len(cleaned) <= 10:
            char_list = list(cleaned)

            # First two characters are State Codes (always Alphabetic)
            for i in [0, 1]:
                if char_list[i] in self.ALPHA_CONFUSIONS:
                    char_list[i] = self.ALPHA_CONFUSIONS[char_list[i]]

            # Last 4 characters are always Numeric
            for i in range(len(char_list) - 4, len(char_list)):
                if char_list[i] in self.NUMERIC_CONFUSIONS:
                    char_list[i] = self.NUMERIC_CONFUSIONS[char_list[i]]

            cleaned = "".join(char_list)

        return cleaned

    def _select_best_candidate(
        self, candidates: List[Tuple[str, float]]
    ) -> OCRResult:
        """
        Select the best candidate string based on format compliance and confidence.
        """
        best_ocr: Optional[OCRResult] = None
        max_overall_score = -1.0

        for raw, ocr_conf in candidates:
            cleaned = self.clean_plate_text(raw)
            if not cleaned or len(cleaned) < 4:
                continue

            # Check format match
            is_strict = bool(self.STRICT_PLATE_REGEX.match(cleaned))
            is_generic = bool(self.GENERIC_PLATE_REGEX.match(cleaned))

            format_weight = 1.0 if is_strict else (0.85 if is_generic else 0.50)
            overall_score = (ocr_conf * 0.6) + (format_weight * 0.4)

            if overall_score > max_overall_score:
                max_overall_score = overall_score
                is_valid = is_strict or (is_generic and len(cleaned) >= 6)
                best_ocr = OCRResult(
                    raw_text=raw,
                    clean_text=cleaned,
                    confidence=round(overall_score, 3),
                    is_valid=is_valid,
                    status="DETECTED" if is_valid else "UNREADABLE",
                    engine_used=self._engine_name,
                )

        if best_ocr is None:
            return OCRResult(
                raw_text="",
                clean_text="UNREADABLE",
                confidence=0.0,
                is_valid=False,
                status="UNREADABLE",
                engine_used=self._engine_name,
            )

        return best_ocr
