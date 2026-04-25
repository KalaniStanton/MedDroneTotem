from __future__ import annotations
import collections
import math
import time

import numpy as np
import pygame

from core.config import W, H, C_BG_TOP, C_SHAPE
from core.input.audio_capture import AudioCapture
from core.modes.base import Mode

N_BARS = 24

# Bass circle — radius pulses with low-end energy
BASS_R_MIN = int(W * 0.13)   # smallest circle (silence)
BASS_R_MAX = int(W * 0.20)   # largest circle (full bass)

# Bars protruding from the circle edge
BAR_MAX_LEN = int(W * 0.25)
BAR_W = 13
PEAK_DOT_R = 5

CX, CY = W // 2, H // 2

# Smoothing
ATTACK = 0.45
DECAY = 0.065
PEAK_DECAY = 0.003

# Beat detection
BEAT_WINDOW = 60
BEAT_MULT = 1.75
BEAT_COOLDOWN = 0.35
MAX_RINGS = 5

# Ring expansion
RING_SPEED = 270   # px/s
RING_FADE = 1.3    # alpha/s


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

        # Per-bar attack/decay
        rising = raw > self._bars
        self._bars[rising] += (raw[rising] - self._bars[rising]) * ATTACK
        self._bars[~rising] = np.maximum(0.0, self._bars[~rising] - DECAY)

        # Peak markers: snap up, drift down
        snap = self._bars > self._peaks
        self._peaks[snap] = self._bars[snap]
        self._peaks[~snap] = np.maximum(0.0, self._peaks[~snap] - PEAK_DECAY)

        # Beat detection
        self._amp_history.append(amp)
        if len(self._amp_history) > 10:
            mean_amp = float(np.mean(self._amp_history))
            if (amp > BEAT_MULT * mean_amp
                    and mean_amp > 1e-4
                    and now - self._last_beat > BEAT_COOLDOWN
                    and len(self._rings) < MAX_RINGS):
                self._rings.append({"t": now})
                self._last_beat = now

        self._rings = [r for r in self._rings if now - r["t"] < 1.0 / RING_FADE]
        return None

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(C_BG_TOP)
        now = time.time()

        # --- Beat rings (behind everything) ---
        for ring in self._rings:
            elapsed = now - ring["t"]
            radius = int(RING_SPEED * elapsed)
            alpha = max(0.0, 1.0 - elapsed * RING_FADE)
            color = _lerp_color(C_BG_TOP, C_SHAPE, alpha)
            width = max(1, int(3 * alpha))
            if 0 < radius < W:
                pygame.draw.circle(screen, color, (CX, CY), radius, width)

        # Bass circle radius driven by low-end energy
        bass_mag = float(np.mean(self._bars[:3]))
        bass_r = int(BASS_R_MIN + (BASS_R_MAX - BASS_R_MIN) * bass_mag)

        # --- Frequency bars (drawn before circle so circle covers the roots) ---
        # Angles sweep from -π/2 (bottom) to +π/2 (top).
        # Bar 0 (lowest freq) is at the bottom junction; bar N-1 (highest) at the top.
        # Right arc: (CX + r*cos(a), CY - r*sin(a))
        # Left arc:  (CX - r*cos(a), CY - r*sin(a))  — mirror across the vertical axis
        # Junction points (cos_a ≈ 0) are at top/bottom; drawn once to avoid overlap.
        for i in range(N_BARS):
            angle = -math.pi / 2 + (i / (N_BARS - 1)) * math.pi
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            bar_len = int(BAR_MAX_LEN * self._bars[i])
            peak_r = bass_r + int(BAR_MAX_LEN * self._peaks[i])
            on_axis = abs(cos_a) < 0.01  # top/bottom junction — skip mirror

            sy = int(CY - bass_r * sin_a)
            ey = int(CY - (bass_r + bar_len) * sin_a)

            # Right arc
            sx_r = int(CX + bass_r * cos_a)
            ex_r = int(CX + (bass_r + bar_len) * cos_a)

            if bar_len > 1:
                pygame.draw.line(screen, C_SHAPE, (sx_r, sy), (ex_r, ey), BAR_W)
                pygame.draw.circle(screen, C_SHAPE, (ex_r, ey), BAR_W // 2)

            # Left arc (skip when on the vertical axis — already drawn by right arc)
            if not on_axis and bar_len > 1:
                sx_l = int(CX - bass_r * cos_a)
                ex_l = int(CX - (bass_r + bar_len) * cos_a)
                pygame.draw.line(screen, C_SHAPE, (sx_l, sy), (ex_l, ey), BAR_W)
                pygame.draw.circle(screen, C_SHAPE, (ex_l, ey), BAR_W // 2)

            # Peak dots (only when peak has separated from bar tip)
            if self._peaks[i] > self._bars[i] + 0.03:
                py = int(CY - peak_r * sin_a)
                px_r = int(CX + peak_r * cos_a)
                pygame.draw.circle(screen, C_SHAPE, (px_r, py), PEAK_DOT_R)
                if not on_axis:
                    px_l = int(CX - peak_r * cos_a)
                    pygame.draw.circle(screen, C_SHAPE, (px_l, py), PEAK_DOT_R)

        # --- Bass circle drawn on top of bar roots for a clean join ---
        pygame.draw.circle(screen, C_SHAPE, (CX, CY), bass_r)

        # CRT scanlines
        for y in range(0, H, 4):
            pygame.draw.line(screen, (0, 0, 0, 20), (0, y), (W, y))
