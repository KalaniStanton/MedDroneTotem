from __future__ import annotations
import pygame


class Mode:
    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass

    def update(self, dt: float, events: list) -> str | None:
        """Process events/logic. Return a mode name string to switch, or None to stay."""
        raise NotImplementedError

    def draw(self, screen: pygame.Surface) -> None:
        raise NotImplementedError
