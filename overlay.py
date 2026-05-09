"""
Transparent overlay window for displaying translated text on screen.
"""

import logging

import pywintypes
import tkinter
import win32api
import win32con

logger = logging.getLogger(__name__)

# Click-through window style
_EX_STYLE = (
    win32con.WS_EX_COMPOSITED
    | win32con.WS_EX_LAYERED
    | win32con.WS_EX_NOACTIVATE
    | win32con.WS_EX_TOPMOST
    | win32con.WS_EX_TRANSPARENT
)

# The colour key used for transparency
_TRANSPARENT_COLOUR = "#add123"


class Overlay:
    """Full-screen transparent overlay that renders text labels on top of other windows."""

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

    # ------------------------------------------------------------------
    # Label management
    # ------------------------------------------------------------------

    def clear_labels(self) -> None:
        """Remove all previously placed labels."""
        for label in self._labels:
            label.destroy()
        self._labels.clear()

    def labeler(
        self,
        text: str,
        x: int,
        y: int,
        width: int,
        height: int,
        font_size: int,
    ) -> None:
        """Create and place a text label at the given screen coordinates."""
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

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Destroy all child widgets."""
        for child in self.win.winfo_children():
            child.destroy()
        self._labels.clear()

    def start(self) -> None:
        """Enter the Tk main loop."""
        self.win.mainloop()