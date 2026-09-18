"""
Utility and Image Preprocessing Helpers for ANPR System.
Contains functions for image loading, validation, geometric transformations,
perspective deskewing, and contrast enhancements using OpenCV and NumPy.
"""

import os
from typing import Optional, Tuple, Union
import cv2
import numpy as np

from src.logger import logger


def load_image(image_input: Union[str, np.ndarray]) -> np.ndarray:
    """
    Load and validate an image from a file path or return an existing numpy array.

    Args:
        image_input: File path (str) or loaded image array (numpy.ndarray).

    Returns:
        np.ndarray: BGR image array.

    Raises:
        FileNotFoundError: If the provided file path does not exist on disk.
        ValueError: If the file is not a valid or readable image, or array is empty.
    """
    if isinstance(image_input, np.ndarray):
        if image_input.size == 0:
            raise ValueError("Provided image array is empty.")
        return image_input

    if not isinstance(image_input, str):
        raise TypeError(f"Expected str or np.ndarray, got {type(image_input).__name__}")

    normalized_path = os.path.abspath(image_input)
    if not os.path.isfile(normalized_path):
        logger.error(f"Image file not found: {normalized_path}")
        raise FileNotFoundError(f"Image file not found: '{normalized_path}'")

    # Read image using OpenCV (BGR format)
    image = cv2.imread(normalized_path)
    if image is None:
        logger.error(f"Unable to decode image file: {normalized_path}")
        raise ValueError(
            f"Failed to read image from '{normalized_path}'. The file may be corrupt or an unsupported format."
        )

    logger.debug(f"Loaded image from '{normalized_path}', shape: {image.shape}")
    return image


def save_image(image: np.ndarray, output_path: str) -> str:
    """
    Safely save an image array to disk, creating parent directories if needed.

    Args:
        image: Numpy image array (BGR or Grayscale).
        output_path: Filepath where the image should be saved.

    Returns:
        str: Absolute path of the saved image.
    """
    abs_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    success = cv2.imwrite(abs_path, image)
    if not success:
        raise IOError(f"Failed to write image to '{abs_path}'")
    logger.debug(f"Saved image to '{abs_path}'")
    return abs_path


def resize_image(
    image: np.ndarray,
    width: Optional[int] = None,
    height: Optional[int] = None,
    inter: int = cv2.INTER_AREA,
) -> Tuple[np.ndarray, float]:
    """
    Resize an image maintaining its aspect ratio.

    Args:
        image: Input image array.
        width: Target width in pixels, or None to scale proportionally to height.
        height: Target height in pixels, or None to scale proportionally to width.
        inter: Interpolation method (default cv2.INTER_AREA).

    Returns:
        Tuple[np.ndarray, float]: Resized image and scaling ratio (resized / original).
    """
    (h, w) = image.shape[:2]

    if width is None and height is None:
        return image, 1.0

    if width is None:
        ratio = height / float(h)
        dim = (int(w * ratio), height)
    else:
        ratio = width / float(w)
        dim = (width, int(h * ratio))

    resized = cv2.resize(image, dim, interpolation=inter)
    return resized, ratio


def order_points(pts: np.ndarray) -> np.ndarray:
    """
    Order four 2D coordinates in clockwise order:
    [top-left, top-right, bottom-right, bottom-left].

    Rationale:
    - Sum of coordinates (x + y): top-left has minimum sum, bottom-right has maximum sum.
    - Difference of coordinates (y - x): top-right has minimum diff, bottom-left has maximum diff.

    Args:
        pts: (4, 2) numpy array of quadrilateral corner coordinates.

    Returns:
        np.ndarray: Ordered (4, 2) float32 coordinates.
    """
    pts = pts.reshape(4, 2)
    rect = np.zeros((4, 2), dtype="float32")

    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # Top-left has smallest sum
    rect[2] = pts[np.argmax(s)]  # Bottom-right has largest sum

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]  # Top-right has smallest diff (x > y)
    rect[3] = pts[np.argmax(diff)]  # Bottom-left has largest diff (y > x)

    return rect


def four_point_transform(image: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """
    Perform a 4-point perspective warp on an image region to deskew tilted
    or angled number plates into an upright, planar rectangle.

    Args:
        image: Source image array.
        pts: (4, 2) array of coordinates defining the quadrilateral plate region.

    Returns:
        np.ndarray: Perspective-corrected (deskewed) cropped image.
    """
    rect = order_points(pts)
    (tl, tr, br, bl) = rect

    # Calculate width of new image (max distance between horizontal corners)
    width_a = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    width_b = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    max_width = max(int(width_a), int(width_b))

    # Calculate height of new image (max distance between vertical corners)
    height_a = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    height_b = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    max_height = max(int(height_a), int(height_b))

    # Ensure minimum non-zero dimensions
    max_width = max(max_width, 10)
    max_height = max(max_height, 10)

    # Destination points for planar rectangle
    dst = np.array(
        [
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1],
        ],
        dtype="float32",
    )

    # Compute perspective transform matrix and warp
    transform_matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, transform_matrix, (max_width, max_height))

    return warped


def enhance_plate_contrast(gray_plate: np.ndarray) -> np.ndarray:
    """
    Enhance plate contrast and eliminate lighting inconsistencies using CLAHE
    (Contrast Limited Adaptive Histogram Equalization).

    Args:
        gray_plate: Grayscale single-channel image of the plate.

    Returns:
        np.ndarray: Contrast-enhanced grayscale image.
    """
    if len(gray_plate.shape) == 3:
        gray_plate = cv2.cvtColor(gray_plate, cv2.COLOR_BGR2GRAY)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray_plate)
    return enhanced
