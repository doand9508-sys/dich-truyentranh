"""
Step 3: AI Translation (LLM Integration).

Sends all detected text boxes for a page to the LLM in a single call (cheaper,
faster, and gives the model full-page context for tone/consistency) and asks
for a strict JSON array back so we can map translations to box ids 1:1.
"""
import json
import re
from typing import List

from config import (
    LLM_PROVIDER,
    ANTHROPIC_API_KEY,
    ANTHROPIC_MODEL,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)
from schemas import BoundingBox, TranslatedBox

SYSTEM_PROMPT = """You are an expert comic/manga localizer specializing in \
English/Japanese-to-Vietnamese translation for a youth-oriented digital comic \
platform.

Rules:
1. Translate naturally and emotionally, the way a native Vietnamese reader \
   their late teens/early twenties would actually speak — not a stiff, \
   literal, textbook translation.
2. Preserve tone: shouting stays loud (use "!", capitalization where it \
   fits), hesitation stays hesitant ("...", "ừm"), sound effects stay punchy.
3. Keep each translation reasonably close in LENGTH to the original — it \
   must fit inside a small speech bubble. Prefer short, punchy phrasing over \
   long literal sentences.
4. Preserve honorifics/relationships implied by context (e.g. sibling, \
   senior/junior) using natural Vietnamese address terms (anh/em/chị/cậu...) \
   when inferable; otherwise stay neutral.
5. Do not translate onomatopoeia into overly formal words — keep it punchy \
   (e.g. "BUM", "RẦM", "XOẸT").
6. Output MUST be a JSON array only — no prose, no markdown fences, no \
   explanations. Each element: {"id": "<same id as input>", \
   "translated_text": "<Vietnamese translation>"}.
7. The output array must contain exactly one entry per input entry, in any \
   order, matched by "id". Never merge, drop, or invent boxes.
"""


def _build_user_prompt(boxes: List[BoundingBox]) -> str:
    payload = [{"id": b.id, "text": b.original_text} for b in boxes]
    return (
        "Translate the following comic dialogue/caption boxes from this page "
        "into Vietnamese. Full page context is given so you can keep tone and "
        "continuity consistent across boxes.\n\n"
        f"INPUT:\n{json.dumps(payload, ensure_ascii=False)}\n\n"
        "Respond with the JSON array described in the system prompt and "
        "nothing else."
    )


def _extract_json_array(raw_text: str) -> list:
    """
    Defensively pull a JSON array out of the model's reply, in case it wraps
    it in ```json fences despite instructions, or adds stray whitespace.
    """
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return json.loads(cleaned)


def _translate_with_anthropic(boxes: List[BoundingBox]) -> List[TranslatedBox]:
    import anthropic

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_user_prompt(boxes)}],
    )
    raw_text = "".join(
        block.text for block in message.content if block.type == "text"
    )
    parsed = _extract_json_array(raw_text)
    return [
        TranslatedBox(id=item["id"], translated_text=item["translated_text"])
        for item in parsed
    ]


def _translate_with_openai(boxes: List[BoundingBox]) -> List[TranslatedBox]:
    from openai import OpenAI

    client = OpenAI(api_key=OPENAI_API_KEY)
    completion = client.chat.completions.create(
        model=OPENAI_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT
                + '\nWrap the array in a JSON object as {"translations": [...]}.'},
            {"role": "user", "content": _build_user_prompt(boxes)},
        ],
    )
    raw_text = completion.choices[0].message.content
    parsed = json.loads(raw_text)
    items = parsed["translations"] if isinstance(parsed, dict) else parsed
    return [
        TranslatedBox(id=item["id"], translated_text=item["translated_text"])
        for item in items
    ]


def translate_boxes(boxes: List[BoundingBox]) -> List[TranslatedBox]:
    """Public entrypoint used by main.py. Dispatches on LLM_PROVIDER."""
    if not boxes:
        return []

    if LLM_PROVIDER == "openai":
        return _translate_with_openai(boxes)
    return _translate_with_anthropic(boxes)
