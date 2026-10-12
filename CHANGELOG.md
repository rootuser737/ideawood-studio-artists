# Changelog

## 1.2.0 - 2026-10-12
- Short clips: suggested cut points (chorus, build-up, last chorus, opening, ending) snapped to whole lyric lines; platform
  presets (Reels/TikTok/Shorts, WhatsApp status, Instagram 4:5, square); fades; preview, export one, export all.
- Startup splash with real progress, elapsed time, heartbeat dots (alive vs frozen), honest hints and a `startup.log`;
  the video engine is warmed up in the background so the first render is not slow.
- Fixed: a generated scene followed by a picture/clip/gradient scene made the render fail (wrong ffmpeg input number).

## 1.1.0 - 2026-10-09
- File size control: bitrate-capped profiles (Tiny / Small / Balanced / High), custom target size in MB, worst-case size
  shown before rendering, grain/flicker/shake skipped in small files, "Shrink an existing video" tool. Fixes gigabyte outputs.
- Verbose speech-model download: live MB, %, speed, time left, log, resume and cancel.
- Custom AI visuals: AI art director + built-in generative backgrounds (aurora, stars, snow, embers, rain, bokeh, dust),
  artist brief box, optional image-AI mode (OpenAI-compatible key); per-scene redo.
- 78 bundled OFL fonts in 7 groups with a group filter; 23 presets; 10 text entrance animations; double outline, 3D shadow.
- Effects: bloom, light leaks, chromatic split, flicker, shake, scanlines, letterbox, particle overlays, 8 grades, 28 transitions.

## 1.0.0 - 2026-10-08
First release: lyric video maker split out of Ideawood Studio (voxcut).
- Audio + pasted lyrics; Whisper auto-sync with fuzzy alignment, tap-to-sync, even spread, LRC import/export
- Timing table editor, SRT/LRC export
- 8 style presets, 15 bundled OFL fonts + user fonts, karaoke sweep/word highlight, glow, box, animations,
  next-line preview, countdown dots, title card
- AI visuals: per-scene search phrases from the lyrics, video/picture download, thumbnail picker, own files, gradient fallback
- Single-pass FFmpeg render: Ken Burns, transitions, grade, grain, vignette, visualiser, logo; 4 shapes, up to 4K
- Live preview frame, 22 s preview clip, `.iwlyric` projects
