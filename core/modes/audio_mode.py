from __future__ import annotations
import collections
import time

import numpy as np
import pygame

from core.config import W, H, C_BG_TOP, C_SHAPE
from core.input.audio_capture import AudioCapture
from core.modes.base import Mode

N_BARS = 24
BAR_SLOT = W / N_BARS
BAR_W = int(BAR_SLOT * 0.68)
BAR_RADIUS = BAR_W // 2
MAX_HALF_H = int(H * 0.40)
CENTER_Y = H // 2

# Bar smoothing — fast attack, slow decay (VU-meter feel)
ATTACK = 0.45
DECAY = 0.065
PEAK_DECAY = 0.003   # peak markers fall slowly back to zero

# Beat detection
BEAT_WINDOW = 60     # rolling RMS history (frames)
BEAT_MULT = 1.75     # spike must be this × rolling mean
BEAT_COOLDOWN = 0.35 # seconds between rings
MAX_RINGS = 5

# Ring expansion
RING_SPEED = 270     # px / second
RING_FADE = 1.3      # alpha units / second (ring life = 1 / RING_FADE)


def _lerp_color(c1, c2, t: float) -> tuple:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


class AudioVisualizerMode(Mode):
    def __init__(self):
        self._capture = AudioCapture()
        self._bars = np.zeros(N_BARS)
        self._peaks = np.zeros(N_BARS)
        self._amp_history: collections.deque[float] = collections.deque(maxlen=BEAT_WINDOW)
        self._last_beat = 0.0
        self._rings: list[dict] = []

    def on_enter(self):
        self._capture.start()
        self._bars[:] = 0
        self._peaks[:] = 0
        self._rings.clear()

    def on_exit(self):
        self._capture.stop()

    def update(self, dt: float, events: list) -> str | None:
        raw = self._capture.get_fft_bands(N_BARS)
        amp = self._capture.get_amplitude()
        now = time.time()

        # Per-bar attack/decay smoothing
        rising = raw > self._bars
        self._bars[rising] += (raw[rising] - self._bars[rising]) * ATTACK
        self._bars[~rising] = np.maximum(0.0, self._bars[~rising] - DECAY)

        # Peak markers: snap up instantly, drift down slowly
        snap = self._bars > self._peaks
        self._peaks[snap] = self._bars[snap]
        self._peaks[~snap] = np.maximum(0.0, self._peaks[~snap] - PEAK_DECAY)

        # Energy-based beat detection
        self._amp_history.append(amp)
        if len(self._amp_history) > 10:
            mean_amp = float(np.mean(self._amp_history))
            if (amp > BEAT_MULT * mean_amp
                    and mean_amp > 1e-4
                    and now - self._last_beat > BEAT_COOLDOWN
                    and len(self._rings) < MAX_RINGS):
                self._rings.append({"t": now})
                self._last_beat = now

        # Expire fully-faded rings
        self._rings = [r for r in self._rings if now - r["t"] < 1.0 / RING_FADE]

        return None

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(C_BG_TOP)
        now = time.time()

        # Beat rings — expand from center, fade toward background color
        for ring in self._rings:
            elapsed = now - ring["t"]
            radius = int(RING_SPEED * elapsed)
            alpha = max(0.0, 1.0 - elapsed * RING_FADE)
            color = _lerp_color(C_BG_TOP, C_SHAPE, alpha)
            line_w = max(1, int(3 * alpha))
            if 0 < radius < W:
                pygame.draw.circle(screen, color, (W // 2, H // 2), radius, line_w)

        # Symmetric bars + peak markers
        for i in range(N_BARS):
            cx = int(BAR_SLOT * (i + 0.5))
            half_h = int(MAX_HALF_H * self._bars[i])
            peak_h = int(MAX_HALF_H * self._peaks[i])

            if half_h > 1:
                pygame.draw.rect(
                    screen, C_SHAPE,
                    (cx - BAR_W // 2, CENTER_Y - half_h, BAR_W, half_h * 2),
                    border_radius=BAR_RADIUS,
                )

            # Peak dots: small pill above and below bar
            if peak_h > half_h + 2:
                pygame.draw.rect(
                    screen, C_SHAPE,
                    (cx - BAR_W // 2, CENTER_Y - peak_h - 5, BAR_W, 5),
                    border_radius=2,
                )
                pygame.draw.rect(
                    screen, C_SHAPE,
                    (cx - BAR_W // 2, CENTER_Y + peak_h, BAR_W, 5),
                    border_radius=2,
                )

        # CRT scanlines
        for y in range(0, H, 4):
            pygame.draw.line(screen, (0, 0, 0, 20), (0, y), (W, y))
