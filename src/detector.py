"""
Module 1: Plate Detection using Classical Computer Vision (OpenCV).

This module implements classical computer vision techniques to localize vehicle license
plates without relying on heavy deep-learning object detectors:
1. Grayscale conversion and scale-invariant image normalization.
2. Bilateral filtering for edge-preserving noise reduction.
3. Morphological operations (Black-hat / Top-hat) for plate contrast isolation.
4. Edge detection (Canny / Sobel gradient) and morphological closing.
5. Contour analysis, aspect ratio filtering, and extent validation.
6. 4-point perspective transform (homography deskewing).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
import cv2
import numpy as np

from src.logger import logger
from src.utils import four_point_transform, load_image, resize_image


@dataclass
class PlateDetectionResult:
    """
    Standardized return type for license plate localization.

    Attributes:
        is_detected: True if a candidate plate region was successfully localized.
        plate_crop: Cropped and perspective-corrected (deskewed) plate image (BGR), or None.
        bbox: Bounding box tuple (x, y, width, height) in original image coordinates, or None.
        polygon: Ordered 4-point corner coordinates (4, 2) in original image coordinates, or None.
        aspect_ratio: Width / Height aspect ratio of the detected plate candidate.
        confidence: Geometric confidence score (0.0 to 1.0) based on rectangularity and aspect ratio.
        message: Diagnostic description of the localization outcome.
    """
    is_detected: bool
    plate_crop: Optional[np.ndarray] = None
    bbox: Optional[Tuple[int, int, int, int]] = None
    polygon: Optional[np.ndarray] = None
    aspect_ratio: float = 0.0
    confidence: float = 0.0
    message: str = ""


class PlateDetector:
    """
    Classical Computer Vision License Plate Detector.

    Applies a deterministic pipeline of filtering, morphological closing, and contour
    geometry analysis to detect and extract license plates from single images or video frames.
    """

    def __init__(
        self,
        min_aspect_ratio: float = 1.8,
        max_aspect_ratio: float = 7.5,
        min_area_ratio: float = 0.0015,
        max_area_ratio: float = 0.35,
        canonical_width: int = 800,
    ):
        """
        Initialize the detector with geometric constraints.

        Args:
            min_aspect_ratio: Minimum acceptable width-to-height ratio (e.g. 1.8 for 2-line plates).
            max_aspect_ratio: Maximum acceptable width-to-height ratio (e.g. 7.5 for angled/wide HSRP plates).
            min_area_ratio: Minimum fraction of total image area occupied by plate.
            max_area_ratio: Maximum fraction of total image area occupied by plate.
            canonical_width: Internal width to which images are normalized for scale-invariant filtering.
        """
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.canonical_width = canonical_width

    def detect(self, image_input: Union[str, np.ndarray]) -> PlateDetectionResult:
        """
        Locate and extract the vehicle license plate from an image.

        Args:
            image_input: Filepath string or numpy image array (BGR).

        Returns:
            PlateDetectionResult: Structured detection output with deskewed crop and metrics.
        """
        try:
            image = load_image(image_input)
        except Exception as exc:
            logger.warning(f"Plate detection aborted: {exc}")
            return PlateDetectionResult(
                is_detected=False,
                message=f"Invalid image input: {str(exc)}",
            )

        orig_h, orig_w = image.shape[:2]
        total_pixels = orig_h * orig_w

        # Step 1: Normalize image scale for consistent kernel and gradient behaviors
        resized_img, scale = resize_image(image, width=self.canonical_width)
        inv_scale = 1.0 / scale

        # Step 2: Primary Detection Pipeline (Morphological Black-Hat + Canny Edge Analysis)
        candidate = self._detect_via_morphology(resized_img, inv_scale, orig_w, orig_h)
        if candidate is not None:
            return self._finalize_candidate(image, candidate, orig_w, orig_h)

        # Step 3: Secondary Detection Pipeline (Bilateral Filter + Adaptive Thresholding)
        # Fallback for low-contrast, weathered, or non-reflective plates
        candidate_fallback = self._detect_via_adaptive_threshold(resized_img, inv_scale, orig_w, orig_h)
        if candidate_fallback is not None:
            return self._finalize_candidate(image, candidate_fallback, orig_w, orig_h)

        # Step 4: Graceful Degradation - No plate detected
        logger.info("No rectangular contour satisfied license plate geometric constraints.")
        return PlateDetectionResult(
            is_detected=False,
            message="No plate found matching geometric and aspect ratio constraints.",
        )

    def _detect_via_morphology(
        self,
        resized_img: np.ndarray,
        inv_scale: float,
        orig_w: int,
        orig_h: int,
    ) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int], float, float]]:
        """
        Primary pipeline: Grayscale -> Bilateral Filter -> Morphological Black-Hat -> Sobel -> Closing.
        """
        gray = cv2.cvtColor(resized_img, cv2.COLOR_BGR2GRAY)

        # Edge-preserving noise reduction: eliminates texture grain while preserving plate boundaries
        smooth = cv2.bilateralFilter(gray, d=11, sigmaColor=17, sigmaSpace=17)

        # Morphological Black-Hat reveals dark characters against bright plate background
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
        blackhat = cv2.morphologyEx(smooth, cv2.MORPH_BLACKHAT, rect_kernel)

        # Vertical edges highlight alphanumeric vertical strokes on plates
        grad_x = cv2.Sobel(blackhat, ddepth=cv2.CV_32F, dx=1, dy=0, ksize=-1)
        grad_x = np.absolute(grad_x)
        min_val, max_val = np.min(grad_x), np.max(grad_x)
        if max_val > min_val:
            grad_x = 255 * ((grad_x - min_val) / (max_val - min_val))
        grad_x = grad_x.astype("uint8")

        # Blur and Close to fuse characters into a continuous rectangular blob
        grad_x = cv2.GaussianBlur(grad_x, (5, 5), 0)
        close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 5))
        closed = cv2.morphologyEx(grad_x, cv2.MORPH_CLOSE, close_kernel)

        # Otsu automatic thresholding
        _, thresh = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # Morphological opening removes stray non-plate background connections
        clean_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.erode(thresh, clean_kernel, iterations=1)
        thresh = cv2.dilate(thresh, clean_kernel, iterations=2)

        return self._find_best_contour(thresh, resized_img.shape[:2], inv_scale, orig_w, orig_h)

    def _detect_via_adaptive_threshold(
        self,
        resized_img: np.ndarray,
        inv_scale: float,
        orig_w: int,
        orig_h: int,
    ) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int], float, float]]:
        """
        Secondary pipeline: Canny edge detection on contrast-enhanced grayscale.
        """
        gray = cv2.cvtColor(resized_img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 200)

        close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, close_kernel)

        return self._find_best_contour(closed, resized_img.shape[:2], inv_scale, orig_w, orig_h)

    def _find_best_contour(
        self,
        binary_mask: np.ndarray,
        frame_dim: Tuple[int, int],
        inv_scale: float,
        orig_w: int,
        orig_h: int,
    ) -> Optional[Tuple[np.ndarray, Tuple[int, int, int, int], float, float]]:
        """
        Search binary mask for the most viable license plate contour based on geometric properties.
        """
        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Sort contours by area in descending order
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]
        total_area = frame_dim[0] * frame_dim[1]

        best_candidate = None
        best_score = -1.0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            area_ratio = area / float(total_area)

            # Area constraint
            if not (self.min_area_ratio <= area_ratio <= self.max_area_ratio):
                continue

            # Check rotated bounding rectangle
            rect = cv2.minAreaRect(cnt)
            (cx, cy), (rw, rh), angle = rect
            if rw == 0 or rh == 0:
                continue

            # Ensure width is the larger dimension
            width = max(rw, rh)
            height = min(rw, rh)
            aspect_ratio = width / float(height)

            # Aspect ratio constraint
            if not (self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio):
                continue

            # Extent constraint: area / bounding box area
            box_area = width * height
            extent = area / float(box_area) if box_area > 0 else 0
            if extent < 0.35:
                continue

            # Evaluate quadrilateral approximation
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.03 * peri, True)

            # Score candidates based on ideal aspect ratio (around 3.5 - 4.5) and extent
            ideal_ar = 3.8
            ar_diff = abs(aspect_ratio - ideal_ar)
            score = (extent * 0.5) + (max(0.0, 1.0 - (ar_diff / 3.0)) * 0.5)

            if len(approx) == 4:
                score += 0.2  # Bonus for true quadrilateral

            if score > best_score:
                best_score = score

                # Get 4-point coordinates
                if len(approx) == 4:
                    pts = approx.reshape(4, 2)
                else:
                    box = cv2.boxPoints(rect)
                    pts = np.int32(box)

                # Scale coordinates back to original image scale
                orig_pts = (pts * inv_scale).astype("float32")

                # Bounding box in original image coordinates
                min_x = max(0, int(np.min(orig_pts[:, 0])))
                max_x = min(orig_w, int(np.max(orig_pts[:, 0])))
                min_y = max(0, int(np.min(orig_pts[:, 1])))
                max_y = min(orig_h, int(np.max(orig_pts[:, 1])))
                orig_bbox = (min_x, min_y, max_x - min_x, max_y - min_y)

                best_candidate = (orig_pts, orig_bbox, aspect_ratio, min(1.0, score))

        return best_candidate

    def _finalize_candidate(
        self,
        original_image: np.ndarray,
        candidate: Tuple[np.ndarray, Tuple[int, int, int, int], float, float],
        orig_w: int,
        orig_h: int,
    ) -> PlateDetectionResult:
        """
        Crop candidate region with 4-point perspective warp, pad slightly, and wrap in PlateDetectionResult.
        """
        orig_pts, bbox, aspect_ratio, score = candidate

        # Deskew using four point perspective transformation
        try:
            warped = four_point_transform(original_image, orig_pts)
        except Exception as exc:
            logger.warning(f"Perspective transform failed, falling back to axis-aligned crop: {exc}")
            x, y, w, h = bbox
            warped = original_image[y : y + h, x : x + w]

        # Verify crop validity
        if warped is None or warped.size == 0 or warped.shape[0] < 8 or warped.shape[1] < 15:
            logger.warning("Extracted plate crop was empty or degenerate.")
            return PlateDetectionResult(
                is_detected=False,
                message="Extracted region was too small or degenerate.",
            )

        # Slight padding around crop to ensure outer digits are intact
        pad_h = int(warped.shape[0] * 0.05)
        pad_w = int(warped.shape[1] * 0.05)
        if pad_h > 0 and pad_w > 0:
            warped = cv2.copyMakeBorder(
                warped, pad_h, pad_h, pad_w, pad_w, cv2.BORDER_REPLICATE
            )

        logger.info(
            f"License plate detected at bbox={bbox}, aspect_ratio={aspect_ratio:.2f}, "
            f"confidence={score:.2f}"
        )

        return PlateDetectionResult(
            is_detected=True,
            plate_crop=warped,
            bbox=bbox,
            polygon=orig_pts,
            aspect_ratio=aspect_ratio,
            confidence=score,
            message="License plate localized and perspective-corrected successfully.",
        )
