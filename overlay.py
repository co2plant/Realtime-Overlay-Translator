"""
Backward-compatible overlay module.

New code should import platform overlay backends through platforms.factory.
"""

from platforms.windows.overlay import WindowsOverlayBackend as Overlay

__all__ = ["Overlay"]
