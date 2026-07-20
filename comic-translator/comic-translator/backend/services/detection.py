"""
Step 1: Text Detection & Bounding Boxes.

Three backends are supported:
  - "simulated": a deterministic placeholder that carves plausible speech-bubble
    regions out of the page. Zero extra dependencies — good for local dev/demo
    and for testing the rest of the pipeline without installing OCR models.
  - "gemini": sends the page image to Gemini's vision endpoint and asks it to
    return bounding boxes + the text inside each one, in one call. No heavy
    ML dependency (no PyTorch), so it fits on small hosts like Render's free
    512MB instance. Recommended default for real use.
  - "easyocr": a real, local OCR detector. Swap DETECTION_BACKEND=easyocr
    once `pip install easyocr` is done. Needs ~1-2GB RAM — usually too heavy
    for free-tier hosting, fine for a VPS/paid instance. Lazy-loaded so it's
    not imported unless selected.

To integrate a different/better detector (CRAFT, PaddleOCR, a fine-tuned
manga bubble detector, etc.) just add another branch in `detect_text_boxes`
and keep the same return contract: List[BoundingBox] with pixel coordinates.
"""
import base64
import json
import re
from pathlib import Path
from typing import List

from PIL import Image

from config import DETECTION_BACKEND, GEMINI_API_KEY, GEMINI_MODEL
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


_GEMINI_DETECT_PROMPT = """You are a comic/manga text-region detector.

Look at this comic page image, which is exactly {width}x{height} pixels.
Find every distinct block of text (speech bubbles, captions, sound effects).

Return ONLY a JSON array, no prose, no markdown fences. Each element:
{{"x": <int>, "y": <int>, "w": <int>, "h": <int>, "text": "<exact text found>"}}

Rules:
- x, y, w, h are pixel coordinates in this exact image (top-left origin),
  tightly bounding just that text block (not the whole speech bubble shape).
- "text" is the literal text you read in that region, in its original
  language — do not translate it here.
- List every separate text block as its own entry, in natural reading order.
- If there is no text on the page, return an empty array: []
"""


def _detect_with_gemini(image_path: Path) -> List[BoundingBox]:
    with Image.open(image_path) as img:
        width, height = img.size
        img_rgb = img.convert("RGB")
        # Downscale very large pages a bit to keep the request light; the
        # model still returns coordinates in *this* image's pixel space,
        # which we then use directly against the original file.
        max_dim = 1600
        if max(width, height) > max_dim:
            scale = max_dim / max(width, height)
            img_rgb = img_rgb.resize(
                (int(width * scale), int(height * scale))
            )
        buf_width, buf_height = img_rgb.size

        import io
        buffer = io.BytesIO()
        img_rgb.save(buffer, format="JPEG", quality=85)
        image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    import requests

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": _GEMINI_DETECT_PROMPT.format(
                        width=buf_width, height=buf_height
                    )},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                ],
            }
        ],
        "generationConfig": {"response_mime_type": "application/json"},
    }

    resp = requests.post(url, json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

    cleaned = re.sub(r"^```(json)?", "", raw_text.strip()).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    detections = json.loads(cleaned)

    # Scale coordinates back up if we downscaled the image before sending it.
    scale_x = width / buf_width
    scale_y = height / buf_height

    boxes: List[BoundingBox] = []
    for i, det in enumerate(detections):
        text = (det.get("text") or "").strip()
        if not text:
            continue
        boxes.append(
            BoundingBox(
                id=f"box_{i}",
                x=int(det["x"] * scale_x),
                y=int(det["y"] * scale_y),
                w=int(det["w"] * scale_x),
                h=int(det["h"] * scale_y),
                original_text=text,
            )
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
    if DETECTION_BACKEND == "gemini":
        return _detect_with_gemini(image_path)
    return _detect_simulated(image_path)
