"""``IdeawoodStudioArtists.exe --selftest result.txt`` - proves a build can start: tools, fonts, model, window, lyric render."""
from __future__ import annotations

import os
import sys
import tempfile
import traceback


def run(out_path: str) -> int:
    lines, ok = [], True

    def check(name, fn):
        nonlocal ok
        try:
            lines.append(f"OK    {name}: {fn()}")
        except Exception:  # noqa: BLE001
            ok = False
            lines.append(f"FAIL  {name}\n{traceback.format_exc()}")

    from . import asr, fonts, lyrics, paths, render
    from .project import Project, Scene
    check("ffmpeg", lambda: paths.find_tool("ffmpeg"))
    check("ffprobe", lambda: paths.find_tool("ffprobe"))
    check("whisper-cli", lambda: asr.find_whisper_cli())
    check("bundled fonts", lambda: (len(fonts.font_files(paths.bundled_fonts_dir())) >= 70 or 1 / 0) and len(fonts.font_files(paths.bundled_fonts_dir())))
    check("font names", lambda: fonts._family_of(fonts.font_files(paths.bundled_fonts_dir())[0]))

    def frame():
        p = Project(duration=10.0, title="Self test", artist="Ideawood")
        p.lines = lyrics.finalize_timing(lyrics.distribute_evenly(lyrics.parse_lyrics("Hello world\nSelf test line"), 10.0, lead=3.0), 10.0)
        p.scenes = [Scene(0, 10, "generated", recipe="stars")]
        out = os.path.join(tempfile.gettempdir(), "iw_selftest.png")
        render.preview_frame(p, 4.0, out)
        return f"{os.path.getsize(out)} bytes"
    check("lyric frame (libass + fonts)", frame)

    def window():
        from PySide6.QtWidgets import QApplication
        from .gui import Studio
        app = QApplication.instance() or QApplication([])
        w = Studio()
        return f"{w.windowTitle()}, {w.font_box.count()} fonts listed"
    check("window", window)
    lines.append("RESULT: " + ("PASS" if ok else "FAIL"))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok else 1
