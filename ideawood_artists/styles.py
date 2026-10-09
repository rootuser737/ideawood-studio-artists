"""Look presets for the lyric text and the background treatment. Plain data, JSON-serialisable, no Qt."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

GRADES = {
    "None": "",
    "Teal & orange": "colorbalance=rs=0.08:bs=-0.08:rh=0.10:bh=-0.10,eq=contrast=1.1:saturation=1.2",
    "Golden hour": "colorbalance=rs=0.12:gs=0.04:bs=-0.12:rm=0.06:bm=-0.06,eq=brightness=0.02:saturation=1.2",
    "Sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
    "Moody dark": "eq=contrast=1.2:brightness=-0.06:saturation=0.85,colorbalance=bs=0.05:bm=0.04",
    "Pastel dream": "eq=contrast=0.9:brightness=0.06:saturation=0.8,colorbalance=rs=0.05:bs=0.06",
    "High contrast": "eq=contrast=1.35:saturation=1.1",
    "Neon pop": "eq=saturation=1.7:contrast=1.15,colorbalance=bs=0.08:rs=0.05",
    "Cinematic": "colorbalance=rs=-0.06:bs=0.07:rh=0.07:bh=-0.07,eq=contrast=1.08:saturation=1.12",
    "Warm film": "colorbalance=rs=0.07:bs=-0.07:rm=0.05:bm=-0.05,eq=saturation=1.1",
    "Cool night": "colorbalance=rs=-0.06:bs=0.09:rm=-0.04:bm=0.06,eq=contrast=1.05",
    "Vibrant": "eq=saturation=1.4:contrast=1.08",
    "Faded vintage": "curves=preset=vintage",
    "Black & white": "hue=s=0,eq=contrast=1.12",
}
TRANSITIONS = ["mix", "fade", "dissolve", "fadeblack", "fadewhite", "smoothleft", "smoothright", "smoothup", "smoothdown",
               "slideleft", "slideright", "slideup", "slidedown", "wipeleft", "wiperight", "wipeup", "wipedown",
               "circleopen", "circleclose", "circlecrop", "rectcrop", "radial", "horzopen", "vertopen", "diagtl",
               "pixelize", "distance", "zoomin", "none"]
MIX_TRANSITIONS = ["fade", "smoothleft", "circleopen", "dissolve", "slideleft", "radial", "zoomin", "wipeleft", "fadeblack"]
ANIMATIONS = ["fade", "pop", "bounce", "slide", "drop", "zoom_out", "blur", "wipe", "spread", "flip", "none"]
HIGHLIGHTS = ["sweep", "word", "none"]
VIZ_MODES = ["none", "wave", "bars"]
OVERLAYS = ["none", "stars", "snow", "embers", "rain", "bokeh", "dust"]


@dataclass
class LyricStyle:
    name: str = "Karaoke Bold"
    # --- text
    font: str = "Poppins"
    bold: bool = True
    italic: bool = False
    uppercase: bool = False
    size: float = 0.075            # fraction of min(height, 0.9 * width)
    spacing: float = 0.0           # letter spacing in px at 1080p
    pos_y: float = 0.5             # centre of the lyric block, 0 = top .. 1 = bottom
    max_chars: int = 0             # 0 = automatic wrap for the video shape
    # --- colours (#RRGGBB)
    color_unsung: str = "#FFFFFF"
    color_sung: str = "#FFD84D"
    outline_color: str = "#000000"
    outline: float = 0.05          # fraction of font size
    shadow: float = 0.03
    glow: bool = False
    glow_color: str = "#00E5FF"
    box: bool = False
    box_color: str = "#000000"
    box_alpha: float = 0.5
    # --- motion
    anim_in: str = "fade"
    anim_ms: int = 280
    highlight: str = "sweep"
    show_next: bool = True
    next_alpha: float = 0.55
    instrumental_dots: bool = True
    # --- background treatment
    bg_dim: float = 0.30
    bg_blur: float = 0.0
    vignette: bool = True
    grain: float = 0.0
    grade: str = "Cinematic"
    ken_burns: bool = True
    transition: str = "fade"
    transition_sec: float = 1.0
    viz: str = "none"
    viz_color: str = "#FFFFFF"
    # --- cinematic effects (all optional)
    bloom: float = 0.0             # soft glow on bright areas, 0..1
    chromatic: float = 0.0         # RGB split in px at 1080p
    scanlines: bool = False
    letterbox: bool = False        # cinematic black bars
    flicker: float = 0.0           # old-projector brightness flicker, 0..1
    shake: float = 0.0             # handheld camera drift in px at 1080p
    light_leak: float = 0.0        # warm film light leaks, 0..1
    overlay: str = "none"          # floating particles on top of the background
    overlay_color: str = "#FFFFFF"
    overlay_amount: float = 0.6
    # --- extra text looks
    outline2: bool = False         # second, outer outline ring
    outline2_color: str = "#000000"
    extrude: bool = False          # hard 3D-style offset shadow
    shadow_color: str = "#000000"
    # --- title card
    title_card: bool = True
    title_sec: float = 4.0

    def copy(self) -> "LyricStyle":
        return dataclasses.replace(self)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "LyricStyle":
        names = {f.name for f in dataclasses.fields(LyricStyle)}
        return LyricStyle(**{k: v for k, v in (d or {}).items() if k in names})


def _p(**kw) -> LyricStyle:
    return LyricStyle(**kw)


PRESETS = {
    "Karaoke Bold": _p(name="Karaoke Bold"),
    "Neon Night": _p(name="Neon Night", font="Righteous", bold=False, size=0.08, color_unsung="#EAFBFF",
                     color_sung="#FF3DCB", outline=0.03, shadow=0.0, glow=True, glow_color="#18E6FF",
                     anim_in="blur", highlight="sweep", bg_dim=0.45, grade="Cool night", viz="bars",
                     viz_color="#18E6FF", grain=0.03),
    "Cinematic Gold": _p(name="Cinematic Gold", font="DM Serif Display", bold=False, size=0.07,
                         color_unsung="#F4EBDD", color_sung="#F2C14E", outline=0.035, shadow=0.05,
                         anim_in="fade", anim_ms=600, highlight="sweep", bg_dim=0.40, grade="Warm film",
                         transition="fadeblack", transition_sec=1.4, grain=0.04, pos_y=0.78),
    "Street Poster": _p(name="Street Poster", font="Anton", bold=False, uppercase=True, size=0.105,
                        color_unsung="#FFFFFF", color_sung="#FF2E2E", outline=0.04, shadow=0.0, anim_in="pop",
                        anim_ms=200, highlight="word", show_next=False, bg_dim=0.5, grade="Black & white",
                        transition="wipeleft", transition_sec=0.5, grain=0.06),
    "Soul & Script": _p(name="Soul & Script", font="Great Vibes", bold=False, size=0.13,
                        color_unsung="#FFF6EE", color_sung="#FFB3C7", outline=0.03, shadow=0.05, glow=True,
                        glow_color="#FF8FB1", anim_in="fade", anim_ms=700, highlight="sweep",
                        bg_dim=0.35, grade="Warm film", transition="dissolve", transition_sec=1.6),
    "Retro Tape": _p(name="Retro Tape", font="Bungee", bold=False, size=0.07, color_unsung="#FFF1D0",
                     color_sung="#FF8A3D", outline=0.05, shadow=0.06, anim_in="slide", highlight="word",
                     bg_dim=0.35, grade="Faded vintage", grain=0.08, transition="slideleft"),
    "Clean Minimal": _p(name="Clean Minimal", font="Poppins", bold=False, size=0.052, color_unsung="#FFFFFF",
                        color_sung="#FFFFFF", outline=0.0, shadow=0.0, box=True, box_alpha=0.45,
                        anim_in="fade", highlight="none", show_next=False, pos_y=0.86, bg_dim=0.15,
                        grade="None", vignette=False, title_card=False),
    "Reggae Sunrise": _p(name="Reggae Sunrise", font="Staatliches", bold=False, size=0.10, uppercase=True,
                         color_unsung="#FFF3C4", color_sung="#3DDC84", outline=0.045, shadow=0.04,
                         anim_in="pop", anim_ms=240, highlight="sweep", bg_dim=0.32, grade="Vibrant",
                         transition="smoothleft", transition_sec=1.2, grain=0.03),
}
DEFAULT_PRESET = "Karaoke Bold"

PRESETS.update({
    "Aurora Dream": _p(name="Aurora Dream", font="Sacramento", bold=False, size=0.14, color_unsung="#E8F6FF",
                       color_sung="#9BFFE0", outline=0.025, shadow=0.0, glow=True, glow_color="#5CF2C8",
                       anim_in="spread", anim_ms=900, highlight="sweep", bg_dim=0.25, grade="Pastel dream",
                       overlay="dust", overlay_color="#BFFFEF", overlay_amount=0.5, bloom=0.35,
                       transition="dissolve", transition_sec=1.8),
    "Midnight Rain": _p(name="Midnight Rain", font="Michroma", bold=False, size=0.052, color_unsung="#D6E4F0",
                        color_sung="#7FC8FF", outline=0.03, shadow=0.04, anim_in="fade", anim_ms=600,
                        bg_dim=0.45, grade="Cool night", overlay="rain", overlay_color="#9FC4E8", overlay_amount=0.55,
                        flicker=0.25, letterbox=True, vignette=True, grain=0.04),
    "Ember Soul": _p(name="Ember Soul", font="Abril Fatface", bold=False, size=0.075, color_unsung="#FFE9D2",
                     color_sung="#FF7A18", outline=0.04, shadow=0.05, glow=True, glow_color="#FF4500",
                     anim_in="zoom_out", anim_ms=500, bg_dim=0.45, grade="Golden hour", overlay="embers",
                     overlay_color="#FF8A3D", overlay_amount=0.75, bloom=0.4, light_leak=0.25),
    "Starlight Gospel": _p(name="Starlight Gospel", font="Allura", bold=False, size=0.13, color_unsung="#FFFDF5",
                           color_sung="#FFE08A", outline=0.02, shadow=0.0, glow=True, glow_color="#FFE9A8",
                           anim_in="fade", anim_ms=900, bg_dim=0.35, grade="Moody dark", overlay="stars",
                           overlay_color="#FFF2C2", overlay_amount=0.8, bloom=0.45, transition="fadeblack"),
    "VHS Glitch": _p(name="VHS Glitch", font="Press Start 2P", bold=False, size=0.04, color_unsung="#FFFFFF",
                     color_sung="#00F0FF", outline=0.0, shadow=0.06, extrude=True, shadow_color="#FF2BD6",
                     anim_in="flip", anim_ms=220, highlight="word", chromatic=3.0, scanlines=True, flicker=0.4,
                     shake=3.0, grain=0.1, grade="Neon pop", bg_dim=0.4, transition="pixelize", transition_sec=0.5),
    "Golden Hour": _p(name="Golden Hour", font="Poppins", bold=False, size=0.07, color_unsung="#FFF4E0",
                      color_sung="#FFC857", outline=0.0, shadow=0.05, anim_in="fade", anim_ms=500, bg_dim=0.2,
                      grade="Golden hour", light_leak=0.35, bloom=0.3, overlay="bokeh", overlay_color="#FFD28A",
                      overlay_amount=0.6, transition="dissolve", transition_sec=1.5, pos_y=0.8),
    "Gold Chain": _p(name="Gold Chain", font="Bebas Neue", bold=False, uppercase=True, size=0.11,
                     color_unsung="#F5F5F5", color_sung="#FFD54A", outline=0.03, outline2=True,
                     outline2_color="#3a2a00", extrude=True, shadow_color="#1a1200", shadow=0.05, anim_in="drop",
                     anim_ms=240, highlight="word", bg_dim=0.5, grade="High contrast", letterbox=True,
                     show_next=False, transition="wipeleft", transition_sec=0.6),
    "Island Breeze": _p(name="Island Breeze", font="Pacifico", bold=False, size=0.075, color_unsung="#FFFFFF",
                        color_sung="#FFEB3B", outline=0.04, shadow=0.04, anim_in="bounce", anim_ms=420,
                        bg_dim=0.2, grade="Vibrant", light_leak=0.2, transition="smoothleft", transition_sec=1.0),
    "Heavenly Light": _p(name="Heavenly Light", font="DM Serif Display", bold=False, size=0.075,
                         color_unsung="#FFFFFF", color_sung="#FFF1B8", outline=0.0, shadow=0.0, glow=True,
                         glow_color="#FFFFFF", anim_in="blur", anim_ms=900, bg_dim=0.3, grade="Pastel dream",
                         overlay="dust", overlay_color="#FFFFFF", overlay_amount=0.7, bloom=0.6,
                         transition="dissolve", transition_sec=2.0),
    "Festival Pop": _p(name="Festival Pop", font="Lilita One", bold=False, size=0.095, color_unsung="#FFFFFF",
                       color_sung="#FF3D81", outline=0.07, outline_color="#2A0A45", outline2=True,
                       outline2_color="#FFFFFF", anim_in="bounce", anim_ms=360, highlight="word",
                       bg_dim=0.2, grade="Neon pop", overlay="bokeh", overlay_color="#FF9BD0", overlay_amount=0.6,
                       transition="circleopen", transition_sec=0.7),
    "Typewriter Indie": _p(name="Typewriter Indie", font="Chelsea Market", bold=False, size=0.06,
                           color_unsung="#F2EBDD", color_sung="#FFFFFF", outline=0.02, shadow=0.03,
                           anim_in="wipe", anim_ms=500, highlight="sweep", bg_dim=0.35, grade="Sepia",
                           grain=0.1, flicker=0.2, vignette=True, show_next=False, pos_y=0.82),
    "Block Party": _p(name="Block Party", font="Bowlby One", bold=False, uppercase=True, size=0.085,
                      color_unsung="#FFFFFF", color_sung="#FFEA00", outline=0.05, extrude=True,
                      shadow_color="#E91E63", shadow=0.06, anim_in="pop", anim_ms=200, highlight="word",
                      bg_dim=0.3, grade="Vibrant", transition="slideleft", transition_sec=0.5),
    "Blackletter Drill": _p(name="Blackletter Drill", font="Pirata One", bold=False, size=0.11,
                            color_unsung="#EDEDED", color_sung="#C8102E", outline=0.04, shadow=0.0,
                            anim_in="zoom_out", anim_ms=260, highlight="word", bg_dim=0.55, grade="Black & white",
                            grain=0.12, chromatic=2.0, letterbox=True, flicker=0.3, show_next=False),
    "Wild West": _p(name="Wild West", font="Rye", bold=False, size=0.07, color_unsung="#F7E7C6",
                    color_sung="#E0A030", outline=0.045, shadow=0.05, anim_in="drop", anim_ms=320,
                    bg_dim=0.35, grade="Sepia", grain=0.1, vignette=True, overlay="dust",
                    overlay_color="#E8C888", overlay_amount=0.4),
    "Arcade": _p(name="Arcade", font="Audiowide", bold=False, size=0.07, color_unsung="#E6FFFB",
                 color_sung="#FFE600", outline=0.03, shadow=0.0, glow=True, glow_color="#FF00E5",
                 anim_in="flip", anim_ms=300, highlight="sweep", bg_dim=0.4, grade="Neon pop", viz="bars",
                 viz_color="#00F0FF", scanlines=True, bloom=0.4),
})
