"""
Backward-compatible capture module.

New code should import platform capture backends through platforms.factory.
"""

from platforms.windows.capture import WindowsCaptureBackend as Capture

__all__ = ["Capture"]
