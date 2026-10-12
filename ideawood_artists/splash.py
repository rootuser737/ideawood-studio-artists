"""Startup splash: shows at once, shows every step, and makes it obvious whether the app is working or frozen.

* A step list with a real progress bar and the time spent so far.
* Three pulsing dots that animate continuously: if they keep moving, the app is alive; if they freeze, it is stuck.
* After 20 s on one step it says what it is waiting for (the first start after installing is slow because Windows
  scans every new file once).
* Every step is written with its timing to ``startup.log`` so slow starts can be diagnosed instead of guessed.
Kept deliberately light: it imports only Qt and ``paths`` so it can appear before the rest of the app is loaded.
"""
from __future__ import annotations

import math
import os
import time

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QWidget

from .paths import asset_path, user_data_dir

T0 = time.perf_counter()
W, H = 600, 330


def log_path() -> str:
    return os.path.join(user_data_dir(), "startup.log")


def write_log(text: str):
    try:
        with open(log_path(), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')}  +{time.perf_counter() - T0:6.1f}s  {text}\n")
    except OSError:
        pass


class Splash(QWidget):
    def __init__(self, title: str = "Ideawood Studio for Artists", version: str = ""):
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(W, H)
        self.title, self.version = title, version
        self.pct, self.text, self.hint = 0.0, "Starting...", ""
        self.step_t0 = self.t0 = time.perf_counter()
        pm = QPixmap(asset_path("icon.png"))
        self.logo = pm.scaled(84, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not pm.isNull() else None
        scr = QGuiApplication.primaryScreen()
        if scr:
            g = scr.availableGeometry()
            self.move(g.center().x() - W // 2, g.center().y() - H // 2)
        self.tm = QTimer(self)
        self.tm.timeout.connect(self.update)
        self.tm.start(40)
        write_log("---- start ----")

    def step(self, text: str, pct: float):
        now = time.perf_counter()
        write_log(f"{pct:5.0f}%  {text}   (previous step took {now - self.step_t0:.1f}s)")
        self.text, self.pct, self.step_t0 = text, max(self.pct, pct), now
        self.update()
        QApplication.processEvents()

    def finish(self):
        write_log(f"100%  ready - total {time.perf_counter() - self.t0:.1f}s")
        self.tm.stop()
        self.close()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        now = time.perf_counter()
        card = QPainterPath()
        card.addRoundedRect(QRectF(6, 6, W - 12, H - 12), 18, 18)
        p.fillPath(card, QColor("#12151c"))
        p.setPen(QPen(QColor("#2b3140"), 1.5))
        p.drawPath(card)
        x0 = 36
        if self.logo:
            p.drawPixmap(x0, 38, self.logo)
            x0 += 104
        p.setPen(QColor("#f1f3f7"))
        f = QFont(self.font())
        f.setPointSizeF(19)
        f.setBold(True)
        p.setFont(f)
        p.drawText(x0, 72, self.title)
        f.setPointSizeF(10)
        f.setBold(False)
        p.setFont(f)
        p.setPen(QColor("#8d96a8"))
        p.drawText(x0, 98, ("Lyric videos for artists   " + (f"v{self.version}" if self.version else "")).strip())
        # step text
        f.setPointSizeF(11.5)
        p.setFont(f)
        p.setPen(QColor("#dfe4ee"))
        p.drawText(QRectF(36, 150, W - 72, 26), Qt.AlignLeft | Qt.AlignVCenter,
                   QFontMetrics(f).elidedText(self.text, Qt.ElideRight, W - 72))
        # progress bar (+ a moving shimmer so it never looks static)
        bar = QRectF(36, 186, W - 72, 10)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#232a38"))
        p.drawRoundedRect(bar, 5, 5)
        done = QRectF(bar.left(), bar.top(), bar.width() * min(self.pct, 100) / 100.0, bar.height())
        p.setBrush(QColor("#4da3ff"))
        p.drawRoundedRect(done, 5, 5)
        if done.width() > 12:
            sh = (now * 0.9) % 1.0
            sx = done.left() + sh * done.width()
            p.setBrush(QColor(255, 255, 255, 70))
            p.drawRoundedRect(QRectF(max(done.left(), sx - 18), done.top(), min(36, done.right() - max(done.left(), sx - 18)), done.height()), 5, 5)
        # heartbeat dots
        for i in range(3):
            a = 0.5 + 0.5 * math.sin(now * 5.0 - i * 0.9)
            p.setBrush(QColor(77, 163, 255, int(70 + 185 * a)))
            r = 4 + 3 * a
            p.drawEllipse(QRectF(36 + i * 22 - r / 2 + 4, 224 - r / 2 + 4, r, r))
        # timing + honest hint
        el, same = now - self.t0, now - self.step_t0
        p.setPen(QColor("#8d96a8"))
        f.setPointSizeF(9.5)
        p.setFont(f)
        p.drawText(QRectF(120, 214, W - 156, 22), Qt.AlignLeft | Qt.AlignVCenter, f"{el:0.0f} s elapsed")
        hint = ""
        if same > 90:
            hint = ("Very slow. If the three dots above have STOPPED moving the app is frozen - close it and open startup.log "
                    "in " + os.path.dirname(log_path()))
        elif same > 20:
            hint = ("Still working - the dots keep moving, so the app is alive. The first start after installing can take a "
                    "minute while Windows checks every new file once; the next starts are fast.")
        if hint:
            p.drawText(QRectF(36, 252, W - 72, 52), Qt.AlignLeft | Qt.TextWordWrap, hint)
