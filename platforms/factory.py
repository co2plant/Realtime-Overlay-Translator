"""
Factory functions for selecting platform adapters.
"""

from __future__ import annotations

import sys

from config import Config
from platforms.base import CaptureBackend, OverlayBackend, PlatformNotSupportedError


def create_capture_backend(
    config: Config | None = None,
    window_id: str | None = None,
) -> CaptureBackend:
    """Create the capture backend for the current OS."""
    del config
    if sys.platform == "win32":
        from platforms.windows.capture import WindowsCaptureBackend

        return WindowsCaptureBackend(window_id)

    raise PlatformNotSupportedError(f"Unsupported platform for capture: {sys.platform}")


def create_overlay_backend(config: Config | None = None) -> OverlayBackend:
    """Create the overlay backend for the current OS."""
    del config
    if sys.platform == "win32":
        from platforms.windows.overlay import WindowsOverlayBackend

        return WindowsOverlayBackend()

    raise PlatformNotSupportedError(f"Unsupported platform for overlay: {sys.platform}")
