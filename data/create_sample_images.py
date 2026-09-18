"""
Sample Image Generator for ANPR System Evaluation.
Generates realistic vehicle test scenes:
- Standard front plate (DL01AB1234)
- Standard rear yellow plate (MH12DE1433)
- Perspective-angled / skewed plate (KA05NB9876)
- Low-light night plate (HR26BR5555)
- Blurry / degraded plate (UP16Z9999)
- Non-plate negative control scenery
"""

import os
import cv2
import numpy as np


def draw_plate(
    plate_text: str,
    bg_color=(245, 245, 245),
    text_color=(20, 20, 20),
    plate_size=(360, 80),
    border_color=(30, 30, 30),
) -> np.ndarray:
    """Draw an authentic rectangular license plate with border and text."""
    w, h = plate_size
    plate = np.full((h, w, 3), bg_color, dtype=np.uint8)

    # Outer border
    cv2.rectangle(plate, (2, 2), (w - 3, h - 3), border_color, thickness=3)
    cv2.rectangle(plate, (5, 5), (w - 6, h - 6), border_color, thickness=1)

    # IND badge on left
    cv2.rectangle(plate, (8, 8), (40, h - 8), (200, 150, 40), thickness=-1)
    cv2.putText(plate, "IND", (12, int(h * 0.65)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

    # Alphanumeric text centered
    font = cv2.FONT_HERSHEY_DUPLEX
    font_scale = 1.3
    thickness = 3
    text_size, _ = cv2.getTextSize(plate_text, font, font_scale, thickness)
    tx = int((w - 45 - text_size[0]) / 2) + 45
    ty = int((h + text_size[1]) / 2) - 2
    cv2.putText(plate, plate_text, (tx, ty), font, font_scale, text_color, thickness, cv2.LINE_AA)

    return plate


def create_standard_car_scene(
    plate_text: str,
    output_path: str,
    bg_color=(240, 240, 240),
    car_color=(45, 55, 72),
    plate_size=(360, 80),
    pos=(320, 450),
    scene_size=(1000, 700),
):
    """Create a realistic car rear bumper scene containing a license plate."""
    sw, sh = scene_size
    scene = np.zeros((sh, sw, 3), dtype=np.uint8)

    # Upper body / car background
    scene[0:int(sh * 0.65), :] = car_color

    # Road / asphalt background
    scene[int(sh * 0.65):, :] = (60, 60, 65)

    # Bumper grill & lines
    cv2.rectangle(scene, (150, int(sh * 0.45)), (sw - 150, int(sh * 0.68)), (25, 28, 36), -1)
    cv2.rectangle(scene, (140, int(sh * 0.43)), (sw - 140, int(sh * 0.70)), (15, 18, 24), 3)

    # Tail lights
    cv2.circle(scene, (200, int(sh * 0.38)), 45, (30, 30, 210), -1)
    cv2.circle(scene, (sw - 200, int(sh * 0.38)), 45, (30, 30, 210), -1)

    # Draw plate
    plate = draw_plate(plate_text, bg_color=bg_color, plate_size=plate_size)
    pw, ph = plate_size
    px, py = pos

    # Plate mounting frame
    cv2.rectangle(scene, (px - 8, py - 8), (px + pw + 8, py + ph + 8), (10, 10, 10), -1)
    scene[py : py + ph, px : px + pw] = plate

    # Save
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    cv2.imwrite(output_path, scene)
    print(f"Created: {output_path}")


def create_angled_scene(output_path: str):
    """Create an angled/perspective-skewed plate to test 4-point homography deskewing."""
    sw, sh = 1000, 700
    scene = np.zeros((sh, sw, 3), dtype=np.uint8)
    scene[:int(sh * 0.7), :] = (70, 40, 35)  # Car body
    scene[int(sh * 0.7):, :] = (55, 55, 60)  # Asphalt

    # Create plate
    plate = draw_plate("KA 05 NB 9876", bg_color=(250, 250, 250), plate_size=(380, 85))
    ph, pw = plate.shape[:2]

    # Warp perspective (angled view)
    src_pts = np.float32([[0, 0], [pw, 0], [pw, ph], [0, ph]])
    dst_pts = np.float32([[300, 420], [700, 390], [680, 495], [295, 510]])

    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped_plate = cv2.warpPerspective(plate, matrix, (sw, sh))

    # Mask and blend into scene
    gray_warp = cv2.cvtColor(warped_plate, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray_warp, 1, 255, cv2.THRESH_BINARY)
    inv_mask = cv2.bitwise_not(mask)

    scene_bg = cv2.bitwise_and(scene, scene, mask=inv_mask)
    scene = cv2.add(scene_bg, warped_plate)

    cv2.imwrite(output_path, scene)
    print(f"Created: {output_path}")


def create_low_light_scene(output_path: str):
    """Create a night-time / low-light scene."""
    sw, sh = 1000, 700
    scene = np.full((sh, sw, 3), (18, 18, 22), dtype=np.uint8)

    # Subtle vehicle shape
    cv2.rectangle(scene, (200, 320), (800, 520), (28, 28, 34), -1)

    # Dim yellow plate
    plate = draw_plate("HR 26 BR 5555", bg_color=(160, 160, 40), text_color=(15, 15, 15), plate_size=(360, 80))
    # Dim the plate slightly to simulate low lighting
    plate = (plate * 0.65).astype(np.uint8)
    scene[400:480, 320:680] = plate

    # Headlight reflection glow
    cv2.circle(scene, (150, 420), 80, (40, 60, 80), -1)
    cv2.circle(scene, (850, 420), 80, (40, 60, 80), -1)

    cv2.imwrite(output_path, scene)
    print(f"Created: {output_path}")


def create_blurry_scene(output_path: str):
    """Create a heavily blurred and noisy scene to test failure handling."""
    sw, sh = 1000, 700
    scene = np.zeros((sh, sw, 3), dtype=np.uint8)
    scene[:int(sh * 0.65), :] = (50, 50, 50)
    scene[int(sh * 0.65):, :] = (40, 40, 45)

    plate = draw_plate("UP 16 Z 9999", bg_color=(240, 240, 240), plate_size=(360, 80))
    scene[420:500, 320:680] = plate

    # Heavy motion blur
    kernel_size = 35
    kernel = np.zeros((kernel_size, kernel_size))
    kernel[int((kernel_size - 1) / 2), :] = np.ones(kernel_size)
    kernel /= kernel_size
    blurred = cv2.filter2D(scene, -1, kernel)

    # Add Gaussian noise
    noise = np.random.normal(0, 25, blurred.shape).astype(np.uint8)
    noisy = cv2.add(blurred, noise)

    cv2.imwrite(output_path, noisy)
    print(f"Created: {output_path}")


def create_no_plate_scenery(output_path: str):
    """Create a negative control image with no vehicle or license plate."""
    sw, sh = 1000, 700
    scene = np.zeros((sh, sw, 3), dtype=np.uint8)

    # Blue sky
    scene[:350, :] = (235, 180, 130)
    # Green landscape / hills
    scene[350:500, :] = (60, 120, 60)
    # Road
    pts = np.array([[380, 500], [620, 500], [900, 700], [100, 700]], np.int32)
    cv2.fillPoly(scene, [pts], (80, 80, 85))

    cv2.imwrite(output_path, scene)
    print(f"Created: {output_path}")


def main():
    target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_images")
    os.makedirs(target_dir, exist_ok=True)

    create_standard_car_scene(
        "DL 01 AB 1234",
        os.path.join(target_dir, "plate_standard_01.jpg"),
        bg_color=(245, 245, 245),
        car_color=(35, 45, 60),
    )
    create_standard_car_scene(
        "MH 12 DE 1433",
        os.path.join(target_dir, "plate_standard_02.jpg"),
        bg_color=(50, 210, 245),  # Yellow commercial / taxi plate
        car_color=(80, 25, 25),
    )
    create_angled_scene(os.path.join(target_dir, "plate_angled_skew.jpg"))
    create_low_light_scene(os.path.join(target_dir, "plate_low_light.jpg"))
    create_blurry_scene(os.path.join(target_dir, "plate_blurry_noisy.jpg"))
    create_no_plate_scenery(os.path.join(target_dir, "no_plate_scenery.jpg"))
    print("All sample images created successfully.")


if __name__ == "__main__":
    main()
