import os
import subprocess
import time

import pytest

from conftest import needs_ffmpeg
from ideawood_artists import clips as C, lyrics as L
from ideawood_artists.mediautil import media_info
from ideawood_artists.project import Project, Scene
from ideawood_artists.render import render

CHORUS = "Omuramba waitu we are one\nDancing in the golden sun"
TEXT = f"[Verse]\nWalking through the city lights\nEvery shadow sings\n\n[Chorus]\n{CHORUS}\n\n[Verse 2]\nRivers run and mountains call\nNothing will be the same\n\n[Chorus]\n{CHORUS}"


def timed(dur=120.0):
    return L.finalize_timing(L.distribute_evenly(L.parse_lyrics(TEXT), dur, lead=6.0), dur)


def test_suggestions_find_the_chorus_and_never_cut_lines():
    ls = timed()
    sug = C.suggest_clips(ls, 120.0, 30)
    labels = [c.label for c in sug]
    assert "Chorus (first time)" in labels and "Last chorus" in labels and len(sug) >= 3
    starts = {round(l.start - C.LEAD, 2) for l in ls} | {0.0}
    ends = {round(min(l.end + C.TAIL, 120.0), 2) for l in ls}
    for c in sug:
        assert c.length <= 31 and c.length >= 6
        assert round(c.start, 2) in starts or c.start == 0.0
        assert any(abs(c.end - e) < 0.02 for e in ends) or abs(c.end - 120.0) < 0.02
    chorus = next(c for c in sug if c.label.startswith("Chorus"))
    first_chorus_line = next(l for l in ls if l.text.startswith("Omuramba"))
    assert abs(chorus.start - (first_chorus_line.start - C.LEAD)) < 0.05


def test_short_platform_limits_and_profiles():
    assert C.PLATFORMS["WhatsApp status  (9:16, 30 s max, tiny file)"]["max_len"] == 30
    assert "Tiny" in C.profile_label("tiny")
    assert C.suggest_clips([], 100.0) == []


def test_clip_project_shifts_everything_to_zero():
    p = Project(duration=120.0, lines=timed())
    p.scenes = [Scene(0, 60, key="a"), Scene(60, 120, key="b")]
    ls = [l for l in p.lines if l.timed]
    s, e = ls[2].start - 0.35, ls[3].end + 0.7
    q = C.make_clip_project(p, s, e)
    assert q.audio_offset == s and abs(q.duration - (e - s)) < 1e-6 and q.clip_fade
    assert [l.text for l in q.lines] == [ls[2].text, ls[3].text]
    assert abs(q.lines[0].start - 0.35) < 0.01 and all(w.start >= 0 for l in q.lines for w in l.words)
    assert q.scenes[0].start == 0 and abs(q.scenes[-1].end - q.duration) < 1e-6
    assert len(p.lines) == len(ls) and p.audio_offset == 0       # the original project is untouched


@needs_ffmpeg
def test_clip_renders_with_matching_length_audio_and_fades(tmp_path):
    song = str(tmp_path / "s.mp3")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=40", song], check=True)
    p = Project(audio=song, duration=40.0, title="T", quality="480p (fast draft)")
    p.lines = L.finalize_timing(L.distribute_evenly(L.parse_lyrics(TEXT), 40.0, lead=3.0), 40.0)
    p.scenes = [Scene(0, 20, "generated", recipe="stars", colors=["#050A24", "#0B1F4A", "#3F51B5"], key="a"),
                Scene(20, 40, "gradient", key="b")]
    ls = p.lines
    q = C.make_clip_project(p, ls[2].start - 0.35, ls[3].end + 0.7)
    q.fmt = "Portrait 9:16 (Reels / TikTok / Shorts)"
    q.size_profile = C.profile_label("tiny")
    out = str(tmp_path / "clip.mp4")
    r = render(q, out)
    info = media_info(out)
    assert info["has_video"] and info["has_audio"] and abs(info["duration"] - q.duration) < 0.4
    assert info["h"] > info["w"] and os.path.getsize(out) < 1_500_000


def test_splash_steps_are_logged_and_never_go_backwards(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("IDEAWOOD_ARTISTS_DATA", str(tmp_path))
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from ideawood_artists import splash as S
    app = QApplication.instance() or QApplication([])
    sp = S.Splash("Test", "9.9")
    sp.show()
    sp.step("one", 10)
    sp.step("two", 5)                                   # a lower number must not move the bar back
    assert sp.pct == 10
    sp.step("three", 60)
    sp.finish()
    text = open(S.log_path(), encoding="utf-8").read()
    assert "one" in text and "three" in text and "ready" in text


@needs_ffmpeg
def test_engine_warmup_reports_each_tool():
    from ideawood_artists.startup import warm_engine
    seen = []
    res = warm_engine(lambda t, p: seen.append((t, p)), lambda: None, 70, 96)
    assert [r[0] for r in res][:2] == ["video engine (ffmpeg)", "media reader (ffprobe)"]
    assert all(r[2] == "ok" for r in res) and seen


@needs_ffmpeg
def test_studio_startup_progress_and_clip_ui(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from ideawood_artists.gui import Studio
    from ideawood_artists.theme import apply_theme
    song = str(tmp_path / "s.mp3")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=duration=40", song], check=True)
    app = QApplication.instance() or QApplication([])
    apply_theme(app, "Midnight")
    seen = []
    w = Studio(progress=lambda t, p: seen.append(p))
    assert seen == sorted(seen) and seen[0] >= 20 and seen[-1] >= 90          # startup reports steady progress
    assert w.set_audio(song)
    w.lyr_edit.setPlainText(TEXT)
    w.do_spread()
    w.clip_platform.setCurrentIndex(1)
    w.suggest_clips_ui()
    assert w.clip_list.count() >= 2 and w.clip_end.value() > w.clip_start.value()
    assert "MB" in w.clip_info.text()
    out = str(tmp_path / "c.mp4")
    import ideawood_artists.gui as G
    monkeypatch.setattr(G.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (out, "")))
    monkeypatch.setattr(G.QDesktopServices, "openUrl", staticmethod(lambda *_: True))
    w.export_clips("one")
    t = time.time()
    while w.worker.isRunning() and time.time() - t < 120:
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()
    assert os.path.exists(out) and media_info(out)["duration"] <= 31
