"""
Lightweight persistence layer.

For a production deployment you'd back this with Redis/Postgres + S3.
For this reference implementation we use an in-memory dict + local disk,
which is enough to demonstrate the full pipeline end-to-end.
"""
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from config import ORIGINALS_DIR, INPAINTED_DIR, FINAL_DIR
from schemas import BoundingBox, TranslatedBox


class ImageRecord:
    """Everything the backend knows about a single uploaded page."""

    def __init__(self, image_id: str, order: int, original_path: Optional[Path] = None):
        self.image_id = image_id
        self.order = order
        self.original_path = original_path
        self.inpainted_path: Optional[Path] = None
        self.final_path: Optional[Path] = None
        self.boxes: List[BoundingBox] = []
        self.translations: List[TranslatedBox] = []
        self.status: str = "uploaded"  # uploaded -> detected -> translated -> rendered


# image_id -> ImageRecord. Simple process-lifetime store.
REGISTRY: Dict[str, ImageRecord] = {}


def new_image_id() -> str:
    return uuid.uuid4().hex[:12]


def register_image(order: int, original_path: Optional[Path] = None) -> ImageRecord:
    image_id = new_image_id()
    record = ImageRecord(image_id, order, original_path)
    REGISTRY[image_id] = record
    return record


def get_image(image_id: str) -> ImageRecord:
    record = REGISTRY.get(image_id)
    if record is None:
        raise KeyError(f"Unknown image_id: {image_id}")
    return record


def all_images_ordered() -> List[ImageRecord]:
    return sorted(REGISTRY.values(), key=lambda r: r.order)


def original_file_path(image_id: str, ext: str) -> Path:
    return ORIGINALS_DIR / f"{image_id}.{ext}"


def inpainted_file_path(image_id: str) -> Path:
    return INPAINTED_DIR / f"{image_id}.png"


def final_file_path(image_id: str) -> Path:
    return FINAL_DIR / f"{image_id}.png"
