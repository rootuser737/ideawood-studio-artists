"""Builds and runs the one-pass ffmpeg render:  scenes (image Ken-Burns / video loop / gradient) -> crossfades ->
dim / blur / colour grade / vignette / grain -> optional audio visualiser + logo -> lyrics (ASS via libass) -> MP4.

Also renders a single still frame for the live look preview. No Qt.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from typing import Callable, List, Optional, Tuple

from .ass_lyrics import build_ass
from .fonts import prepare_fontsdir
from . import encoding
from .mediautil import Job
from .paths import find_tool
from .project import QUALITIES, Project, Scene, frame_size
from . import generative
from .styles import GRADES, MIX_TRANSITIONS, LyricStyle

FPS = 30
KB_SCALE = 1.5          # Ken Burns works on an image this much larger than the frame (keeps motion smooth)


class Cancelled(Exception):
    pass


def encode_plan(p: Project, preview: bool = False) -> encoding.EncodePlan:
    """The size/quality plan for this project (the preview clip is always a small fast draft)."""
    if preview:
        return encoding.EncodePlan(480, 30, 27, 1500, 128, "ultrafast", True, False, 0.0)
    return encoding.plan(p.size_profile, QUALITIES.get(p.quality, 1080), p.duration, p.target_mb)


def _even(x: float) -> int:
    return int(x) // 2 * 2


def _hex(c: str) -> str:
    return "0x" + (c or "#000000").lstrip("#")[:6]


def _segment(idx: int, i: int, sc: Scene, L: float, w: int, h: int, st: LyricStyle, seed: int = 0):
    """-> (ffmpeg input args, filter text producing [s<i>] from input number ``idx``)."""
    end = f"setsar=1,format=yuv420p,fps={FPS},settb=1/{FPS},setpts=PTS-STARTPTS[s{i}]"
    if sc.kind == "generated":
        return ([], generative.scene_graph(sc.recipe or "aurora", sc.colors, w, h, L, i, seed, end, FPS))
    usable = sc.kind in ("image", "video") and sc.path and os.path.isfile(sc.path)
    if usable and sc.kind == "video":
        return (["-stream_loop", "-1", "-t", f"{L:.3f}", "-i", sc.path],
                f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},{end}")
    if usable and sc.kind == "image":
        if st.ken_burns:
            n = max(2, int(L * FPS) + 2)
            bw, bh = _even(w * KB_SCALE), _even(h * KB_SCALE)
            v = i % 4
            cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
            z, x, y = [(f"1+0.10*on/{n}", cx, cy), (f"1.10-0.10*on/{n}", cx, cy),
                       ("1.08", f"(iw-iw/zoom)*on/{n}", cy), ("1.08", f"(iw-iw/zoom)*(1-on/{n})", cy)][v]
            return (["-i", sc.path],
                    f"[{idx}:v]scale={bw}:{bh}:force_original_aspect_ratio=increase,crop={bw}:{bh},"
                    f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={w}x{h}:fps={FPS},trim=duration={L:.3f},{end}")
        return (["-loop", "1", "-framerate", str(FPS), "-t", f"{L:.3f}", "-i", sc.path],
                f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},{end}")
    c0, c1 = (sc.colors + ["#141E30", "#243B55"])[:2]
    return (["-f", "lavfi", "-i", f"gradients=s={w}x{h}:r={FPS}:d={L:.3f}:c0={_hex(c0)}:c1={_hex(c1)}:"
                                  f"nb_colors=2:speed=0.012:seed={(seed * 7 + i * 13) % 1000 + 1}"],
            f"[{idx}:v]{end}")


def post_graph(st: LyricStyle, w: int, h: int, dur: float, src: str, dst: str, tag: str = "") -> List[str]:
    """Background treatment as filter-graph chunks from ``src`` to ``dst``: shake, blur, grade, dim, light leaks,
    particles, bloom, chromatic split, flicker, scanlines, letterbox, vignette, grain."""
    chunks: List[str] = []
    cur, n = src, [0]
    k = h / 1080.0

    def nxt() -> str:
        n[0] += 1
        return f"[{tag}x{n[0]}]"

    def lin(f: str):
        nonlocal cur
        out = nxt()
        chunks.append(f"{cur}{f}{out}")
        cur = out

    if st.shake > 0:
        m = max(2, int(st.shake * k * 2))
        lin(f"crop=iw-{m * 2}:ih-{m * 2}:x='{m}+{m * 0.9:.1f}*sin(t*2.7)':y='{m}+{m * 0.8:.1f}*cos(t*2.1)',scale={w}:{h}")
    if st.bg_blur > 0:
        lin(f"gblur=sigma={st.bg_blur * k:.1f}")
    g = GRADES.get(st.grade, "")
    if g:
        lin(g)
    if st.bg_dim > 0:
        lin(f"drawbox=x=0:y=0:w=iw:h=ih:color=black@{min(st.bg_dim, 0.9):.2f}:t=fill")
    if st.light_leak > 0:
        chunks.append(f"gradients=s={w}x{h}:r={FPS}:d={dur + 2:.2f}:c0=0xFF7A18:c1=0xAF002D:c2=0x319197:c3=0xFFC857:"
                      f"nb_colors=4:speed=0.05:seed=7,format=yuv420p[{tag}leak]")
        out = nxt()
        chunks.append(f"{cur}[{tag}leak]blend=all_mode=screen:all_opacity={min(st.light_leak, 1) * 0.6:.2f}:shortest=1{out}")
        cur = out
    if st.overlay != "none":
        chunks.append(generative_overlay(st, w, h, dur, f"{tag}pl"))
        out = nxt()
        chunks.append(f"{cur}[{tag}pl]blend=all_mode=screen:shortest=1{out}")
        cur = out
    if st.bloom > 0:
        a, b = f"[{tag}ba]", f"[{tag}bb]"
        chunks.append(f"{cur}split{a}{b}")
        chunks.append(f"{b}gblur=sigma={max(6, 14 * k):.1f},eq=brightness=0.04:contrast=1.3[{tag}bc]")
        out = nxt()
        chunks.append(f"{a}[{tag}bc]blend=all_mode=screen:all_opacity={min(st.bloom, 1):.2f}{out}")
        cur = out
    if st.chromatic > 0:
        px = max(1, int(round(st.chromatic * k)))
        lin(f"rgbashift=rh=-{px}:bh={px}")
    if st.flicker > 0:
        lin(f"eq=brightness='{0.05 * st.flicker:.3f}*sin(t*37)*sin(t*11.3)':eval=frame")
    if st.scanlines:
        lin(f"drawgrid=y=0:h={max(3, int(4 * k))}:t=1:c=black@0.22")
    if st.letterbox:
        lin(f"drawbox=x=0:y=0:w=iw:h=ih*0.11:color=black:t=fill,drawbox=x=0:y=ih*0.89:w=iw:h=ih*0.11:color=black:t=fill")
    if st.vignette:
        lin("vignette=angle=PI/5")
    if st.grain > 0:
        lin(f"noise=alls={int(st.grain * 150)}:allf=t")
    if not chunks:
        return [f"{src}null{dst}"]
    chunks[-1] = chunks[-1][: chunks[-1].rindex("[")] + dst
    return chunks


def generative_overlay(st: LyricStyle, w: int, h: int, dur: float, label: str) -> str:
    return generative.particle_chain(st.overlay, w, h, dur, st.overlay_color, st.overlay_amount, label, FPS)


def _logo_pos(name: str) -> str:
    m = "W*0.03"
    return {"Top left": f"{m}:{m}", "Top right": f"W-w-{m}:{m}", "Bottom left": f"{m}:H-h-{m}",
            "Bottom right": f"W-w-{m}:H-h-{m}"}.get(name, f"W-w-{m}:{m}")


def effective_transition(st: LyricStyle, scenes: List[Scene]) -> float:
    if st.transition == "none" or len(scenes) < 2:
        return 0.0
    return max(0.2, min(st.transition_sec, min(s.duration for s in scenes) * 0.45))


def build_command(p: Project, out_path: str, work: str, ff: str, *, preview: bool = False,
                  t0: float = 0.0, span: Optional[float] = None) -> Tuple[list, float]:
    pl = encode_plan(p, preview)
    short = pl.short
    w, h = frame_size(p.fmt, short)
    st = encoding.apply_to_style(p.style, pl)
    scenes = [s for s in p.scenes if s.duration > 0.05] or [Scene(0, p.duration)]
    scenes[0].start = 0.0
    scenes[-1].end = max(scenes[-1].end, p.duration)
    T = effective_transition(st, scenes)
    n = len(scenes)

    inputs: List[str] = []
    filt: List[str] = []
    for i, sc in enumerate(scenes):
        L = sc.duration + (T if i < n - 1 else 0.0)
        args, f = _segment(i, i, sc, L, w, h, st, seed=int(p.duration) + 1)
        inputs += args
        filt.append(f)
    if n == 1:
        filt.append("[s0]null[vj]")
    elif T <= 0:
        filt.append("".join(f"[s{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vj]")
    else:
        cur, off = "[s0]", 0.0
        for k in range(1, n):
            off += scenes[k - 1].duration
            out = "[vj]" if k == n - 1 else f"[x{k}]"
            tr = MIX_TRANSITIONS[(k - 1) % len(MIX_TRANSITIONS)] if st.transition == "mix" else st.transition
            filt.append(f"{cur}[s{k}]xfade=transition={tr}:duration={T:.3f}:offset={off:.3f}{out}")
            cur = out
    filt += post_graph(st, w, h, p.duration, "[vj]", "[vp]")
    cur = "[vp]"

    a_idx = inputs.count("-i")                                  # audio is the next input number
    inputs += ["-i", p.audio]
    audio_label = f"{a_idx}:a"
    use_logo = bool(p.logo and os.path.isfile(p.logo))
    if st.viz != "none":
        vh = _even(h * 0.16)
        filt.append(f"[{audio_label}]asplit=2[aout][aviz]")
        col = st.viz_color
        if st.viz == "bars":
            filt.append(f"[aviz]showfreqs=s={w}x{vh}:mode=bar:ascale=sqrt:fscale=log:win_size=2048:"
                        f"colors={_hex(col)}:rate={FPS},format=rgba,colorkey=black:0.15:0.2[viz]")
        else:
            filt.append(f"[aviz]showwaves=s={w}x{vh}:mode=cline:rate={FPS}:colors={_hex(col)}:scale=sqrt,"
                        f"format=rgba,colorkey=black:0.15:0.2[viz]")
        y = "H*0.04" if st.pos_y > 0.68 else "H-h-H*0.04"
        filt.append(f"{cur}[viz]overlay=0:{y}:format=auto:shortest=0[vv]")
        cur, a_src = "[vv]", "[aout]"
    else:
        a_src = f"[{audio_label}]"
    if use_logo:
        li = inputs.count("-i")
        inputs += ["-i", p.logo]
        filt.append(f"[{li}:v]scale={_even(w * p.logo_size)}:-2,format=rgba,colorchannelmixer=aa=0.9[lg]")
        filt.append(f"{cur}[lg]overlay={_logo_pos(p.logo_pos)}:format=auto[vl]")
        cur = "[vl]"
    filt.append(f"{cur}ass=filename=lyrics.ass:fontsdir=fonts,format=yuv420p[v]")
    if p.normalize_audio:
        filt.append(f"{a_src}loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    else:
        filt.append(f"{a_src}aresample=48000[a]")

    total = p.duration
    out_dur = total if span is None else max(0.5, min(span, total - t0))
    cmd = [ff, "-y", "-nostdin", "-progress", "pipe:1", "-nostats", *inputs, "-filter_complex", ";".join(filt),
           "-map", "[v]", "-map", "[a]"]
    if preview:
        cmd += ["-ss", f"{t0:.2f}"]
    cmd += ["-t", f"{out_dur:.2f}", *encoding.x264_args(pl), *encoding.audio_args(pl), "-movflags", "+faststart",
            os.path.abspath(out_path)]
    return cmd, out_dur


def write_ass(p: Project, work: str, preview: bool = False) -> Tuple[str, int, int]:
    w, h = frame_size(p.fmt, encode_plan(p, preview).short)
    credit = "Lyric video made with Ideawood Studio for Artists" if p.credit else ""
    text = build_ass(p.lines, encoding.apply_to_style(p.style, encode_plan(p, preview)), w, h, p.duration, p.title,
                     p.artist, credit)
    with open(os.path.join(work, "lyrics.ass"), "w", encoding="utf-8") as f:
        f.write(text)
    prepare_fontsdir(work)
    return text, w, h


def render(p: Project, out_path: str, on_progress: Callable[[float], None] = lambda v: None,
           on_status: Callable[[str], None] = lambda s: None, should_cancel: Callable[[], bool] = lambda: False,
           preview: bool = False, keep_workdir: bool = False) -> dict:
    if not p.audio or not os.path.isfile(p.audio):
        raise RuntimeError("Please choose the song's audio file first.")
    if not [l for l in p.lines if l.timed]:
        raise RuntimeError("There are no timed lyrics yet. Sync the lyrics first.")
    ff = find_tool("ffmpeg")
    work = tempfile.mkdtemp(prefix="ideawood_lyric_")
    holder = {"job": None}
    try:
        on_status("Preparing the lyrics and fonts...")
        write_ass(p, work, preview)
        first = min(l.start for l in p.lines if l.timed)
        t0 = max(0.0, first - 4.0) if preview else 0.0
        cmd, dur = build_command(p, out_path, work, ff, preview=preview, t0=t0, span=22.0 if preview else None)
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
        job = Job(cmd, dur, cwd=work)
        holder["job"] = job
        on_status("Rendering the preview clip..." if preview else "Rendering your lyric video...")

        def prog(v):
            if should_cancel():
                job.cancel()
            on_progress(v)
        try:
            job.run(prog)
        except RuntimeError:
            if should_cancel():
                raise Cancelled()
            raise
        on_status("Done")
        return {"path": out_path, "duration": dur}
    finally:
        if not keep_workdir:
            shutil.rmtree(work, ignore_errors=True)


def preview_frame(p: Project, t: float, out_png: str, short: int = 540) -> str:
    """Render ONE frame at time ``t`` (background of that scene + lyrics) for the live look preview."""
    import subprocess
    from .paths import no_window_flags
    ff = find_tool("ffmpeg")
    work = tempfile.mkdtemp(prefix="ideawood_frame_")
    try:
        w, h = frame_size(p.fmt, short)
        text = build_ass(p.lines, p.style, w, h, p.duration, p.title, p.artist,
                         "Lyric video made with Ideawood Studio for Artists" if p.credit else "")
        with open(os.path.join(work, "lyrics.ass"), "w", encoding="utf-8") as f:
            f.write(text)
        prepare_fontsdir(work)
        sc = next((s for s in p.scenes if s.start <= t < s.end), p.scenes[0] if p.scenes else Scene(0, max(p.duration, 1)))
        idx = p.scenes.index(sc) if sc in p.scenes else 0
        sc1 = Scene(0, 2.0, sc.kind, sc.path, colors=sc.colors, recipe=sc.recipe)
        st = p.style.copy()
        st.ken_burns = False
        args, f = _segment(0, idx, sc1, 2.0, w, h, st, seed=int(p.duration) + 1)
        post = ";".join(post_graph(st, w, h, 3.0, f"[s{idx}]", "[vp]", "f"))
        fc = (f"{f};{post};[vp]setpts=PTS+{t:.3f}/TB,ass=filename=lyrics.ass:fontsdir=fonts,format=rgb24[v]")
        cmd = [ff, "-y", "-nostdin", "-v", "error", *args, "-filter_complex", fc, "-map", "[v]", "-frames:v", "1",
               os.path.abspath(out_png)]
        r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, errors="replace",
                           creationflags=no_window_flags())
        if r.returncode != 0 or not os.path.exists(out_png):
            raise RuntimeError("Could not draw the preview frame.\n" + (r.stderr or "")[-300:])
        return out_png
    finally:
        shutil.rmtree(work, ignore_errors=True)
