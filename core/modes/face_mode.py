from __future__ import annotations
import math
import random
import time

import pygame

from core.config import W, H, C_BG_TOP, C_SHAPE, EXPRESSION_INTERVAL
from core.modes.base import Mode


def _blur_surf(surf: pygame.Surface, radius: int) -> pygame.Surface:
    w, h = surf.get_size()
    factor = max(2, radius)
    small = pygame.transform.smoothscale(surf, (max(1, w // factor), max(1, h // factor)))
    return pygame.transform.smoothscale(small, (w, h))


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def ease(t):
    return 2 * t * t if t < 0.5 else -1 + (4 - 2 * t) * t


FACES = {
    "normal": {
        "eyeL": [0.27, 0.30, 0.12, 0.08, 0, 10],
        "eyeR": [0.73, 0.30, 0.12, 0.08, 0, 10],
        "mouth": [0.50, 0.64, 0.13, 0.11, 0.22, 0, 0, 0],
    },
    "happy": {
        "eyeL": [0.27, 0.29, 0.13, 0.10, 0, 15],
        "eyeR": [0.73, 0.29, 0.13, 0.10, 0, 15],
        "mouth": [0.50, 0.65, 0.15, 0.14, 0.20, -0.15, -0.15, 0],
    },
    "blink": {
        "eyeL": [0.27, 0.30, 0.12, 0.01, 0, 2],
        "eyeR": [0.73, 0.30, 0.12, 0.01, 0, 2],
        "mouth": [0.50, 0.64, 0.13, 0.11, 0.22, 0, 0, 0],
    },
    "wonder": {
        "eyeL": [0.27, 0.26, 0.16, 0.16, 0, 60],
        "eyeR": [0.73, 0.26, 0.16, 0.16, 0, 60],
        "mouth": [0.50, 0.70, 0.12, 0.18, 0.08, 0, 0, 0],
    },
    "bobbing": {
        "eyeL": [0.27, 0.30, 0.12, 0.005, 0, 2],
        "eyeR": [0.73, 0.30, 0.12, 0.005, 0, 2],
        "mouth": [0.50, 0.65, 0.14, 0.11, 0.22, -0.1, -0.1, 0],
    },
    "sad": {
        "eyeL": [0.275, 0.32, 0.10, 0.07, 0.1, 8],
        "eyeR": [0.725, 0.32, 0.10, 0.07, -0.1, 8],
        "mouth": [0.50, 0.62, 0.12, 0.10, 0.18, 0.12, 0.12, 0],
    },
    "smirk": {
        "eyeL": [0.26, 0.30, 0.13, 0.08, -0.2, 10],
        "eyeR": [0.74, 0.28, 0.13, 0.09, 0.1, 10],
        "mouth": [0.52, 0.64, 0.13, 0.11, 0.24, -0.08, 0.04, 0.08],
    },
}

HIGHFIVE_SEQUENCE = ["happy", "wonder", "happy"]
HIGHFIVE_DURATION = 0.4


class FaceMode(Mode):
    def __init__(self):
        self.mouth_surf = None
        self._reset_state()

    def _reset_state(self):
        self.cur_face = FACES["normal"]
        self.target_face = FACES["normal"]
        self.anim_t = 1.0

        self.sequence = ["normal", "smirk", "wonder", "bobbing", "happy", "sad"]
        self.seq_idx = 0
        self.next_event = time.time() + EXPRESSION_INTERVAL

        self.next_blink = time.time() + random.uniform(2.0, 6.0)
        self.is_blinking = False
        self.blink_timeout = 0.0

        self.cur_eye = FACES["normal"]["eyeL"]
        self.target_eye = FACES["normal"]["eyeL"]
        self.eye_t = 1.0
        self.eye_speed = 0.05

        self.cur_mouth = FACES["normal"]["mouth"]
        self.target_mouth = FACES["normal"]["mouth"]

        self._highfive_queue: list[str] = []
        self._highfive_timer = 0.0

    def on_enter(self):
        if self.mouth_surf is None:
            self.mouth_surf = pygame.Surface((W, H), pygame.SRCALPHA)

    def lerp_part(self, a, b, t):
        return [lerp(av, bv, t) for av, bv in zip(a, b)]

    def draw_rounded_rect(self, surf, color, rect, radius):
        pygame.draw.rect(surf, color, rect, border_radius=int(radius))

    def draw_mouth_liquid(self, screen, m, offset_y=0, tilt_extra=0):
        self.mouth_surf.fill((0, 0, 0, 0))

        cx, cy = m[0] * W, (m[1] * H) + offset_y
        bw, bh = m[2] * W, m[3] * H
        hg = (m[4] * W) / 2
        lL, lR = m[5] * H / 2, m[6] * H / 2
        rh = bh / 2
        total_tilt = m[7] + tilt_extra

        temp_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        self.draw_rounded_rect(temp_surf, C_SHAPE, (cx - hg - bw, cy + lL - rh, bw, bh), 12)
        self.draw_rounded_rect(temp_surf, C_SHAPE, (cx + hg, cy + lR - rh, bw, bh), 12)
        pygame.draw.rect(temp_surf, C_SHAPE, (cx - hg - 2, cy - rh, (hg * 2) + 4, bh))

        blurred = _blur_surf(temp_surf, 6)
        liquid_mouth = pygame.mask.from_surface(blurred, threshold=140).to_surface(
            setcolor=C_SHAPE, unsetcolor=(0, 0, 0, 0)
        )

        if total_tilt != 0:
            rotated_surf = pygame.transform.rotate(liquid_mouth, math.degrees(-total_tilt))
            new_rect = rotated_surf.get_rect(center=(W // 2, H // 2))
            screen.blit(rotated_surf, new_rect.topleft)
        else:
            screen.blit(liquid_mouth, (0, 0))

    def set_mouth(self, key):
        if key in FACES:
            self.cur_mouth = self.lerp_part(
                self.cur_mouth, self.target_mouth, ease(clamp(self.anim_t, 0, 1))
            )
            self.target_mouth = FACES[key]["mouth"]
            self.anim_t = 0.0

    def set_eyes(self, key, speed=0.05):
        if key in FACES:
            self.cur_eye = self.lerp_part(
                self.cur_eye, self.target_eye, ease(clamp(self.eye_t, 0, 1))
            )
            self.target_eye = FACES[key]["eyeL"]
            self.eye_t = 0.0
            self.eye_speed = speed

    def trigger_highfive(self):
        self._highfive_queue = list(HIGHFIVE_SEQUENCE)
        self._highfive_timer = 0.0
        if self._highfive_queue:
            key = self._highfive_queue.pop(0)
            self.set_mouth(key)
            self.set_eyes(key, speed=0.2)

    def update(self, dt: float, events: list) -> str | None:
        now = time.time()

        # High-five sequence pump
        if self._highfive_queue:
            self._highfive_timer += dt
            if self._highfive_timer >= HIGHFIVE_DURATION:
                self._highfive_timer = 0.0
                key = self._highfive_queue.pop(0)
                self.set_mouth(key)
                self.set_eyes(key, speed=0.2)

        # Auto expression cycle
        if now > self.next_event and not self._highfive_queue:
            self.seq_idx = (self.seq_idx + 1) % len(self.sequence)
            new_key = self.sequence[self.seq_idx]
            self.set_mouth(new_key)
            if not self.is_blinking:
                self.set_eyes(new_key, speed=0.05)
            self.next_event = now + EXPRESSION_INTERVAL

        # Blink
        if not self.is_blinking and now > self.next_blink:
            self.is_blinking = True
            self.set_eyes("blink", speed=0.2)
            self.blink_timeout = now + 0.12

        if self.is_blinking and now > self.blink_timeout:
            self.is_blinking = False
            self.set_eyes(self.sequence[self.seq_idx], speed=0.2)
            self.next_blink = now + random.uniform(2.0, 8.0)

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    self.set_mouth("normal")
                    self.set_eyes("normal")
                elif event.key == pygame.K_2:
                    self.set_mouth("happy")
                    self.set_eyes("happy")
                elif event.key == pygame.K_3:
                    self.set_mouth("sad")
                    self.set_eyes("sad")
                elif event.key == pygame.K_b:
                    self.set_eyes("blink")

        return None

    def draw(self, screen: pygame.Surface) -> None:
        self.anim_t += 0.05
        self.eye_t += self.eye_speed

        mt = ease(clamp(self.anim_t, 0, 1))
        et = ease(clamp(self.eye_t, 0, 1))

        eye_now = self.lerp_part(self.cur_eye, self.target_eye, et)
        mouth_now = self.lerp_part(self.cur_mouth, self.target_mouth, mt)

        bob_y = 0
        bob_tilt = 0
        scan_x = 0

        current_mood = self.sequence[self.seq_idx]
        if current_mood == "bobbing":
            bob_y = math.sin(time.time() * 8) * 15
            bob_tilt = math.sin(time.time() * 4) * 0.15

        if current_mood == "wonder":
            raw_sine = math.sin(time.time() * 3)
            scan_x = math.copysign(math.pow(abs(raw_sine), 0.7), raw_sine) * 25
            bob_y = math.sin(time.time() * 1.5) * 8

        screen.fill(C_BG_TOP)

        for side in [-1, 1]:
            cx = (0.5 + (0.23 * side)) * W + scan_x
            ey = (eye_now[1] * H) + bob_y
            ew, eh = eye_now[2] * W, eye_now[3] * H
            pygame.draw.rect(
                screen,
                C_SHAPE,
                (cx - ew, ey - eh, ew * 2, eh * 2),
                border_radius=int(eye_now[5]),
            )

        self.draw_mouth_liquid(screen, mouth_now, offset_y=bob_y, tilt_extra=bob_tilt)

        for y in range(0, H, 4):
            pygame.draw.line(screen, (0, 0, 0, 20), (0, y), (W, y))
