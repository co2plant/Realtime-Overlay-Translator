"""
OS-neutral platform adapter interfaces and data objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

import numpy as np


class PlatformNotSupportedError(RuntimeError):
    """Raised when the current OS does not have a platform adapter."""


@dataclass(frozen=True)
class WindowInfo:
    """A capture target shown to the user."""

    id: str
    title: str


@dataclass(frozen=True)
class CapturedFrame:
    """Image frame captured from a target window plus screen origin."""

    image: np.ndarray
    screen_x: int
    screen_y: int
    width: int
    height: int


@dataclass(frozen=True)
class OverlayText:
    """Text item to render on an overlay."""

    text: str
    x: int
    y: int
    width: int
    height: int
    font_size: int


class CaptureBackend(Protocol):
    """Common interface for platform capture implementations."""

    def list_windows(self) -> list[WindowInfo]:
        """Return visible capture targets."""

    def select_window(self, window_id: str) -> None:
        """Select a capture target by platform-neutral id."""

    def capture_frame(self) -> CapturedFrame:
        """Capture the currently selected target."""


class OverlayBackend(Protocol):
    """Common interface for platform overlay implementations."""

    def after(self, delay_ms: int, callback: Callable[[], None]) -> None:
        """Schedule a callback in the overlay UI loop."""

    def run(self) -> None:
        """Start the overlay UI loop."""

    def update(self) -> None:
        """Flush pending overlay UI updates."""

    def clear(self) -> None:
        """Clear all rendered overlay text."""

    def show_text(self, item: OverlayText) -> None:
        """Render one overlay text item."""

    def destroy(self) -> None:
        """Destroy the overlay window."""
