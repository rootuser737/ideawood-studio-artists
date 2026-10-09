"""Built-in generative visuals: custom animated backgrounds designed from the lyrics, rendered by FFmpeg itself.

Not stock footage and not downloaded: every scene is *made* - an animated colour field (aurora) plus an optional
particle layer (stars, snow, embers, rain, bokeh, dust) tinted to the mood of that part of the song.
``look_for`` is the "art director": it reads the lyrics, the AI search phrase for the scene and the artist's own brief
(e.g. "neon rain over Kampala at night") and chooses a recipe + palette. Works fully offline. No Qt.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

PALETTES: Dict[str, List[str]] = {
    "warm_pink": ["#3B0A45", "#C2185B", "#FF8A65"], "night_blue": ["#050A24", "#0B1F4A", "#3F51B5"],
    "fire": ["#1A0500", "#7A1200", "#FF6D00"], "rain": ["#0B1520", "#1D3447", "#3D5A73"],
    "gold": ["#2A1500", "#8A5A00", "#FFC107"], "ocean": ["#021B2B", "#05667A", "#2EC4B6"],
    "heaven": ["#1B2845", "#6C7FB5", "#FFF1C1"], "neon": ["#12002B", "#6A00F4", "#00E5FF"],
    "forest": ["#04140A", "#0B4D2C", "#7BD96B"], "sunset": ["#2B0A3D", "#C2185B", "#FFB74D"],
    "snow": ["#0A1A2F", "#274C77", "#A3CEF1"], "mono": ["#0D0D0D", "#2B2B2B", "#555555"],
    "violet": ["#14052B", "#4A148C", "#CE93D8"], "emerald": ["#00121A", "#006D5B", "#9BFFE0"],
}

# recipe -> (gradient colours count, gradient speed, particle kind or None)
RECIPES: Dict[str, tuple] = {
    "aurora": (3, 0.030, None), "plain": (2, 0.012, None), "stars": (3, 0.010, "stars"),
    "snow": (3, 0.012, "snow"), "embers": (3, 0.016, "embers"), "rain": (3, 0.012, "rain"),
    "bokeh": (3, 0.016, "bokeh"), "dust": (3, 0.014, "dust"), "sunset": (3, 0.010, "bokeh"),
}

# particle kind -> (grid divisor, dot density, blur sigma factor (x height), scroll vertical, scroll horizontal, brightness)
PARTICLES: Dict[str, tuple] = {
    "stars": (3, 0.0050, 0.0008, 0.0, 0.0, 1.00), "snow": (4, 0.0070, 0.0030, 0.0030, 0.0004, 1.00),
    "embers": (4, 0.0055, 0.0035, -0.0040, 0.0006, 1.00), "rain": (3, 0.0080, 0.0006, 0.0300, 0.0, 0.85),
    "bokeh": (12, 0.0060, 0.0140, -0.0010, 0.0, 0.95), "dust": (4, 0.0080, 0.0016, -0.0008, 0.0003, 0.80),
}

# lyric/prompt word -> (recipe, palette)
LEX = {}
for words, rp in {
    "love heart hearts kiss lover darling romance baby": ("bokeh", "warm_pink"),
    "night moon star stars sky dream dreams midnight dark": ("stars", "night_blue"),
    "fire burn burning flame flames hot blaze smoke": ("embers", "fire"),
    "rain cry crying tears storm cloud clouds lonely alone pain": ("rain", "rain"),
    "sun sunshine gold golden shine smile shining bright money": ("bokeh", "gold"),
    "ocean sea wave waves water river lake beach island summer": ("aurora", "ocean"),
    "god pray prayer heaven angel angels lord jesus grace holy worship blessed": ("dust", "heaven"),
    "dance dancing party club fun festival disco groove jump": ("aurora", "neon"),
    "winter snow cold ice frozen christmas": ("snow", "snow"),
    "forest tree trees garden flower flowers nature mountain village green home": ("aurora", "forest"),
    "sunrise morning sunset evening dawn dusk horizon": ("sunset", "sunset"),
    "city street hustle ghetto neon lights town": ("bokeh", "neon"),
    "magic mystic spirit ancestors ancestor soul spirits": ("dust", "violet"),
}.items():
    for w in words.split():
        LEX[w] = rp
GENRE_LOOK = {"reggae": ("bokeh", "sunset"), "gospel": ("dust", "heaven"), "hip hop": ("bokeh", "neon"),
              "rap": ("bokeh", "neon"), "afrobeats": ("aurora", "neon"), "rock": ("embers", "fire"),
              "pop": ("bokeh", "violet"), "rnb": ("stars", "night_blue"), "r&b": ("stars", "night_blue"),
              "worship": ("dust", "heaven"), "acoustic": ("dust", "gold"), "dancehall": ("aurora", "neon"),
              "funk": ("aurora", "violet")}
CYCLE = [("aurora", "violet"), ("stars", "night_blue"), ("bokeh", "warm_pink"), ("aurora", "emerald"),
         ("dust", "gold"), ("aurora", "ocean")]


def look_for(lyric_text: str, hint: str = "", brief: str = "", genre: str = "", salt: int = 0) -> Tuple[str, List[str]]:
    """Art direction for one scene -> (recipe, 3 colours). The artist's brief counts triple, the AI phrase double."""
    score: Dict[tuple, float] = {}
    for text, weight in ((lyric_text, 1.0), (hint, 2.0), (brief, 3.0)):
        for w in re.findall(r"[a-z']+", (text or "").lower()):
            rp = LEX.get(w.strip("'"))
            if rp:
                score[rp] = score.get(rp, 0.0) + weight
    if score:
        recipe, pal = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    else:
        g = (genre or "").lower()
        hit = next((v for k, v in GENRE_LOOK.items() if k in g), None)
        recipe, pal = hit or CYCLE[salt % len(CYCLE)]
    # the brief can force a particle type even when the lyrics point elsewhere ("... with falling snow")
    for w in re.findall(r"[a-z]+", (brief or "").lower()):
        forced = {"snow": "snow", "rain": "rain", "stars": "stars", "embers": "embers", "sparks": "embers",
                  "bokeh": "bokeh", "dust": "dust", "aurora": "aurora"}.get(w)
        if forced:
            recipe = forced
    return recipe, list(PALETTES[pal])


def _hex(c: str) -> str:
    return "0x" + (c or "#000000").lstrip("#")[:6]


def _rgb(c: str) -> Tuple[float, float, float]:
    c = (c or "#FFFFFF").lstrip("#")[:6].ljust(6, "0")
    return int(c[0:2], 16) / 255.0, int(c[2:4], 16) / 255.0, int(c[4:6], 16) / 255.0


def particle_chain(kind: str, w: int, h: int, dur: float, color: str, amount: float, label: str, fps: int = 30) -> str:
    """A filter chain that *creates* a particle layer from nothing (no input files) and ends in ``[label]``."""
    div, dens, blur, vy, vx, bright = PARTICLES.get(kind, PARTICLES["dust"])
    gw, gh = max(16, w // div), max(16, h // div)
    r, g, b = (x * bright * max(0.0, min(amount, 1.0)) for x in _rgb(color))
    sigma = max(0.3, blur * h)
    blur_f = f"gblur=sigma=0.6:sigmaV={max(sigma * 14, 2.0):.1f}" if kind == "rain" else f"gblur=sigma={sigma:.2f}"
    scroll = f",scroll=vertical={vy}:horizontal={vx}" if (vy or vx) else ""
    return (f"color=c=black:s={gw}x{gh}:r={fps}:d=0.1,format=gray,"
            f"geq=lum='if(lt(random(0),{dens}),90+165*random(1),0)',"
            f"loop=loop=-1:size=1:start=0,setpts=N/({fps}*TB),"
            f"scale={w}:{h}:flags={'neighbor' if kind in ('stars',) else 'bicubic'},{blur_f}{scroll},"
            f"format=rgb24,colorchannelmixer=rr={r:.3f}:gg={g:.3f}:bb={b:.3f},"
            f"trim=duration={dur:.3f},setpts=PTS-STARTPTS,fps={fps},format=yuv420p[{label}]")


def scene_graph(recipe: str, colors: List[str], w: int, h: int, L: float, i: int, seed: int, end: str, fps: int = 30) -> str:
    """Complete filter graph for a generated scene; output label is ``[s<i>]`` (``end`` closes the chain)."""
    nb, speed, kind = RECIPES.get(recipe, RECIPES["aurora"])
    cols = (list(colors) + PALETTES["violet"])[: max(nb, 2)]
    cs = ":".join(f"c{k}={_hex(c)}" for k, c in enumerate(cols))
    grad = (f"gradients=s={w}x{h}:r={fps}:d={L:.3f}:{cs}:nb_colors={len(cols)}:speed={speed}:"
            f"seed={(seed * 7 + i * 13) % 1000 + 1}")
    if not kind:
        return f"{grad},{end}"
    accent = cols[-1]
    return (f"{grad},format=yuv420p[g{i}];{particle_chain(kind, w, h, L, accent, 1.0, f'pp{i}', fps)};"
            f"[g{i}][pp{i}]blend=all_mode=screen:shortest=1,{end}")
