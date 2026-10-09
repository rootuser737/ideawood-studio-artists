"""Professional fonts for lyric videos.

* 77 open-licence (SIL OFL) display fonts in 7 groups ship in ``assets/fonts`` so the render looks the same on every PC.
* Anything the artist drops into the user fonts folder (or picks with "Add font file") is available too.
* Installed system fonts can be typed in as well - libass uses them directly.
"""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from typing import List

from .paths import bundled_fonts_dir, user_fonts_dir

FONT_EXT = (".ttf", ".otf")


@dataclass(frozen=True)
class FontChoice:
    family: str          # name libass/Qt use to find it
    label: str           # shown in the picker
    mood: str            # one-line "when to use"
    bold: bool = False   # ASS bold flag (only for families that ship a Bold file, like Poppins)


# (family, group, when to use). bold=True only where the family ships a Bold file we want (Poppins).
_TABLE = [
    # --- clean & modern
    ("Poppins", "Clean & modern", "Clean modern pop / afrobeats / R&B (bold)"),
    ("Poppins ExtraBold", "Clean & modern", "Heavy karaoke look, very readable"),
    ("Archivo Black", "Clean & modern", "Solid grotesque - rap, rock"),
    ("Concert One", "Clean & modern", "Friendly rounded - pop, kids, feel-good"),
    ("Patua One", "Clean & modern", "Warm slab-sans - acoustic, folk"),
    ("Fjalla One", "Clean & modern", "Condensed headline - clean urban"),
    # --- poster / bold caps
    ("Bebas Neue", "Poster caps", "Tall poster caps - hip-hop, drill, dancehall"),
    ("Anton", "Poster caps", "Loud condensed headline - trap, street"),
    ("Staatliches", "Poster caps", "Retro poster caps - reggae, funk"),
    ("Squada One", "Poster caps", "Squared condensed - sport, EDM"),
    ("Russo One", "Poster caps", "Techno-sport - gaming, electronic"),
    ("Passion One", "Poster caps", "Fat friendly headline - party, hype"),
    ("Bowlby One", "Poster caps", "Fat heavy headline - big statement lines"),
    ("Lilita One", "Poster caps", "Playful bold - kids, afro-pop"),
    ("Paytone One", "Poster caps", "Round bold - upbeat pop"),
    ("Titan One", "Poster caps", "Chunky bubbly - party, dance"),
    ("Chango", "Poster caps", "Ultra-fat rounded - comedy, hype"),
    ("Changa One", "Poster caps", "Bold italic feel - sport, energy"),
    ("Sigmar One", "Poster caps", "Heavy brush-marker - street, carnival"),
    ("Wendy One", "Poster caps", "Soft fat - cartoon, fun"),
    ("Modak", "Poster caps", "Balloon letters - novelty, kids"),
    ("Londrina Solid", "Poster caps", "Hand-cut poster - indie, urban"),
    ("Boogaloo", "Poster caps", "Casual bold - comic, light"),
    ("Ceviche One", "Poster caps", "Quirky heavy - fashion, playful"),
    ("Fugaz One", "Poster caps", "Italic speed - racing, dancehall"),
    ("Racing Sans One", "Poster caps", "Italic sport - racing, rap"),
    ("Rubik Mono One", "Poster caps", "Wide monospace block - hype, techno"),
    ("Bangers", "Poster caps", "Comic-book shout - hype, dancehall"),
    ("Black Ops One", "Poster caps", "Stencil military - drill, trap"),
    # --- display & retro
    ("Alfa Slab One", "Display & retro", "Chunky slab - gospel, country, vintage"),
    ("Bevan", "Display & retro", "Classic heavy slab - soul, retro"),
    ("Bungee", "Display & retro", "Signage block - dance, hype"),
    ("Bungee Inline", "Display & retro", "Signage with inline - nightlife, retro"),
    ("Bungee Shade", "Display & retro", "Signage with 3D shade - big titles"),
    ("Fascinate", "Display & retro", "Art-deco display - disco, jazz"),
    ("Lemon", "Display & retro", "Round retro display - summer"),
    ("Chelsea Market", "Display & retro", "Shop-sign hand lettering - indie, cafe"),
    ("Spicy Rice", "Display & retro", "Fun swirly display - afro, festival"),
    ("Bigshot One", "Display & retro", "Vintage poster - old-school"),
    ("Original Surfer", "Display & retro", "Surf-shop retro - summer, reggae"),
    # --- elegant serif
    ("Abril Fatface", "Elegant serif", "High-contrast fashion serif - soul, ballads"),
    ("DM Serif Display", "Elegant serif", "Elegant serif - acoustic, cinematic"),
    ("Berkshire Swash", "Elegant serif", "Swash serif - vintage romance"),
    ("Ribeye", "Elegant serif", "Textured old-style - folk, ballad"),
    # --- script & handwriting
    ("Great Vibes", "Script", "Formal calligraphy - wedding, worship, love songs"),
    ("Allura", "Script", "Delicate formal script - love, gospel"),
    ("Alex Brush", "Script", "Brush calligraphy - romantic, luxury"),
    ("Parisienne", "Script", "Elegant flowing script - romantic"),
    ("Sacramento", "Script", "Thin monoline script - dreamy, indie"),
    ("Cookie", "Script", "Soft retro script - feel-good"),
    ("Courgette", "Script", "Casual connected script - acoustic, pop"),
    ("Kaushan Script", "Script", "Brush script - confident, hip-hop soul"),
    ("Leckerli One", "Script", "Bold script - upbeat pop"),
    ("Marck Script", "Script", "Handwritten calligraphy - storytelling"),
    ("Oleo Script", "Script", "Heavy script - party, retro"),
    ("Lobster", "Script", "Friendly retro script - pop, feel-good"),
    ("Pacifico", "Script", "Surf-style script - summer, tropical"),
    ("Shrikhand", "Script", "Fat italic display script - bold romance"),
    ("Knewave", "Script", "Rough brush - rebel, street"),
    ("Gochi Hand", "Script", "Marker handwriting - casual, youth"),
    ("Sue Ellen Francisco", "Script", "Tall handwriting - diary, intimate"),
    ("Emilys Candy", "Script", "Sweet decorative - kids, romance"),
    # --- tech & neon
    ("Righteous", "Tech & neon", "Futuristic rounded - EDM, synth"),
    ("Monoton", "Tech & neon", "Neon multi-line - nightlife, disco (use big, short lines)"),
    ("Audiowide", "Tech & neon", "Wide techno - electronic, sci-fi"),
    ("Faster One", "Tech & neon", "Speed-lines display - racing, EDM"),
    ("Michroma", "Tech & neon", "Wide geometric - clean futuristic"),
    ("Press Start 2P", "Tech & neon", "8-bit pixel - gaming, chiptune"),
    ("Vampiro One", "Tech & neon", "Sharp neo-gothic - dark synth"),
    ("Londrina Shadow", "Tech & neon", "Outlined shadow display - hype"),
    # --- rock / western / gothic
    ("Rye", "Rock & western", "Wild-west slab - country, blues"),
    ("Sancreek", "Rock & western", "Saloon western - country"),
    ("Trade Winds", "Rock & western", "Tiki / pirate - island, reggae"),
    ("Pirata One", "Rock & western", "Blackletter - metal, drill, gothic"),
    ("Metal Mania", "Rock & western", "Heavy-metal gothic - rock, metal"),
    ("Creepster", "Rock & western", "Horror drip - horror, dark trap"),
    ("Kavoon", "Rock & western", "Rough carnival - festival"),
    ("Mouse Memoirs", "Rock & western", "Condensed quirky - indie, rap"),
]
CURATED: List[FontChoice] = [
    FontChoice(fam, fam if fam != "Poppins" else "Poppins Bold", f"{grp} - {mood}", fam == "Poppins")
    for fam, grp, mood in _TABLE
]
FONT_GROUPS = [g for g in dict.fromkeys(g for _f, g, _m in _TABLE)]


def _family_of(path: str) -> str:
    try:
        from PIL import ImageFont
        return ImageFont.truetype(path, 24).getname()[0]
    except Exception:  # noqa: BLE001
        return os.path.splitext(os.path.basename(path))[0].split("-")[0]


def font_files(folder: str) -> List[str]:
    if not os.path.isdir(folder):
        return []
    return sorted(os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(FONT_EXT))


def user_fonts() -> List[FontChoice]:
    seen, out = set(), []
    for p in font_files(user_fonts_dir()):
        fam = _family_of(p)
        if fam not in seen:
            seen.add(fam)
            out.append(FontChoice(fam, f"{fam} (yours)", "Added by you"))
    return out


def catalog() -> List[FontChoice]:
    return CURATED + user_fonts()


def add_user_font(path: str) -> str:
    """Copy a .ttf/.otf into the user fonts folder; returns the family name."""
    if not path.lower().endswith(FONT_EXT):
        raise ValueError("Please choose a .ttf or .otf font file.")
    dest = os.path.join(user_fonts_dir(), os.path.basename(path))
    shutil.copyfile(path, dest)
    return _family_of(dest)


def prepare_fontsdir(workdir: str) -> str:
    """Copy bundled + user fonts into ``<workdir>/fonts`` and return that *relative* name.

    Running ffmpeg with cwd=workdir and ``fontsdir=fonts`` avoids every Windows path-escaping problem.
    """
    d = os.path.join(workdir, "fonts")
    os.makedirs(d, exist_ok=True)
    for src in font_files(bundled_fonts_dir()) + font_files(user_fonts_dir()):
        dst = os.path.join(d, os.path.basename(src))
        if not os.path.exists(dst):
            shutil.copyfile(src, dst)
    return "fonts"
