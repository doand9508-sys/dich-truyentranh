# Comic Translator

Automated comic/manga page translator: upload pages → detect text → erase it
→ translate with an LLM → typeset the Vietnamese translation back onto the
page → download as a ZIP.

## Architecture

```
comic-translator/
├── backend/                  FastAPI (Python)
│   ├── main.py                Routes: /api/upload, /detect, /translate, /render, /download-all
│   ├── config.py               Env-driven settings (LLM provider, paths, fonts, CORS)
│   ├── schemas.py               Pydantic models shared by routes + services
│   ├── storage.py                In-memory registry + on-disk file layout
│   ├── services/
│   │   ├── detection.py           Step 1 — bounding boxes (simulated or EasyOCR)
│   │   ├── inpainting.py           Step 2 — cv2.inpaint erases text
│   │   ├── translation.py           Step 3 — Claude/OpenAI localization call
│   │   └── typesetting.py            Step 4 — PIL wrap/scale/center-draw
│   └── assets/fonts/                Drop a Vietnamese-capable .ttf here
│
└── frontend/                 Next.js 14 (App Router) + TypeScript + Tailwind
    ├── app/page.tsx            Dashboard: orchestrates the whole pipeline
    ├── components/
    │   ├── UploadZone.tsx        Drag-and-drop multi-file input
    │   └── ImageCard.tsx          Thumbnail, order badge, progress, before/after
    └── lib/
        ├── api.ts                  Typed fetch wrappers + processPage() orchestrator
        └── types.ts                 Shared client-side types
```

### Why four endpoints instead of one big `/process` call?

Splitting `upload → detect → translate → render` into separate calls means
the frontend can show *which step* each page is on ("Detecting Text",
"Translating", "Rendering") instead of a single opaque spinner, and a
failure in one step (e.g. the LLM call) doesn't force re-running OCR/upload.
`lib/api.ts#processPage()` chains them for you.

## Backend setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000
```

Add a Vietnamese-capable font (see `backend/assets/fonts/README.md`) before
relying on real output — without one, typesetting falls back to a bitmap
font that can't render diacritics.

To use real OCR instead of the built-in simulated detector:
```bash
pip install easyocr
# then in .env:
DETECTION_BACKEND=easyocr
```

## Frontend setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000 — the backend must be running on
http://localhost:8000 (or whatever `NEXT_PUBLIC_API_URL` points to).

## Extending this reference implementation

- **Detection**: `services/detection.py` — swap in CRAFT, PaddleOCR, or a
  fine-tuned manga bubble detector; keep the `List[BoundingBox]` contract.
- **Translation**: `services/translation.py` — the localization prompt is
  isolated in `SYSTEM_PROMPT`; tune tone/glossary rules there. Batch is
  page-level (all boxes at once) for context + cost efficiency.
- **Typesetting**: `services/typesetting.py` — binary-searches font size
  per box; swap fonts, add stroke/outline, or support vertical text.
- **Persistence**: `storage.py` is in-memory + local disk for demo purposes.
  Swap for Redis/Postgres + S3/GCS for multi-user/production use.
- **Concurrency**: `lib/api.ts#processPage` runs pages sequentially from the
  dashboard; add a concurrency-limited `Promise.all` if you want parallel
  throughput (mind LLM rate limits).
