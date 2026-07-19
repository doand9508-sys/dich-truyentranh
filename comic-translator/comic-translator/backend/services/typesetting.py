"""
Step 4: Automated Typesetting.

Draws the translated Vietnamese text back onto the inpainted (clean) image,
inside each original bounding box. Implements:
  - Word-wrapping to the box width.
  - Dynamic font-size scaling (binary search) so the wrapped block fits the
    box height as well as its width.
  - Center alignment (both horizontally and vertically within the box).

Requires a font file with Vietnamese diacritics support (e.g. Noto Sans,
Be Vietnam Pro). See config.DEFAULT_FONT_PATH.
"""
from pathlib import Path
from typing import List

from PIL import Image, ImageDraw, ImageFont

from config import DEFAULT_FONT_PATH, MIN_FONT_SIZE, MAX_FONT_SIZE
from schemas import BoundingBox, TranslatedBox

LINE_SPACING = 1.15  # multiplier applied to font size for line height


def _load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    """
    Loads a TrueType font, falling back to PIL's built-in bitmap font if the
    configured font file is missing. The bitmap fallback does NOT render
    Vietnamese diacritics correctly — it exists only so the pipeline doesn't
    crash before a proper font (e.g. Noto Sans, Be Vietnam Pro) is installed.
    See backend/assets/fonts/README.md.
    """
    try:
        return ImageFont.truetype(font_path, size)
    except OSError:
        return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
                max_width: int) -> List[str]:
    """Greedy word-wrap: fits as many words per line as max_width allows."""
    words = text.split()
    if not words:
        return [""]

    lines: List[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _measure_block(draw: ImageDraw.ImageDraw, lines: List[str],
                    font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    """Returns (block_width, block_height) for the given wrapped lines."""
    line_height = int(font.size * LINE_SPACING)
    max_line_width = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        max_line_width = max(max_line_width, bbox[2] - bbox[0])
    return max_line_width, line_height * len(lines)


def _fit_text_to_box(
    draw: ImageDraw.ImageDraw, text: str, box_w: int, box_h: int,
    font_path: str, padding: int = 6,
) -> tuple[List[str], ImageFont.FreeTypeFont]:
    """
    Binary-searches the largest font size (within MIN/MAX_FONT_SIZE) whose
    word-wrapped block still fits inside (box_w - padding, box_h - padding).
    """
    available_w = max(box_w - 2 * padding, 10)
    available_h = max(box_h - 2 * padding, 10)

    lo, hi = MIN_FONT_SIZE, MAX_FONT_SIZE
    best_lines: List[str] = [text]
    best_font = _load_font(font_path, MIN_FONT_SIZE)

    while lo <= hi:
        mid = (lo + hi) // 2
        font = _load_font(font_path, mid)
        lines = _wrap_text(draw, text, font, available_w)
        block_w, block_h = _measure_block(draw, lines, font)

        if block_w <= available_w and block_h <= available_h:
            # This size fits — remember it and try a bigger one.
            best_lines, best_font = lines, font
            lo = mid + 1
        else:
            hi = mid - 1

    return best_lines, best_font


def render_translated_text(
    inpainted_image_path: Path,
    boxes: List[BoundingBox],
    translations: List[TranslatedBox],
    output_path: Path,
    font_path: str = DEFAULT_FONT_PATH,
    text_color: tuple = (20, 20, 20, 255),
) -> Path:
    """
    Draws each translated string into its corresponding box on top of the
    inpainted image and writes the final composited page to output_path.
    """
    translation_by_id = {t.id: t.translated_text for t in translations}

    image = Image.open(inpainted_image_path).convert("RGBA")
    draw = ImageDraw.Draw(image)

    for box in boxes:
        text = translation_by_id.get(box.id, "").strip()
        if not text:
            continue

        lines, font = _fit_text_to_box(draw, text, box.w, box.h, font_path)
        _, block_h = _measure_block(draw, lines, font)
        line_height = int(font.size * LINE_SPACING)

        # Vertically center the whole text block within the box.
        start_y = box.y + max((box.h - block_h) // 2, 0)

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_w = bbox[2] - bbox[0]
            # Horizontally center each line within the box.
            start_x = box.x + max((box.w - line_w) // 2, 0)
            y = start_y + i * line_height
            draw.text((start_x, y), line, font=font, fill=text_color)

    image.convert("RGB").save(output_path, "PNG")
    return output_path
