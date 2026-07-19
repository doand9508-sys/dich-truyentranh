"""
Central configuration for the Comic Translator backend.
All tunables live here so the rest of the codebase never reads os.environ directly.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths -------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
ORIGINALS_DIR = STORAGE_DIR / "originals"
INPAINTED_DIR = STORAGE_DIR / "inpainted"
FINAL_DIR = STORAGE_DIR / "final"
FONTS_DIR = BASE_DIR / "assets" / "fonts"

for d in (ORIGINALS_DIR, INPAINTED_DIR, FINAL_DIR, FONTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# --- LLM Provider --------------------------------------------------------
# "anthropic" or "openai"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# --- Detection -----------------------------------------------------------
# "simulated" (no dependency, good for local dev/demo) or "easyocr"
DETECTION_BACKEND = os.getenv("DETECTION_BACKEND", "simulated")

# --- Typesetting -----------------------------------------------------------
DEFAULT_FONT_PATH = str(FONTS_DIR / "NotoSans-Bold.ttf")  # must support Vietnamese diacritics
MIN_FONT_SIZE = 10
MAX_FONT_SIZE = 42

# --- CORS -----------------------------------------------------------
FRONTEND_ORIGINS = os.getenv(
    "FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")
