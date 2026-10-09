"""Output size control. A 3-minute lyric video should be a few MB to a few tens of MB - never gigabytes.

What makes lyric videos huge: film grain / flicker / shake (random noise cannot be compressed), 4K, and quality-only
(CRF) encoding with no bitrate ceiling. Every profile here caps the video bitrate, so the *worst case* size is known
before rendering:  size <= (video_kbps + audio_kbps) x duration.  Real files are usually far smaller because lyric
backgrounds are mostly calm. No Qt.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

PROFILES = {
    "Tiny - smallest file (3 min: up to ~6 MB, 480p)": "tiny",
    "Small - phones & WhatsApp (3 min: up to ~22 MB, 720p)": "small",
    "Balanced - YouTube & Instagram (3 min: up to ~80 MB, 1080p)": "balanced",
    "High quality (3 min: up to ~230 MB at 1080p)": "high",
    "Custom - I choose the file size": "custom",
}
DEFAULT_PROFILE = "Balanced - YouTube & Instagram (3 min: up to ~80 MB, 1080p)"
MB = 1024 * 1024


@dataclass
class EncodePlan:
    short: int            # short side in px (360 .. 2160)
    fps: int
    crf: int
    maxrate_k: int        # video bitrate ceiling, kbit/s
    audio_k: int
    preset: str
    strip_noise: bool     # drop grain / flicker / shake (they make files huge)
    cap_grain: bool       # keep only a whisper of grain
    est_max_mb: float     # worst-case size for this duration
    note: str = ""


def _est(maxrate_k: int, audio_k: int, duration: float) -> float:
    return (maxrate_k + audio_k) * 1000.0 / 8.0 * max(duration, 1.0) / MB


def plan(profile_key: str, quality_short: int, duration: float, target_mb: float = 10.0) -> EncodePlan:
    prof = PROFILES.get(profile_key, profile_key) if profile_key not in PROFILES.values() else profile_key
    q = max(240, int(quality_short))
    if prof == "tiny":
        short, fps, crf, mr, ak = min(q, 480), 24, 33, 220, 64
        return EncodePlan(short, fps, crf, mr, ak, "slow", True, False, _est(mr, ak, duration))
    if prof == "small":
        short = min(q, 720)
        return EncodePlan(short, 25, 28, 900, 96, "slow", True, False, _est(900, 96, duration))
    if prof == "high":
        mr = int(10000 * (q / 1080.0) ** 2)
        return EncodePlan(q, 30, 19, mr, 256, "medium", False, False, _est(mr, 256, duration))
    if prof == "custom":
        total = target_mb * MB * 8 / max(duration, 1.0) / 1000.0 * 0.96       # kbit/s incl. ~4 % container overhead
        ak = 128 if total >= 900 else 96 if total >= 500 else 64 if total >= 250 else 48
        vk = max(int(total - ak), 30)
        short = 360 if vk < 120 else 480 if vk < 350 else 720 if vk < 1400 else 1080 if vk < 4000 else 1440
        short = min(short, q)
        crf = 31 if vk < 400 else 27 if vk < 1500 else 23
        note = ""
        if vk < 120 or ak <= 48:
            note = "Very small target: expect soft video and plain backgrounds, and audio is reduced to save space."
        return EncodePlan(short, 24 if vk < 1000 else 30, crf, vk, ak, "slow", vk < 2500, False,
                          _est(vk, ak, duration), note)
    # balanced (default)
    mr = int(3500 * (min(q, 1080) / 1080.0) ** 2) if q <= 1080 else int(3500 * (q / 1080.0) ** 2)
    return EncodePlan(q if q <= 1080 else q, 30, 24, mr, 160, "medium", False, True, _est(mr, 160, duration))


def apply_to_style(style, pl: EncodePlan):
    """Return a copy of the style without the effects that bloat files for this plan."""
    st = style.copy()
    if pl.strip_noise:
        st.grain, st.flicker, st.shake = 0.0, 0.0, 0.0
    elif pl.cap_grain:
        st.grain = min(st.grain, 0.03)
        st.flicker = min(st.flicker, 0.2)
    return st


def x264_args(pl: EncodePlan, fps: Optional[int] = None) -> list:
    fps = fps or pl.fps
    return ["-c:v", "libx264", "-preset", pl.preset, "-crf", str(pl.crf), "-maxrate", f"{pl.maxrate_k}k",
            "-bufsize", f"{pl.maxrate_k * 2}k", "-g", str(fps * 10), "-keyint_min", str(fps), "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-r", str(fps)]


def audio_args(pl: EncodePlan) -> list:
    return ["-c:a", "aac", "-b:a", f"{pl.audio_k}k", "-ar", "44100" if pl.audio_k <= 96 else "48000"]


def shrink_command(ff: str, src: str, out: str, profile_key: str, quality_short: int, duration: float,
                   target_mb: float = 10.0) -> tuple:
    """Re-encode any existing video (e.g. a 1.3 GB file) to the chosen size. Returns (cmd, plan)."""
    pl = plan(profile_key, quality_short, duration, target_mb)
    vf = f"scale=-2:'min({pl.short},ih)':flags=bicubic,fps={pl.fps}"
    cmd = [ff, "-y", "-nostdin", "-progress", "pipe:1", "-nostats", "-i", src, "-map", "0:v:0", "-map", "0:a:0?",
           "-vf", vf, *x264_args(pl), *audio_args(pl), "-movflags", "+faststart", out]
    return cmd, pl
