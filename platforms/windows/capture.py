"""
Windows screen capture adapter using Win32 GDI APIs.
"""

from __future__ import annotations

import logging
import os
from typing import Sequence

import numpy as np
import win32con
import win32gui
import win32ui

from platforms.base import CapturedFrame, WindowInfo

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class WindowsCaptureBackend:
    """Captures screenshots of a target window via the Win32 GDI API."""

    def __init__(self, window_id: str | None = None) -> None:
        self._hwnd = 0
        self._width = 0
        self._height = 0
        self._cropped_x = 0
        self._cropped_y = 0
        self._offset_x = 0
        self._offset_y = 0
        self._window_id = None

        if window_id is None:
            self._set_hwnd(win32gui.GetDesktopWindow(), None)
        else:
            self.select_window(window_id)

    def _set_hwnd(self, hwnd: int, window_id: str | None) -> None:
        if not hwnd:
            raise Exception(f"Window not found: {window_id}")

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        border_pixels = 0
        titlebar_pixels = 0

        self._hwnd = hwnd
        self._window_id = window_id
        self._width = width - border_pixels
        self._height = height - titlebar_pixels - border_pixels
        self._cropped_x = border_pixels
        self._cropped_y = titlebar_pixels
        self._offset_x = left + self._cropped_x
        self._offset_y = top + self._cropped_y

    @staticmethod
    def _list_windows() -> list[WindowInfo]:
        windows: list[WindowInfo] = []

        def _enum_handler(hwnd, _ctx):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append(WindowInfo(id=title, title=title))

        win32gui.EnumWindows(_enum_handler, None)
        return windows

    def list_windows(self) -> list[WindowInfo]:
        """Return visible windows."""
        return self._list_windows()

    @staticmethod
    def list_window_names(target_list: list[str]) -> None:
        """Backward-compatible visible window title collector."""
        target_list.extend(window.title for window in WindowsCaptureBackend._list_windows())

    def select_window(self, window_id: str) -> None:
        """Select a visible window by title."""
        hwnd = win32gui.FindWindow(None, window_id)
        logger.info("Window handle for '%s': %s", window_id, hwnd)
        self._set_hwnd(hwnd, window_id)

    def get_screenshot(self) -> np.ndarray:
        """Return a BGR numpy array of the selected window content."""
        import cv2

        w_dc = None
        dc_obj = None
        c_dc = None
        bitmap = None
        bitmap_created = False

        try:
            w_dc = win32gui.GetWindowDC(self._hwnd)
            dc_obj = win32ui.CreateDCFromHandle(w_dc)
            c_dc = dc_obj.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(dc_obj, self._width, self._height)
            bitmap_created = True
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

            img = img[..., :3]
            img = np.ascontiguousarray(img)

            screenshot_path = os.path.join(_BASE_DIR, "images", "img1.png")
            cv2.imwrite(screenshot_path, img)
        finally:
            if c_dc is not None:
                c_dc.DeleteDC()
            if dc_obj is not None:
                dc_obj.DeleteDC()
            if w_dc:
                win32gui.ReleaseDC(self._hwnd, w_dc)
            if bitmap_created and bitmap is not None:
                win32gui.DeleteObject(bitmap.GetHandle())

        return img

    def capture_frame(self) -> CapturedFrame:
        """Capture the selected window and return image plus screen origin."""
        image = self.get_screenshot()
        x, y = self.get_rect()
        height, width = image.shape[:2]
        return CapturedFrame(image=image, screen_x=x, screen_y=y, width=width, height=height)

    def get_screen_position(self, pos: Sequence[int]) -> tuple[int, int]:
        """Convert window-relative position to screen-absolute position."""
        return (pos[0] + self._offset_x, pos[1] + self._offset_y)

    def get_screen_minimize(self) -> int:
        """Return 1 if the window is visible, 0 if minimized."""
        placement = win32gui.GetWindowPlacement(self._hwnd)
        if placement[1] == win32con.SW_SHOWMINIMIZED:
            return 0
        return 1

    def get_rect(self) -> tuple[int, int]:
        """Return the current left/top of the selected window."""
        left, top, _right, _bottom = win32gui.GetWindowRect(self._hwnd)
        return left, top
