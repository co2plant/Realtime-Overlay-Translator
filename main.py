"""
Bridge – Realtime Overlay Translator

Main application entry-point.  Provides the GUI (CustomTkinter) and
delegates the translation pipeline to :mod:`pipeline`.
"""

import logging
import os
import sys

import customtkinter
from PIL import Image

from config import Config
from capture import Capture
from overlay import Overlay
from pipeline import TranslationPipeline

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Resolve paths relative to this file (never rely on os.chdir)
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_IMAGE_DIR = os.path.join(_BASE_DIR, "images")


class App(customtkinter.CTk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        self._config = Config()
        self._window_name: str | None = None
        self._overlay: Overlay | None = None
        self._pipeline: TranslationPipeline | None = None

        self.title("Bridge - RealtimeOverlayTranslator")
        self.geometry("700x450")

        # Grid layout 1×2
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._load_images()
        self._build_navigation()
        self._build_home_frame()
        self._build_second_frame()
        self._build_settings_frame()

        self._select_frame("home")

    # ==================================================================
    # Image loading
    # ==================================================================

    def _load_images(self) -> None:
        self._logo = customtkinter.CTkImage(
            Image.open(os.path.join(_IMAGE_DIR, "main_icon.png")), size=(32, 32)
        )
        self._large_preview = customtkinter.CTkImage(
            Image.open(os.path.join(_IMAGE_DIR, "img1.png")), size=(500, 300)
        )
        self._home_icon = customtkinter.CTkImage(
            light_image=Image.open(os.path.join(_IMAGE_DIR, "main_icon.png")),
            dark_image=Image.open(os.path.join(_IMAGE_DIR, "main_icon.png")),
            size=(20, 20),
        )
        self._setting_icon = customtkinter.CTkImage(
            light_image=Image.open(os.path.join(_IMAGE_DIR, "setting_icon.png")),
            dark_image=Image.open(os.path.join(_IMAGE_DIR, "setting_icon.png")),
            size=(20, 20),
        )

    # ==================================================================
    # Navigation sidebar
    # ==================================================================

    def _build_navigation(self) -> None:
        nav = customtkinter.CTkFrame(self, corner_radius=0)
        nav.grid(row=0, column=0, sticky="nsew")
        nav.grid_rowconfigure(4, weight=1)

        customtkinter.CTkLabel(
            nav,
            text="  Bridge",
            image=self._logo,
            compound="left",
            font=customtkinter.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=20)

        btn_style = dict(
            corner_radius=0,
            height=40,
            border_spacing=10,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            anchor="w",
        )

        self._btn_home = customtkinter.CTkButton(
            nav, text="Detect Window", image=self._home_icon,
            command=lambda: self._select_frame("home"), **btn_style,
        )
        self._btn_home.grid(row=1, column=0, sticky="ew")

        self._btn_frame2 = customtkinter.CTkButton(
            nav, text="Frame 2", image=self._home_icon,
            command=lambda: self._select_frame("frame_2"), **btn_style,
        )
        self._btn_frame2.grid(row=2, column=0, sticky="ew")

        self._btn_settings = customtkinter.CTkButton(
            nav, text="Setting", image=self._setting_icon,
            command=lambda: self._select_frame("settings"), **btn_style,
        )
        self._btn_settings.grid(row=3, column=0, sticky="ew")

        customtkinter.CTkOptionMenu(
            nav,
            values=["Light", "Dark", "System"],
            command=self._on_appearance_change,
        ).grid(row=6, column=0, padx=20, pady=20, sticky="s")

        self._nav_buttons = {
            "home": self._btn_home,
            "frame_2": self._btn_frame2,
            "settings": self._btn_settings,
        }

    # ==================================================================
    # Home frame
    # ==================================================================

    def _build_home_frame(self) -> None:
        self._home_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._home_frame.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            self._home_frame, text="", image=self._large_preview,
        ).grid(row=0, column=0, padx=20, pady=10)

        customtkinter.CTkButton(
            self._home_frame, width=500, text="Detect Window",
            command=self._on_detect,
        ).grid(row=1, column=0, padx=20, pady=5)

        combo_var = customtkinter.StringVar(value="Click 'Detect Window' first")
        self._combo = customtkinter.CTkComboBox(
            self._home_frame, width=500, values=[],
            command=self._on_window_selected, variable=combo_var,
        )
        self._combo.grid(row=2, column=0, padx=20, pady=5)

        self._start_btn = customtkinter.CTkButton(
            self._home_frame, width=500, text="Start",
            compound="bottom", state="disabled",
            command=self._on_start,
        )
        self._start_btn.grid(row=3, column=0, padx=20, pady=5)

    # ==================================================================
    # Second frame (placeholder)
    # ==================================================================

    def _build_second_frame(self) -> None:
        self._second_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")

    # ==================================================================
    # Settings frame
    # ==================================================================

    def _build_settings_frame(self) -> None:
        self._settings_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self._settings_frame.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(self._settings_frame, text="Client ID:").grid(
            row=0, column=0, padx=20, pady=10,
        )
        self._entry_id = customtkinter.CTkEntry(self._settings_frame)
        self._entry_id.grid(row=1, column=0, padx=20, pady=10)
        self._entry_id.insert(0, self._config.client_id)

        customtkinter.CTkLabel(self._settings_frame, text="Client Secret:").grid(
            row=2, column=0, padx=20, pady=10,
        )
        self._entry_secret = customtkinter.CTkEntry(self._settings_frame)
        self._entry_secret.grid(row=3, column=0, padx=20, pady=10)
        self._entry_secret.insert(0, self._config.client_secret)

        customtkinter.CTkButton(
            self._settings_frame, text="Save", command=self._on_save_settings,
        ).grid(row=4, column=0, padx=20, pady=20)

    # ==================================================================
    # Frame switching
    # ==================================================================

    _FRAME_MAP_ATTR = {
        "home": "_home_frame",
        "frame_2": "_second_frame",
        "settings": "_settings_frame",
    }

    def _select_frame(self, name: str) -> None:
        for key, btn in self._nav_buttons.items():
            colour = ("gray75", "gray25") if key == name else "transparent"
            btn.configure(fg_color=colour)

        for key, attr in self._FRAME_MAP_ATTR.items():
            frame = getattr(self, attr)
            if key == name:
                frame.grid(row=0, column=1, sticky="nsew")
            else:
                frame.grid_forget()

    # ==================================================================
    # Event handlers
    # ==================================================================

    @staticmethod
    def _on_appearance_change(mode: str) -> None:
        customtkinter.set_appearance_mode(mode)

    def _on_detect(self) -> None:
        logger.info("Detecting visible windows")
        window_names: list[str] = []
        Capture.list_window_names(window_names)
        self._combo.configure(values=window_names)
        if window_names:
            self._combo.set(window_names[0])

    def _on_window_selected(self, choice: str) -> None:
        logger.info("Window selected: %s", choice)
        if self._start_btn.cget("state") == "disabled":
            self._start_btn.configure(state="normal")
        self._window_name = choice

    def _on_start(self) -> None:
        if self._window_name is None:
            return

        # Tear down previous overlay if any
        if self._overlay is not None:
            self._overlay.win.destroy()

        self._overlay = Overlay()
        self._pipeline = TranslationPipeline(self._window_name)

        interval = self._config.capture_interval_ms
        self._overlay.win.after(interval, self._pipeline_tick)
        self._overlay.win.mainloop()

    def _pipeline_tick(self) -> None:
        """Run one pipeline cycle and schedule the next."""
        if self._overlay is None or self._pipeline is None:
            return

        self._overlay.clear_labels()
        self._pipeline.run_once(self._overlay.labeler)
        self._overlay.win.update()

        interval = self._config.capture_interval_ms
        self._overlay.win.after(interval, self._pipeline_tick)

    def _on_save_settings(self) -> None:
        self._config.client_id = self._entry_id.get()
        self._config.client_secret = self._entry_secret.get()
        logger.info("Settings saved")

    # ==================================================================
    # Shutdown
    # ==================================================================

    def on_closing(self) -> None:
        """Clean shutdown — destroy overlay then main window."""
        if self._overlay is not None:
            self._overlay.win.destroy()
        self.destroy()


# ======================================================================
# Entry point
# ======================================================================

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()