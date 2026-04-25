from __future__ import annotations
import time

import pygame

HIGHFIVE_THRESHOLD = 0.2  # seconds — tap shorter than this = high-five
MODE_THRESHOLD = 0.2      # seconds — hold longer than this = mode change

EVENT_PREV = "prev_mode"
EVENT_NEXT = "next_mode"
EVENT_HIGHFIVE = "highfive"


class TouchInput:
    """
    Wraps MPR121 capacitive touch on Pi, falls back to keyboard on other platforms.
    Gesture logic:
      Quick tap (< 200ms) on L or R  → high-five
      Hold L (≥ 200ms, release)       → previous mode
      Hold R (≥ 200ms, release)       → next mode
    Keyboard fallback:
      ← arrow  → previous mode
      → arrow  → next mode
      Space    → high-five
    """

    def __init__(self):
        self._mpr121 = None
        self._down_at: dict[int, float] = {}  # pad index → time of touch-down
        self._prev_touched = 0

        try:
            import board
            import busio
            import adafruit_mpr121
            i2c = busio.I2C(board.SCL, board.SDA)
            self._mpr121 = adafruit_mpr121.MPR121(i2c)
        except Exception:
            pass  # Non-Pi environment; keyboard fallback active

    def get_events(self) -> list[str]:
        if self._mpr121 is not None:
            return self._poll_mpr121()
        return []  # Keyboard handled directly in ModeManager via pygame events

    def _poll_mpr121(self) -> list[str]:
        events = []
        now = time.time()
        try:
            touched = self._mpr121.touched()
        except Exception:
            return events

        for pad in (0, 1):
            bit = 1 << pad
            was = bool(self._prev_touched & bit)
            is_ = bool(touched & bit)

            if not was and is_:
                self._down_at[pad] = now

            if was and not is_:
                duration = now - self._down_at.get(pad, now)
                if duration < HIGHFIVE_THRESHOLD:
                    events.append(EVENT_HIGHFIVE)
                else:
                    events.append(EVENT_PREV if pad == 0 else EVENT_NEXT)

        self._prev_touched = touched
        return events

    @staticmethod
    def keyboard_event(event: pygame.event.Event) -> str | None:
        if event.type != pygame.KEYDOWN:
            return None
        if event.key == pygame.K_LEFT:
            return EVENT_PREV
        if event.key == pygame.K_RIGHT:
            return EVENT_NEXT
        if event.key == pygame.K_SPACE:
            return EVENT_HIGHFIVE
        return None
