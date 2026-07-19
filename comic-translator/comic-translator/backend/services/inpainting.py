"""
Step 2: Text Inpainting (Erasing).

Builds a binary mask from the detected bounding boxes and uses OpenCV's
Navier-Stokes / Telea inpainting to reconstruct the background underneath
the original text, so the translated text can be typeset on a clean panel.
"""
from pathlib import Path
from typing import List

import cv2
import numpy as np

from schemas import BoundingBox

# Padding (px) added around each box so we also erase anti-aliased text edges
# and thin bubble borders that sit just outside the tight OCR box.
MASK_PADDING = 4


def inpaint_text_regions(
    image_path: Path, boxes: List[BoundingBox], output_path: Path
) -> Path:
    """
    Reads the original image, erases the content under each bounding box via
    inpainting, and writes the cleaned result to output_path (PNG).
    """
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not read image at {image_path}")

    height, width = image.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)

    for box in boxes:
        x0 = max(box.x - MASK_PADDING, 0)
        y0 = max(box.y - MASK_PADDING, 0)
        x1 = min(box.x + box.w + MASK_PADDING, width)
        y1 = min(box.y + box.h + MASK_PADDING, height)
        mask[y0:y1, x0:x1] = 255

    # INPAINT_TELEA: fast marching method, generally cleaner for flat comic
    # backgrounds/screentones than INPAINT_NS. Radius controls how far the
    # algorithm samples surrounding pixels — tune per art style if needed.
    result = cv2.inpaint(image, mask, inpaintRadius=7, flags=cv2.INPAINT_TELEA)

    cv2.imwrite(str(output_path), result)
    return output_path
