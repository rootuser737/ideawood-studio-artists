"""Short clips for Reels / TikTok / Shorts / WhatsApp status, cut from the finished lyric video.

A clip never starts or ends in the middle of a lyric line: the window is snapped to whole lines. The chorus (the stanza
that comes back) is found from the lyrics themselves, so it works in any language. No Qt.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import List

from . import encoding
from .lyrics import LyricLine
from .project import Project
from .scenes import _key, plan_scenes
from .project import Scene

LENGTHS = [15, 20, 30, 45, 60]
LEAD, TAIL = 0.35, 0.7          # seconds before the first line / after the last line

PLATFORMS = {
    "Reels / TikTok / Shorts  (9:16, up to 60 s)": {"fmt": "Portrait 9:16 (Reels / TikTok / Shorts)", "max_len": 60, "profile": "small"},
    "WhatsApp status  (9:16, 30 s max, tiny file)": {"fmt": "Portrait 9:16 (Reels / TikTok / Shorts)", "max_len": 30, "profile": "tiny"},
    "Instagram feed  (4:5, up to 60 s)": {"fmt": "Portrait 4:5 (Instagram feed)", "max_len": 60, "profile": "small"},
    "Square  (1:1, up to 60 s)": {"fmt": "Square 1:1", "max_len": 60, "profile": "small"},
}


def profile_label(key: str) -> str:
    return next(label for label, k in encoding.PROFILES.items() if k == key)


@dataclass
class Clip:
    label: str
    start: float
    end: float
    n_lines: int = 0

    @property
    def length(self) -> float:
        return self.end - self.start


def _timed(lines: List[LyricLine]) -> List[LyricLine]:
    return sorted((l for l in lines if l.timed and l.text.strip()), key=lambda l: l.start)


def window_from(lines: List[LyricLine], i: int, length: float, duration: float) -> Clip:
    """A clip that starts at line ``i`` and holds as many whole lines as fit in ``length`` seconds."""
    ls = _timed(lines)
    start = max(0.0, ls[i].start - LEAD)
    j = i
    while j + 1 < len(ls) and ls[j + 1].end - start <= length - TAIL:
        j += 1
    end = min(ls[j].end + TAIL, duration if duration else ls[j].end + TAIL)
    if end - start < min(8.0, length):                      # a very short phrase: keep going so the clip is worth posting
        while j + 1 < len(ls) and end - start < min(8.0, length):
            j += 1
            end = min(ls[j].end + TAIL, duration or ls[j].end + TAIL)
    return Clip("", start, end, j - i + 1)


def suggest_clips(lines: List[LyricLine], duration: float, length: float = 30.0, max_n: int = 4) -> List[Clip]:
    """Good places to cut: the chorus, the lead-in to the chorus, the opening, the last chorus, the ending."""
    ls = _timed(lines)
    if not ls:
        return []
    stanzas: dict = {}
    for ln in ls:
        stanzas.setdefault(ln.stanza, []).append(ln)
    groups = [stanzas[k] for k in sorted(stanzas)]
    keys = [_key(g) for g in groups]
    index_of = {id(l): n for n, l in enumerate(ls)}
    counts: dict = {}
    for k, g in zip(keys, groups):
        counts[k] = counts.get(k, 0) + 1
    repeated = [(counts[k], sum(l.end - l.start for l in g), k) for k, g in zip(keys, groups) if counts[k] >= 2]
    out: List[Clip] = []
    if repeated:
        best = max(repeated)[2]
        occ = [g for k, g in zip(keys, groups) if k == best]
        c = window_from(ls, index_of[id(occ[0][0])], length, duration)
        c.label = "Chorus (first time)"
        out.append(c)
        pos = groups.index(occ[0])
        if pos > 0:                                          # the verse lines that lead into the chorus
            prev = groups[pos - 1]
            i0 = index_of[id(prev[max(0, len(prev) - 2)])]
            c2 = window_from(ls, i0, length, duration)
            c2.label = "Build-up into the chorus"
            out.append(c2)
        if len(occ) > 1:
            c3 = window_from(ls, index_of[id(occ[-1][0])], length, duration)
            c3.label = "Last chorus"
            out.append(c3)
    c4 = window_from(ls, 0, length, duration)
    c4.label = "Opening"
    out.append(c4)
    # ending: the last lines that fit
    i_end = len(ls) - 1
    while i_end > 0 and ls[-1].end - ls[i_end - 1].start + LEAD + TAIL <= length:
        i_end -= 1
    c5 = window_from(ls, i_end, length, duration)
    c5.label = "Ending"
    out.append(c5)
    uniq: List[Clip] = []
    for c in out:                                            # drop near-duplicates (more than 70 % overlap)
        if all(min(c.end, u.end) - max(c.start, u.start) < 0.7 * min(c.length, u.length) for u in uniq):
            uniq.append(c)
    return uniq[:max_n]


def make_clip_project(p: Project, start: float, end: float, fade: bool = True) -> Project:
    """A copy of the project covering only [start, end]: lyrics and scenes shifted to start at 0, audio cut to match."""
    if not p.scenes:
        p.scenes = plan_scenes(p.lines, p.duration)
    q = copy.deepcopy(p)
    q.audio_offset, q.duration, q.clip_fade = start, end - start, fade
    lines: List[LyricLine] = []
    for ln in p.lines:
        if ln.timed and ln.start >= start - 0.05 and ln.end <= end + 0.05:
            c = copy.deepcopy(ln)
            c.start, c.end = max(0.0, ln.start - start), ln.end - start
            for w in c.words:
                w.start, w.end = max(0.0, w.start - start), w.end - start
            lines.append(c)
    q.lines = lines
    scenes: List[Scene] = []
    for s in p.scenes:
        a, b = max(s.start, start), min(s.end, end)
        if b - a > 0.05:
            c = copy.deepcopy(s)
            c.start, c.end = a - start, b - start
            scenes.append(c)
    q.scenes = scenes or [Scene(0.0, end - start)]
    q.style = copy.deepcopy(p.style)
    q.style.title_card = False
    return q
