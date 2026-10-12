# Ideawood Studio for Artists

Turn a finished song into a professional **lyric video** on your own PC: add the audio, paste the lyrics, get them timed,
pick a look, let **AI find the background pictures and video clips**, and export for YouTube, Reels, TikTok or Instagram.

Built from the engines of [voxcut / Ideawood Studio](https://github.com/Goddy36-A/voxcut) (offline Whisper, FFmpeg, the AI
cloud client, the theme), re-focused on one job.

## The five steps

| Step | What happens |
|---|---|
| **1 Song & lyrics** | Choose the audio, paste lyrics (`[Chorus]`-style headers and blank-line verses understood), then **Auto-sync** (offline Whisper + alignment), **Tap to sync** (press Space as each line starts - best for Luganda, Runyankole and other languages Whisper doesn't know) or **Spread evenly**. |
| **2 Timing** | Table editor: change any time or text, move everything, split / merge / add / delete lines, play from a line, export `.lrc` (with word timing) and `.srt`. |
| **3 Look & fonts** | 23 presets (Karaoke Bold, Neon Night, Aurora Dream, Midnight Rain, Ember Soul, VHS Glitch, Gold Chain, Festival Pop ...), **78 bundled professional fonts in 7 groups** + add your own `.ttf/.otf`, karaoke fill (sweep or word), glow, box, double outline, 3D shadow, 10 entrance animations (bounce, drop, flip, wipe, spread ...), next-line preview, countdown dots in long gaps, title card, colour grade, grain, vignette, transitions, optional audio visualiser, plus cinematic effects: bloom, light leaks, chromatic split, film flicker, handheld shake, scanlines, letterbox, floating particles (stars, snow, embers, rain, bokeh, dust), 8 colour grades and 28 transitions. |
| **4 Visuals (AI)** | **Custom visuals made for your song**: describe the world of the video and an AI art director designs a different animated look per scene (aurora colour fields, stars, snow, embers, rain, bokeh, dust) - offline, no key; or paint real pictures with your own image-AI key. Plus stock search: AI reads the lyrics, plans a search phrase per part of the song and downloads matching **video clips or pictures** (needs your API key). Repeated choruses reuse the same background. Pick alternatives with thumbnails, or use your own files. No key? Designed animated gradients - it always renders. Add your logo. |
| **5 Export** | 16:9, 9:16, 1:1 or 4:5; **file-size control** (Tiny / Small / Balanced / High / your own target in MB - the worst-case size is shown before rendering); a built-in **shrinker** for any big video; 22 s preview clip; `.credits.txt` for stock media. Projects save as `.iwlyric`. |

A **live preview** frame (right side) follows every change.

## Short clips (Reels, TikTok, Shorts, WhatsApp status)

Export > *Short clips*: press **Suggest clips** and the app proposes the chorus, the build-up into it, the last chorus, the
opening and the ending, cut to whole lyric lines (found from your lyrics, so it works in any language). Pick a platform
(9:16, 4:5, 1:1; WhatsApp status is capped at 30 s and exported tiny), adjust the start/end if you like, then preview, export one
clip or export all suggestions. Clips fade in and out and are small enough to send on WhatsApp.

## Startup

A splash appears immediately with a progress bar, the time spent, and three pulsing dots - **moving dots mean the app is alive,
frozen dots mean it is stuck**. It names every step and writes timings to `startup.log` (in `%LOCALAPPDATA%\\IdeawoodStudio\\Artists`).
The first start after installing can be slow because Windows scans every new file once; later starts are fast.

## Why files stay small

Lyric videos only become gigabytes when the encoder is told to keep every grain of noise. Every profile caps the video
bitrate, so the worst case is known up front (3 min: Tiny <= ~6 MB, Small <= ~22 MB, Balanced <= ~80 MB, High <= ~230 MB at 1080p),
and the small profiles skip film grain, flicker and shake, which cannot be compressed. A custom target (e.g. 3 MB) picks
resolution, frame rate and audio bitrate to fit. "Shrink an existing video" re-compresses any file the same way.

## How it renders

Everything is one FFmpeg pass: scenes (image Ken-Burns / looped video / gradient) -> crossfades -> darken, blur, grade,
vignette, grain -> optional visualiser + logo -> lyrics drawn by libass from a generated ASS script -> H.264 + AAC MP4.
ASS gives true karaoke sweep, glow and outlines without drawing frames in Python, so exports are fast.

## Run from source

```
pip install -r requirements.txt
# put ffmpeg(.exe), ffprobe(.exe) in bin/ (or on PATH); whisper-cli + a model are only needed for Auto-sync
python main.py
```
Tests: `pip install -r requirements-dev.txt && python -m pytest -q tests`

## Windows EXE

Push to GitHub: the **Build Windows EXE** workflow runs the tests, bundles FFmpeg, whisper.cpp and the English base model,
and produces `IdeawoodStudioArtists-windows.zip`: extract it fully, then run `IdeawoodStudioArtists.exe` from inside the extracted folder (do not run it from inside the zip). The workflow self-tests the built app before publishing. Tag `v1.0.0` to publish a release.

## What was kept from voxcut and what was left behind

Kept: offline speech engine (`asr.py`), cloud client (`cloud.py`), theme, FFmpeg job runner, model management.
Left behind: lecture recorder, whiteboard, screen capture, background removal (RVM / onnxruntime - saves ~100 MB), workspaces,
generic video tools. They don't help a lyric video and would only slow the app down.

## Notes

* Lyric accuracy: Whisper is trained mostly on speech; over loud music it can miss words. Your pasted text is always what
  is shown - only the *timing* comes from the audio - and the match rate is reported so you know when to check step 2 or use Tap to sync.
* Stock media comes from your AI service; keep the generated `.credits.txt` with the video where licences ask for credit.
* Fonts: SIL Open Font License (see `assets/fonts/OFL-LICENSES.txt`). FFmpeg is GPL; whisper.cpp is MIT.
