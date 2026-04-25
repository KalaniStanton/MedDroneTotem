from __future__ import annotations
import time

import pygame

from core.config import W, H, C_BG_TOP, C_SHAPE, MESSAGES
from core.modes.base import Mode

DISPLAY_DURATION = 4.0
TRANSITION_DURATION = 0.6


def ease_out(t: float) -> float:
    return 1 - (1 - t) ** 3


class MessageDisplayMode(Mode):
    def __init__(self):
        self._font_large: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None
        self._idx = 0
        self._phase = "in"  # "in" | "hold" | "out"
        self._phase_t = 0.0
        self._alpha = 0
        self._scale = 0.7

    def on_enter(self):
        if self._font_large is None:
            pygame.font.init()
            size_large = int(H * 0.11)
            size_small = int(H * 0.065)
            self._font_large = pygame.font.SysFont("helvetica", size_large, bold=True)
            self._font_small = pygame.font.SysFont("helvetica", size_small)
        self._phase = "in"
        self._phase_t = 0.0

    def _advance(self):
        self._idx = (self._idx + 1) % len(MESSAGES)
        self._phase = "in"
        self._phase_t = 0.0

    def update(self, dt: float, events: list) -> str | None:
        self._phase_t += dt

        if self._phase == "in":
            p = min(self._phase_t / TRANSITION_DURATION, 1.0)
            self._alpha = int(255 * ease_out(p))
            self._scale = 0.7 + 0.3 * ease_out(p)
            if p >= 1.0:
                self._phase = "hold"
                self._phase_t = 0.0

        elif self._phase == "hold":
            self._alpha = 255
            self._scale = 1.0
            if self._phase_t >= DISPLAY_DURATION:
                self._phase = "out"
                self._phase_t = 0.0

        elif self._phase == "out":
            p = min(self._phase_t / TRANSITION_DURATION, 1.0)
            self._alpha = int(255 * (1 - ease_out(p)))
            self._scale = 1.0 - 0.3 * ease_out(p)
            if p >= 1.0:
                self._advance()

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                self._phase = "out"
                self._phase_t = 0.0

        return None

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(C_BG_TOP)

        msg = MESSAGES[self._idx]
        words = msg.split()

        # Wrap long messages to two lines
        if len(words) > 3:
            mid = len(words) // 2
            lines = [" ".join(words[:mid]), " ".join(words[mid:])]
        else:
            lines = [msg]

        line_height = int(H * 0.13)
        total_h = line_height * len(lines)
        start_y = H // 2 - total_h // 2

        for i, line in enumerate(lines):
            surf = self._font_large.render(line, True, C_SHAPE)

            scaled_w = int(surf.get_width() * self._scale)
            scaled_h = int(surf.get_height() * self._scale)
            if scaled_w > 0 and scaled_h > 0:
                scaled = pygame.transform.smoothscale(surf, (scaled_w, scaled_h))
                scaled.set_alpha(self._alpha)
                x = W // 2 - scaled_w // 2
                y = start_y + i * line_height - (scaled_h - surf.get_height()) // 2
                screen.blit(scaled, (x, y))

        # CRT scanlines
        for y in range(0, H, 4):
            pygame.draw.line(screen, (0, 0, 0, 20), (0, y), (W, y))
