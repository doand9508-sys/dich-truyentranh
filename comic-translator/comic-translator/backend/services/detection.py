"""
Step 1: Text Detection & Bounding Boxes.

Two backends are supported:
  - "simulated": a deterministic placeholder that carves plausible speech-bubble
    regions out of the page. Zero extra dependencies — good for local dev/demo
    and for testing the rest of the pipeline without installing OCR models.
  - "easyocr": a real, lightweight OCR detector. Swap DETECTION_BACKEND=easyocr
    in .env once `pip install easyocr` is done. Because EasyOCR is heavy to
    import, it's lazy-loaded only when selected.

To integrate a different/better detector (CRAFT, PaddleOCR, a fine-tuned
manga bubble detector, etc.) just add another branch in `detect_text_boxes`
and keep the same return contract: List[BoundingBox] with pixel coordinates.
"""
from pathlib import Path
from typing import List

import numpy as np
from PIL import Image

from config import DETECTION_BACKEND
from schemas import BoundingBox

_easyocr_reader = None  # lazy singleton, avoids paying import cost unless used


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr  # imported lazily; only required if DETECTION_BACKEND=easyocr

        # 'en' + 'ja' cover most source comics (English scanlations / raw manga).
        # Add/remove language codes according to your source material.
        _easyocr_reader = easyocr.Reader(["en", "ja"], gpu=False)
    return _easyocr_reader


def _detect_with_easyocr(image_path: Path) -> List[BoundingBox]:
    reader = _get_easyocr_reader()
    results = reader.readtext(str(image_path))  # [(box_pts, text, confidence), ...]

    boxes: List[BoundingBox] = []
    for i, (pts, text, conf) in enumerate(results):
        if conf < 0.25:
            continue  # drop very low-confidence noise
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x, y = int(min(xs)), int(min(ys))
        w, h = int(max(xs) - x), int(max(ys) - y)
        boxes.append(
            BoundingBox(id=f"box_{i}", x=x, y=y, w=w, h=h, original_text=text)
        )
    return boxes


def _detect_simulated(image_path: Path) -> List[BoundingBox]:
    """
    Deterministic placeholder detector.

    Splits the page into a plausible grid of "speech bubble" regions so the
    rest of the pipeline (inpaint -> translate -> render) can be exercised
    end-to-end without any OCR model installed. Replace this with a real
    detector for production use.
    """
    with Image.open(image_path) as img:
        width, height = img.size

    # A small deterministic layout: two "bubbles" in the upper third,
    # one wide caption box near the bottom. Adjust freely / replace with
    # a real model's output.
    boxes = [
        BoundingBox(
            id="box_0",
            x=int(width * 0.08),
            y=int(height * 0.06),
            w=int(width * 0.34),
            h=int(height * 0.14),
            original_text="Sample detected text A",
        ),
        BoundingBox(
            id="box_1",
            x=int(width * 0.55),
            y=int(height * 0.10),
            w=int(width * 0.34),
            h=int(height * 0.12),
            original_text="Sample detected text B",
        ),
        BoundingBox(
            id="box_2",
            x=int(width * 0.10),
            y=int(height * 0.80),
            w=int(width * 0.80),
            h=int(height * 0.10),
            original_text="Sample caption text C",
        ),
    ]
    return boxes


def detect_text_boxes(image_path: Path) -> List[BoundingBox]:
    """Public entrypoint used by main.py. Dispatches on DETECTION_BACKEND."""
    if DETECTION_BACKEND == "easyocr":
        return _detect_with_easyocr(image_path)
    return _detect_simulated(image_path)
