"""
Windows transparent overlay adapter.
"""

from __future__ import annotations

from collections.abc import Callable
import logging
import tkinter

import pywintypes
import win32api
import win32con

from platforms.base import OverlayText

logger = logging.getLogger(__name__)

_EX_STYLE = (
    win32con.WS_EX_COMPOSITED
    | win32con.WS_EX_LAYERED
    | win32con.WS_EX_NOACTIVATE
    | win32con.WS_EX_TOPMOST
    | win32con.WS_EX_TRANSPARENT
)

_TRANSPARENT_COLOUR = "#add123"


class WindowsOverlayBackend:
    """Full-screen transparent overlay that renders text labels."""

    def __init__(self) -> None:
        self.win = tkinter.Tk()
        self.win.config(bg=_TRANSPARENT_COLOUR)
        self.win.config(highlightbackground=_TRANSPARENT_COLOUR)
        self.win.wm_attributes("-transparentcolor", _TRANSPARENT_COLOUR)
        self.win.attributes("-fullscreen", True)
        self.win.wm_attributes("-topmost", True)
        self.win.wm_attributes("-disabled", True)
        self.win.overrideredirect(True)

        self._labels: list[tkinter.Label] = []
        logger.info("Overlay window created")

    def after(self, delay_ms: int, callback: Callable[[], None]) -> None:
        """Schedule a callback in the Tk event loop."""
        self.win.after(delay_ms, callback)

    def run(self) -> None:
        """Enter the Tk main loop."""
        self.win.mainloop()

    def update(self) -> None:
        """Flush pending Tk updates."""
        self.win.update()

    def clear(self) -> None:
        """Remove all previously placed labels."""
        for label in self._labels:
            label.destroy()
        self._labels.clear()

    def clear_labels(self) -> None:
        """Backward-compatible label clearing method."""
        self.clear()

    def show_text(self, item: OverlayText) -> None:
        """Create and place a text label at screen coordinates."""
        self.labeler(item.text, item.x, item.y, item.width, item.height, item.font_size)

    def labeler(
        self,
        text: str,
        x: int,
        y: int,
        width: int,
        height: int,
        font_size: int,
    ) -> None:
        """Backward-compatible text label method."""
        del width, height
        logger.debug("Label at (%d, %d): %s", x, y, text)
        label = tkinter.Label(
            self.win,
            text=text,
            font=("Times", font_size),
            fg="white",
            bg="black",
        )
        label.place(x=x, y=y)
        label.configure(anchor="center")
        label.master.wm_attributes("-alpha", "1")
        label.master.lift()

        h_window = pywintypes.HANDLE(int(label.master.frame(), 16))
        win32api.SetWindowLong(h_window, win32con.GWL_EXSTYLE, _EX_STYLE)

        self._labels.append(label)

    def stop(self) -> None:
        """Destroy all child widgets."""
        for child in self.win.winfo_children():
            child.destroy()
        self._labels.clear()

    def destroy(self) -> None:
        """Destroy the overlay window."""
        self.stop()
        self.win.destroy()

    def start(self) -> None:
        """Backward-compatible main loop entry point."""
        self.run()
