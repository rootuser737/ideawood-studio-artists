"""Optional photoreal image generation through any OpenAI-compatible images endpoint (the artist's own key).

The built-in generative visuals (generative.py) need no key. This adds true AI-generated pictures per scene
(``POST {base}/images/generations``). Pictures become normal image scenes (Ken-Burns). The key never leaves the PC
except to the endpoint the artist configured. No Qt.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request
from typing import Optional

DEFAULT_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-image-1"
STYLE_SUFFIX = ("cinematic background for a music lyric video, rich colour, soft depth of field, enough dark areas for "
                "white text on top, no text, no letters, no logos, no watermark, no close-up faces")


class ImageGenError(Exception):
    pass


def size_for(orientation: Optional[str], model: str) -> str:
    dalle3 = model.startswith("dall-e-3")
    if orientation == "vertical":
        return "1024x1792" if dalle3 else "1024x1536"
    if orientation == "horizontal":
        return "1792x1024" if dalle3 else "1536x1024"
    return "1024x1024"


def build_prompt(brief: str, scene_theme: str, mood: str = "", genre: str = "") -> str:
    parts = [brief.strip(), f"Theme of this part of the song: {scene_theme.strip()}" if scene_theme.strip() else "",
             f"Mood: {mood.strip()}" if mood.strip() else "", f"Genre: {genre.strip()}" if genre.strip() else "", STYLE_SUFFIX]
    return ". ".join(x for x in parts if x)[:1500]


def generate_image(prompt: str, dest_no_ext: str, api_key: str, base_url: str = DEFAULT_BASE,
                   model: str = DEFAULT_MODEL, size: str = "1536x1024", timeout: int = 240) -> str:
    if not api_key:
        raise ImageGenError("Paste your image-AI key first.")
    body = {"model": model, "prompt": prompt, "size": size, "n": 1}
    if model.startswith("dall-e"):
        body["response_format"] = "b64_json"
    req = urllib.request.Request(base_url.rstrip("/") + "/images/generations", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                                          "User-Agent": "IdeawoodStudioArtists"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read().decode("utf-8", "replace")).get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            msg = ""
        raise ImageGenError(f"Image AI error {e.code}: {msg or e.reason}") from e
    except Exception as e:  # noqa: BLE001
        raise ImageGenError(f"Could not reach the image AI: {e}") from e
    item = (data.get("data") or [{}])[0]
    path = dest_no_ext + ".png"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if item.get("b64_json"):
        with open(path, "wb") as f:
            f.write(base64.b64decode(item["b64_json"]))
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=timeout) as r, open(path, "wb") as f:
            f.write(r.read())
    else:
        raise ImageGenError("The image AI returned no picture.")
    return path
