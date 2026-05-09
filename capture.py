"""
Screen capture module using Win32 API.
"""

import logging
from typing import Sequence

import cv2
import numpy as np
import win32con
import win32gui
import win32ui

from config import Config

logger = logging.getLogger(__name__)

# Resolve base directory for saving screenshots
import os

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Capture:
    """Captures screenshots of a target window via the Win32 GDI API."""

    def __init__(self, window_name: str | None = None) -> None:
        if window_name is None:
            self._hwnd = win32gui.GetDesktopWindow()
        else:
            self._hwnd = win32gui.FindWindow(None, window_name)
            logger.info("Window handle for '%s': %s", window_name, self._hwnd)
            if not self._hwnd:
                raise Exception(f"Window not found: {window_name}")

        left, top, right, bottom = win32gui.GetWindowRect(self._hwnd)
        self._width = right - left
        self._height = bottom - top

        border_pixels = 0
        titlebar_pixels = 0
        self._width -= border_pixels
        self._height -= titlebar_pixels + border_pixels

        self._cropped_x = border_pixels
        self._cropped_y = titlebar_pixels
        self._offset_x = left + self._cropped_x
        self._offset_y = top + self._cropped_y

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def get_screenshot(self) -> np.ndarray:
        """Return a BGR numpy array of the target window's content."""
        w_dc = win32gui.GetWindowDC(self._hwnd)
        dc_obj = win32ui.CreateDCFromHandle(w_dc)
        c_dc = dc_obj.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(dc_obj, self._width, self._height)
        c_dc.SelectObject(bitmap)
        c_dc.BitBlt(
            (0, 0),
            (self._width, self._height),
            dc_obj,
            (self._cropped_x, self._cropped_y),
            win32con.SRCCOPY,
        )

        signed_ints = bitmap.GetBitmapBits(True)
        img = np.frombuffer(signed_ints, dtype="uint8")
        img.shape = (self._height, self._width, 4)

        # Release GDI resources
        dc_obj.DeleteDC()
        c_dc.DeleteDC()
        win32gui.ReleaseDC(self._hwnd, w_dc)
        win32gui.DeleteObject(bitmap.GetHandle())

        # Drop alpha channel
        img = img[..., :3]
        img = np.ascontiguousarray(img)

        screenshot_path = os.path.join(_BASE_DIR, "images", "img1.png")
        cv2.imwrite(screenshot_path, img)

        return img

    # ------------------------------------------------------------------
    # Window enumeration
    # ------------------------------------------------------------------

    @staticmethod
    def list_window_names(target_list: list[str]) -> None:
        """Populate *target_list* with visible window titles."""

        def _enum_handler(hwnd, _ctx):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    target_list.append(title)

        win32gui.EnumWindows(_enum_handler, None)

    # ------------------------------------------------------------------
    # Position helpers
    # ------------------------------------------------------------------

    def get_screen_position(self, pos: Sequence[int]) -> tuple[int, int]:
        """Convert window-relative position to screen-absolute position."""
        return (pos[0] + self._offset_x, pos[1] + self._offset_y)

    def get_screen_minimize(self) -> int:
        """Return 1 if the window is visible, 0 if minimised."""
        placement = win32gui.GetWindowPlacement(self._hwnd)
        if placement[1] == win32con.SW_SHOWMINIMIZED:
            return 0
        return 1

    def get_rect(self) -> tuple[int, int]:
        """Return the current (left, top) of the target window."""
        left, top, _right, _bottom = win32gui.GetWindowRect(self._hwnd)
        return left, top