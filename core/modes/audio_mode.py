from __future__ import annotations
import math
import time

import numpy as np
import pygame

from core.config import W, H, C_BG_TOP, C_SHAPE
from core.input.audio_capture import AudioCapture
from core.modes.base import Mode

N_BANDS = 32
SMOOTHING = 0.2
CENTER = (W // 2, H // 2)
INNER_R = int(W * 0.18)
OUTER_R_MAX = int(W * 0.42)
BAR_WIDTH_DEG = 360 / N_BANDS - 1.5


class AudioVisualizerMode(Mode):
    def __init__(self):
        self._capture = AudioCapture()
        self._smoothed = np.zeros(N_BANDS)

    def on_enter(self):
        self._capture.start()

    def on_exit(self):
        self._capture.stop()

    def update(self, dt: float, events: list) -> str | None:
        raw = self._capture.get_fft_bands(N_BANDS)
        self._smoothed = self._smoothed * (1 - SMOOTHING) + raw * SMOOTHING
        return None

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(C_BG_TOP)
        cx, cy = CENTER
        now = time.time()

        # Radial frequency bars
        for i, mag in enumerate(self._smoothed):
            angle_deg = (i / N_BANDS) * 360 - 90
            angle_rad = math.radians(angle_deg)

            bar_len = int((OUTER_R_MAX - INNER_R) * mag)
            r_start = INNER_R
            r_end = INNER_R + max(bar_len, 3)

            # Draw as a rounded rectangle rotated to the bar angle
            bar_surf = pygame.Surface((int(W * BAR_WIDTH_DEG / 360 * 2), r_end - r_start), pygame.SRCALPHA)
            bar_w = max(6, int(W * 0.018))
            bar_h = r_end - r_start
            pygame.draw.rect(bar_surf, C_SHAPE, (0, 0, bar_w, bar_h), border_radius=bar_w // 2)

            rotated = pygame.transform.rotate(bar_surf, -angle_deg - 90)
            tip_x = cx + int(math.cos(angle_rad) * (r_start + bar_h // 2))
            tip_y = cy + int(math.sin(angle_rad) * (r_start + bar_h // 2))
            rect = rotated.get_rect(center=(tip_x, tip_y))
            screen.blit(rotated, rect.topleft)

        # Waveform breathing ring
        waveform = self._capture.get_waveform()
        n_pts = 128
        indices = np.linspace(0, len(waveform) - 1, n_pts).astype(int)
        samples = waveform[indices]

        pts = []
        for i, amp in enumerate(samples):
            a = math.radians((i / n_pts) * 360 - 90)
            r = INNER_R + int(amp * INNER_R * 0.6)
            pts.append((cx + int(math.cos(a) * r), cy + int(math.sin(a) * r)))

        if len(pts) >= 2:
            pygame.draw.lines(screen, C_SHAPE, True, pts, 2)

        # CRT scanlines
        for y in range(0, H, 4):
            pygame.draw.line(screen, (0, 0, 0, 20), (0, y), (W, y))
