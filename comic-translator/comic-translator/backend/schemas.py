"""
Pydantic models shared across routers/services.
Keeping them in one place avoids circular imports between main.py and services/*.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """A single detected text region, in absolute pixel coordinates."""
    id: str                      # stable id so we can map translations back, e.g. "box_0"
    x: int
    y: int
    w: int
    h: int
    original_text: str = ""      # OCR output (may be empty for the simulated backend)


class DetectResponse(BaseModel):
    image_id: str
    width: int
    height: int
    boxes: List[BoundingBox]


class TranslateRequest(BaseModel):
    image_id: str
    boxes: List[BoundingBox]
    # Optional style hints the frontend/user can tweak
    tone: str = "natural, emotional, youth-friendly"


class TranslatedBox(BaseModel):
    id: str
    translated_text: str


class TranslateResponse(BaseModel):
    image_id: str
    translations: List[TranslatedBox]


class RenderRequest(BaseModel):
    image_id: str
    boxes: List[BoundingBox]
    translations: List[TranslatedBox]


class RenderResponse(BaseModel):
    image_id: str
    final_image_url: str


class UploadResponse(BaseModel):
    image_id: str
    original_url: str
    order: int
    width: int
    height: int
