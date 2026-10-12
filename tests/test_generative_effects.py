import http.server
import os
import subprocess
import threading
import time

import pytest

from conftest import needs_ffmpeg
from ideawood_artists import asr, fonts, generative as G, lyrics as L
from ideawood_artists.mediautil import media_info
from ideawood_artists.project import Project, Scene
from ideawood_artists.render import preview_frame, render
from ideawood_artists.styles import ANIMATIONS, OVERLAYS, PRESETS, TRANSITIONS


def test_art_director_reads_lyrics_hint_and_brief():
    assert G.look_for("the rain keeps falling and I cry")[0] == "rain"
    assert G.look_for("sun gold shine")[1][2] == G.PALETTES["gold"][2]
    assert G.look_for("rain on me", brief="warm night with falling snow")[0] == "snow"       # brief wins
    assert G.look_for("la la la", genre="Gospel")[0] == "dust"                               # genre fallback
    r, cols = G.look_for("hmm", salt=3)
    assert r in G.RECIPES and len(cols) == 3


def test_catalog_is_big_and_valid():
    assert len(fonts.CURATED) >= 75 and len(fonts.FONT_GROUPS) >= 6
    have = {os.path.basename(f) for f in fonts.font_files(fonts.bundled_fonts_dir())}
    assert len(have) >= 78
    assert len(PRESETS) >= 22 and len(ANIMATIONS) >= 10 and len(TRANSITIONS) >= 25 and len(OVERLAYS) >= 6


@needs_ffmpeg
def test_every_preset_renders_a_frame_on_generated_background(tmp_path):
    p = Project(duration=30.0, title="T", artist="A")
    p.lines = L.finalize_timing(L.distribute_evenly(L.parse_lyrics("Walking through the city lights\nEvery shadow sings"), 30.0, lead=4.0), 30.0)
    recipes = list(G.RECIPES)
    for i, (name, st) in enumerate(PRESETS.items()):
        p.style = st.copy()
        p.scenes = [Scene(0, 30, "generated", recipe=recipes[i % len(recipes)], colors=list(G.PALETTES["violet"]))]
        out = str(tmp_path / f"{i}.png")
        preview_frame(p, 5.5, out)
        assert os.path.getsize(out) > 2000, name


@needs_ffmpeg
def test_full_render_with_generated_scenes_and_stacked_effects(tmp_path):
    song = str(tmp_path / "s.mp3")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=duration=12", song], check=True)
    p = Project(audio=song, duration=12.0, quality="480p (fast draft)")
    p.lines = L.finalize_timing(L.distribute_evenly(L.parse_lyrics("first line here\nsecond line here\n\nthird one"), 12.0, lead=2.0), 12.0)
    p.scenes = [Scene(0, 6, "generated", recipe="snow", colors=list(G.PALETTES["snow"])),
                Scene(6, 12, "generated", recipe="embers", colors=list(G.PALETTES["fire"]))]
    p.style = PRESETS["VHS Glitch"].copy()
    p.style.transition, p.style.light_leak, p.style.bloom, p.style.overlay = "mix", 0.4, 0.4, "snow"
    out = str(tmp_path / "o.mp4")
    render(p, out)
    info = media_info(out)
    assert info["has_video"] and abs(info["duration"] - 12.0) < 0.3


def test_model_download_is_verbose_resumable_and_cancellable(tmp_path, monkeypatch):
    data = os.urandom(2_000_000)

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            rng = self.headers.get("Range")
            start = int(rng.split("=")[1].split("-")[0]) if rng else 0
            self.send_response(206 if rng else 200)
            self.send_header("Content-Length", str(len(data) - start))
            self.end_headers()
            try:
                for i in range(start, len(data), 100_000):
                    self.wfile.write(data[i:i + 100_000])
                    time.sleep(0.02)
            except OSError:
                pass

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(asr, "MODEL_URL", f"http://127.0.0.1:{srv.server_port}/{{file}}")
    monkeypatch.setattr(asr, "models_dir", lambda: str(tmp_path))
    key = next(iter(asr.MODELS))
    lab, fn, mb, x = asr.MODELS[key]
    monkeypatch.setitem(asr.MODELS, key, (lab, fn, 2, x))
    logs, details, calls = [], [], {"n": 0}

    def cancel():
        calls["n"] += 1
        return calls["n"] > 6
    with pytest.raises(asr.Cancelled):
        asr.download_model(key, lambda p: None, cancel, logs.append, lambda *a: details.append(a))
    assert os.path.getsize(asr.model_file(key) + ".part") > 0
    path = asr.download_model(key, lambda p: None, lambda: False, logs.append, lambda *a: details.append(a))
    assert os.path.getsize(path) == len(data)
    text = "\n".join(logs)
    assert "Source:" in text and "Resumed at" in text and "Ready:" in text
    assert details and details[-1][0] == details[-1][1] == len(data)


def test_size_profiles_are_bounded_and_noise_is_stripped():
    from ideawood_artists import encoding as E
    for prof, cap in (("tiny", 7), ("small", 25), ("balanced", 90), ("high", 240)):
        assert E.plan(prof, 1080, 180).est_max_mb < cap, prof
    assert E.plan("balanced", 2160, 180).est_max_mb < 330           # even 4K can't reach gigabytes
    c = E.plan("custom", 1080, 180, 3.0)
    assert c.est_max_mb <= 3.0 and c.short <= 480 and c.strip_noise
    st = PRESETS["Street Poster"].copy()
    assert st.grain > 0 and E.apply_to_style(st, E.plan("tiny", 1080, 180)).grain == 0


@needs_ffmpeg
def test_shrink_existing_video(tmp_path):
    from ideawood_artists import encoding as E
    src = str(tmp_path / "big.mp4")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=6",
                    "-f", "lavfi", "-i", "sine=duration=6", "-c:v", "libx264", "-crf", "10", "-c:a", "aac", "-b:a", "256k", src], check=True)
    out = str(tmp_path / "small.mp4")
    cmd, pl = E.shrink_command("ffmpeg", src, out, "tiny", 1080, 6.0)
    subprocess.run([c for c in cmd if c not in ("-progress", "pipe:1", "-nostats")], check=True, capture_output=True)
    assert os.path.getsize(out) < os.path.getsize(src) * 0.25 and media_info(out)["h"] <= 480


@needs_ffmpeg
def test_generated_scene_followed_by_picture_scene_renders(tmp_path):
    """Regression: input numbering when a scene without an input file (generated) precedes one with a file."""
    from PIL import Image
    song = str(tmp_path / "s.mp3")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=duration=10", song], check=True)
    img = str(tmp_path / "a.jpg")
    Image.new("RGB", (640, 360), (120, 40, 90)).save(img)
    p = Project(audio=song, duration=10.0, quality="480p (fast draft)")
    p.lines = L.finalize_timing(L.distribute_evenly(L.parse_lyrics("one two three\nfour five six"), 10.0, lead=1.0), 10.0)
    p.scenes = [Scene(0, 3, "generated", recipe="snow", colors=list(G.PALETTES["snow"]), key="a"),
                Scene(3, 6, "image", img, key="b"), Scene(6, 8, "generated", recipe="stars", colors=list(G.PALETTES["night_blue"]), key="c"),
                Scene(8, 10, "gradient", key="d")]
    out = str(tmp_path / "m.mp4")
    render(p, out)
    assert abs(media_info(out)["duration"] - 10.0) < 0.3
