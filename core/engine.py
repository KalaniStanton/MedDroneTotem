from __future__ import annotations

import pygame

from core.config import W, H, FPS, FULLSCREEN
from core.input.touch import TouchInput, EVENT_PREV, EVENT_NEXT, EVENT_HIGHFIVE
from core.modes.base import Mode
from core.modes.face_mode import FaceMode
from core.modes.audio_mode import AudioVisualizerMode
from core.modes.message_mode import MessageDisplayMode

MODE_ORDER = ["face", "audio", "message"]


class ModeManager:
    def __init__(self):
        self._modes: dict[str, Mode] = {
            "face": FaceMode(),
            "audio": AudioVisualizerMode(),
            "message": MessageDisplayMode(),
        }
        self._order = MODE_ORDER
        self._current_name = "face"
        self._touch = TouchInput()

    def _switch_to(self, name: str, screen: pygame.Surface):
        self._modes[self._current_name].on_exit()
        self._current_name = name
        mode = self._modes[self._current_name]
        mode.on_enter()

    def _next_mode_name(self, direction: int) -> str:
        idx = self._order.index(self._current_name)
        return self._order[(idx + direction) % len(self._order)]

    def run(self):
        pygame.init()
        flags = pygame.FULLSCREEN if FULLSCREEN else 0
        screen = pygame.display.set_mode((W, H), flags)
        pygame.display.set_caption("MedDroneTotem")
        clock = pygame.time.Clock()

        active = self._modes[self._current_name]
        active.on_enter()

        running = True
        while running:
            dt = clock.tick(FPS) / 1000.0
            raw_events = pygame.event.get()

            next_mode: str | None = None

            # Translate pygame events + touch to gesture strings, pass remainder to mode
            mode_events = []
            for event in raw_events:
                if event.type == pygame.QUIT:
                    running = False
                    break

                gesture = TouchInput.keyboard_event(event)
                if gesture:
                    if gesture == EVENT_PREV:
                        next_mode = self._next_mode_name(-1)
                    elif gesture == EVENT_NEXT:
                        next_mode = self._next_mode_name(1)
                    elif gesture == EVENT_HIGHFIVE:
                        face: FaceMode = self._modes["face"]  # type: ignore[assignment]
                        face.trigger_highfive()
                else:
                    mode_events.append(event)

            # MPR121 gestures (Pi only; returns [] on Mac)
            for gesture in self._touch.get_events():
                if gesture == EVENT_PREV:
                    next_mode = self._next_mode_name(-1)
                elif gesture == EVENT_NEXT:
                    next_mode = self._next_mode_name(1)
                elif gesture == EVENT_HIGHFIVE:
                    face = self._modes["face"]  # type: ignore[assignment]
                    face.trigger_highfive()  # type: ignore[attr-defined]

            if not running:
                break

            # Let the active mode process remaining events and update state
            mode_next = active.update(dt, mode_events)
            if mode_next and mode_next in self._modes:
                next_mode = mode_next

            if next_mode and next_mode != self._current_name:
                self._switch_to(next_mode, screen)
                active = self._modes[self._current_name]

            active.draw(screen)
            pygame.display.flip()

        pygame.quit()
