"""
Comic Translator — FastAPI backend entrypoint.

Pipeline is exposed as four separate, stateful endpoints (upload -> detect ->
translate -> render) rather than one monolithic call. This lets the frontend
show granular per-image progress ("Detecting Text" / "Translating" /
"Rendering") and lets each step be retried independently if it fails.

Run locally:
    uvicorn main:app --reload --port 8000
"""
import io
import zipfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from config import FRONTEND_ORIGINS, STORAGE_DIR
from schemas import (
    UploadResponse,
    DetectResponse,
    TranslateRequest,
    TranslateResponse,
    RenderRequest,
    RenderResponse,
)
from storage import (
    register_image,
    get_image,
    all_images_ordered,
    original_file_path,
    inpainted_file_path,
    final_file_path,
)
from services.detection import detect_text_boxes
from services.inpainting import inpaint_text_regions
from services.translation import translate_boxes
from services.typesetting import render_translated_text

app = FastAPI(title="Comic Translator API", version="1.0.0")

# --- CORS ---------------------------------------------------------------
# Required because the Next.js dev server (localhost:3000) and this API
# (localhost:8000) run on different origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve stored images directly (originals / inpainted / final) so the
# frontend can render preview <img> tags via simple URLs.
app.mount("/static", StaticFiles(directory=str(STORAGE_DIR)), name="static")


# =========================================================================
# Step 0 — Upload
# =========================================================================
@app.post("/api/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...), order: int = Form(...)):
    """
    Accepts a single page image + its intended order (0-based). Called once
    per file by the frontend so each thumbnail can start its own pipeline
    and progress independently.
    """
    ext = (file.filename.split(".")[-1] if "." in file.filename else "png").lower()
    if ext not in {"png", "jpg", "jpeg", "webp"}:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    contents = await file.read()

    # Validate it's actually a readable image before we persist it.
    try:
        with Image.open(io.BytesIO(contents)) as img:
            width, height = img.size
    except Exception:
        raise HTTPException(400, "Uploaded file is not a valid image")

    record = register_image(order, original_path=None)  # path set below
    dest_path = original_file_path(record.image_id, ext)
    dest_path.write_bytes(contents)
    record.original_path = dest_path

    return UploadResponse(
        image_id=record.image_id,
        original_url=f"/static/originals/{dest_path.name}",
        order=order,
        width=width,
        height=height,
    )


# =========================================================================
# Step 1 — Detect
# =========================================================================
@app.post("/api/detect/{image_id}", response_model=DetectResponse)
async def detect(image_id: str):
    """Runs text detection and returns bounding boxes for the given page."""
    try:
        record = get_image(image_id)
    except KeyError:
        raise HTTPException(404, "Unknown image_id")

    boxes = detect_text_boxes(record.original_path)
    record.boxes = boxes
    record.status = "detected"

    with Image.open(record.original_path) as img:
        width, height = img.size

    return DetectResponse(image_id=image_id, width=width, height=height, boxes=boxes)


# =========================================================================
# Step 2 — Translate
# =========================================================================
@app.post("/api/translate", response_model=TranslateResponse)
async def translate(req: TranslateRequest):
    """
    Calls the LLM to translate all boxes for a page in one batched request
    (see services/translation.py for the localization prompt).
    """
    try:
        record = get_image(req.image_id)
    except KeyError:
        raise HTTPException(404, "Unknown image_id")

    try:
        translations = translate_boxes(req.boxes)
    except Exception as exc:  # noqa: BLE001 — surface LLM/parsing errors to client
        raise HTTPException(502, f"Translation failed: {exc}")

    record.translations = translations
    record.status = "translated"
    return TranslateResponse(image_id=req.image_id, translations=translations)


# =========================================================================
# Step 3 — Render (inpaint + typeset)
# =========================================================================
@app.post("/api/render/{image_id}", response_model=RenderResponse)
async def render(image_id: str, req: RenderRequest):
    """
    Erases original text (inpainting) then draws the translated text back
    onto the cleaned page (typesetting), producing the final output image.
    """
    try:
        record = get_image(image_id)
    except KeyError:
        raise HTTPException(404, "Unknown image_id")

    inpainted_path = inpainted_file_path(image_id)
    inpaint_text_regions(record.original_path, req.boxes, inpainted_path)
    record.inpainted_path = inpainted_path

    final_path = final_file_path(image_id)
    render_translated_text(inpainted_path, req.boxes, req.translations, final_path)
    record.final_path = final_path
    record.status = "rendered"

    return RenderResponse(
        image_id=image_id, final_image_url=f"/static/final/{final_path.name}"
    )


# =========================================================================
# Download — ZIP of all finished pages, in original order
# =========================================================================
@app.get("/api/download-all")
async def download_all():
    records = [r for r in all_images_ordered() if r.final_path is not None]
    if not records:
        raise HTTPException(400, "No rendered images available yet")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, record in enumerate(records, start=1):
            arcname = f"{i:02d}.png"
            zf.write(record.final_path, arcname=arcname)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=comic_translated.zip"},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
