# Backend Adapter Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor BRIDGE so translation backends and platform-specific capture/overlay code are selected through explicit interfaces instead of direct concrete imports.

**Architecture:** Use Strategy + Factory for translation backends and Adapter + Factory for platform capture/overlay backends. Keep the current Windows behavior as the only implemented platform in this phase, while moving Win32 details behind platform interfaces.

**Tech Stack:** Python 3.12+, standard library `unittest`, CustomTkinter, Pillow, OpenCV, NumPy, pytesseract, pywin32.

---

## File Structure

Create these files:

- `tests/test_translate_backends.py`: unit tests for translation result, dummy translator, disabled translator, Papago compatibility wrapper, and translator factory.
- `tests/test_config_and_cache.py`: unit tests for new config defaults and backend/language-separated CSV cache filenames.
- `tests/test_platform_factory.py`: unit tests for platform factory unsupported-platform behavior and Windows factory wiring.
- `tests/test_pipeline_adapters.py`: unit tests for injecting fake capture, OCR, translator, and cache into `TranslationPipeline`.
- `tests/test_main_backend_labels.py`: unit tests for Korean UI label to backend value mapping.
- `platforms/__init__.py`: platform package marker and public exports.
- `platforms/base.py`: OS-neutral dataclasses, protocols, and `PlatformNotSupportedError`.
- `platforms/factory.py`: creates the current OS capture and overlay adapters.
- `platforms/windows/__init__.py`: Windows platform package marker.
- `platforms/windows/capture.py`: Windows capture adapter wrapping the current Win32 capture behavior.
- `platforms/windows/overlay.py`: Windows overlay adapter wrapping the current Tkinter/Win32 overlay behavior.

Modify these files:

- `translate.py`: replace Papago-only API with translation result, translator protocol, concrete backends, and factory.
- `config.py`: add translation backend, local model path, and Papago enabled settings.
- `savecsv.py`: add backend/language-specific cache filenames and safe filename handling.
- `capture.py`: keep backward-compatible wrapper exporting `WindowsCaptureBackend` as `Capture`.
- `overlay.py`: keep backward-compatible wrapper exporting `WindowsOverlayBackend` as `Overlay`.
- `pipeline.py`: accept injectable adapters, use translator factory and platform capture factory, and emit `OverlayText`.
- `main.py`: use platform overlay factory, platform capture factory for window listing, and Korean translation backend labels in settings.

Do not modify existing `__pycache__`, `build`, or unrelated dirty files.

---

### Task 1: Translation Backend Interface And Factory

**Files:**
- Create: `tests/test_translate_backends.py`
- Modify: `translate.py`

- [ ] **Step 1: Write failing translation backend tests**

Create `tests/test_translate_backends.py`:

```python
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from translate import (
    DisabledTranslator,
    LocalDummyTranslator,
    PapagoTranslator,
    TranslatorPapago,
    create_translator,
)


class TranslationBackendTests(unittest.TestCase):
    def test_local_dummy_translator_prefixes_text(self):
        translator = LocalDummyTranslator()

        result = translator.translate("Hello", "en", "ko")

        self.assertTrue(result.success)
        self.assertEqual(result.backend, "local_dummy")
        self.assertEqual(result.text, "[테스트 번역] Hello")
        self.assertEqual(result.error, "")

    def test_disabled_translator_returns_original_text(self):
        translator = DisabledTranslator()

        result = translator.translate("Hello", "en", "ko")

        self.assertTrue(result.success)
        self.assertEqual(result.backend, "disabled")
        self.assertEqual(result.text, "Hello")

    def test_factory_creates_dummy_by_default(self):
        config = SimpleNamespace(translation_backend="local_dummy")

        translator = create_translator(config)

        self.assertIsInstance(translator, LocalDummyTranslator)

    def test_factory_creates_disabled_translator(self):
        config = SimpleNamespace(translation_backend="disabled")

        translator = create_translator(config)

        self.assertIsInstance(translator, DisabledTranslator)

    def test_factory_rejects_unknown_backend(self):
        config = SimpleNamespace(translation_backend="unknown")

        with self.assertRaises(ValueError) as ctx:
            create_translator(config)

        self.assertIn("Unsupported translation backend", str(ctx.exception))

    def test_papago_compatibility_alias_exists(self):
        self.assertIs(TranslatorPapago, PapagoTranslator)

    def test_papago_get_translate_returns_text_on_success_result(self):
        translator = PapagoTranslator(SimpleNamespace(client_id="id", client_secret="secret"))

        with patch.object(
            translator,
            "translate",
            return_value=SimpleNamespace(success=True, text="안녕하세요", error=""),
        ):
            self.assertEqual(translator.get_translate("Hello", "en", "ko"), "안녕하세요")

    def test_papago_get_translate_returns_none_on_failure_result(self):
        translator = PapagoTranslator(SimpleNamespace(client_id="id", client_secret="secret"))

        with patch.object(
            translator,
            "translate",
            return_value=SimpleNamespace(success=False, text="Hello", error="failed"),
        ):
            self.assertIsNone(translator.get_translate("Hello", "en", "ko"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m unittest tests.test_translate_backends -v
```

Expected: FAIL or ERROR because `DisabledTranslator`, `LocalDummyTranslator`, `PapagoTranslator`, or `create_translator` is not available with the required behavior.

- [ ] **Step 3: Replace `translate.py` with translation backend implementation**

Replace `translate.py` with:

```python
"""
Translation backends for BRIDGE.

This module exposes a small OS-neutral translation interface and keeps the
existing Papago implementation behind that interface.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Protocol
import urllib.parse
import urllib.request

from config import Config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranslationResult:
    """Result returned by every translation backend."""

    text: str
    success: bool
    backend: str
    error: str = ""


class Translator(Protocol):
    """Common interface implemented by all translation backends."""

    backend: str

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        """Translate text from source_lang to target_lang."""


class LocalDummyTranslator:
    """Local test translator used before a real local model is selected."""

    backend = "local_dummy"

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        del source_lang, target_lang
        return TranslationResult(
            text=f"[테스트 번역] {text}",
            success=True,
            backend=self.backend,
        )


class DisabledTranslator:
    """Translator that leaves recognized text unchanged."""

    backend = "disabled"

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        del source_lang, target_lang
        return TranslationResult(text=text, success=True, backend=self.backend)


class PapagoTranslator:
    """Translator that delegates to the Naver Papago NMT API."""

    backend = "papago"

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config()

    @property
    def client_id(self) -> str:
        return self._config.client_id

    @property
    def client_secret(self) -> str:
        return self._config.client_secret

    def set_client_id(self, client_id: str) -> None:
        self._config.client_id = client_id

    def set_client_secret(self, client_secret: str) -> None:
        self._config.client_secret = client_secret

    def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationResult:
        logger.info("Translating with Papago: %s (%s -> %s)", text, source_lang, target_lang)

        enc_text = urllib.parse.quote(text)
        data = f"source={source_lang}&target={target_lang}&text={enc_text}"
        url = "https://openapi.naver.com/v1/papago/n2mt"

        try:
            request = urllib.request.Request(url)
            request.add_header("X-Naver-Client-Id", self.client_id)
            request.add_header("X-Naver-Client-Secret", self.client_secret)
            response = urllib.request.urlopen(request, data=data.encode("utf-8"))
        except Exception as exc:
            error = f"Papago request failed: {exc}"
            logger.error(error)
            return TranslationResult(text=text, success=False, backend=self.backend, error=error)

        response_code = response.getcode()
        if response_code != 200:
            error = f"Papago returned status code {response_code}"
            logger.error(error)
            return TranslationResult(text=text, success=False, backend=self.backend, error=error)

        try:
            response_body = response.read()
            decoded = json.loads(response_body.decode("utf-8"))
            translated = decoded["message"]["result"]["translatedText"]
        except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            error = f"Papago response parse failed: {exc}"
            logger.error(error)
            return TranslationResult(text=text, success=False, backend=self.backend, error=error)

        return TranslationResult(text=translated, success=True, backend=self.backend)

    def get_translate(
        self,
        input_text: str,
        native_language: str | None = None,
        target_language: str | None = None,
    ) -> str | None:
        """Backward-compatible wrapper for the previous Papago API."""
        if native_language is None:
            native_language = self._config.translate_source_lang
        if target_language is None:
            target_language = self._config.translate_target_lang

        result = self.translate(input_text, native_language, target_language)
        if result.success:
            return result.text
        return None


TranslatorPapago = PapagoTranslator


def create_translator(config: Config | None = None) -> Translator:
    """Create the configured translation backend."""
    config = config or Config()
    backend = getattr(config, "translation_backend", "local_dummy")

    if backend == "local_dummy":
        return LocalDummyTranslator()
    if backend == "disabled":
        return DisabledTranslator()
    if backend == "papago":
        return PapagoTranslator(config)

    raise ValueError(f"Unsupported translation backend: {backend}")
```

- [ ] **Step 4: Run translation backend tests and verify they pass**

Run:

```powershell
python -m unittest tests.test_translate_backends -v
```

Expected: PASS.

- [ ] **Step 5: Commit translation backend interface**

Run:

```powershell
git add -- translate.py tests/test_translate_backends.py
git commit -m "feat: add translation backend interface"
```

---

### Task 2: Config Defaults And Cache Separation

**Files:**
- Create: `tests/test_config_and_cache.py`
- Modify: `config.py`
- Modify: `savecsv.py`

- [ ] **Step 1: Write failing config and cache tests**

Create `tests/test_config_and_cache.py`:

```python
import os
import tempfile
import unittest
from unittest.mock import patch

import config
from savecsv import SaveCsv, safe_filename_part


class ConfigAndCacheTests(unittest.TestCase):
    def test_default_config_contains_translation_backend_settings(self):
        self.assertEqual(config.DEFAULT_CONFIG["translation_backend"], "local_dummy")
        self.assertEqual(config.DEFAULT_CONFIG["local_model_path"], "")
        self.assertFalse(config.DEFAULT_CONFIG["papago_enabled"])

    def test_safe_filename_part_replaces_windows_invalid_characters(self):
        self.assertEqual(safe_filename_part('A:B/C\\D*E?F"G<H>I|J'), "A_B_C_D_E_F_G_H_I_J")

    def test_cache_filename_includes_backend_and_language_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("savecsv._CSV_DIR", tmp):
                cache = SaveCsv(
                    "Chrome: Demo",
                    backend="local_dummy",
                    source_lang="en",
                    target_lang="ko",
                )

                expected = os.path.join(tmp, "Chrome_ Demo.local_dummy.en-ko.csv")
                self.assertEqual(cache.file_path, expected)

    def test_cache_round_trip_uses_separated_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("savecsv._CSV_DIR", tmp):
                cache = SaveCsv(
                    "Chrome",
                    backend="local_dummy",
                    source_lang="en",
                    target_lang="ko",
                )

                cache.save_dictionary("Hello", "안녕하세요")

                self.assertEqual(cache.search("Hello"), "안녕하세요")
                self.assertFalse(cache.search("Missing"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m unittest tests.test_config_and_cache -v
```

Expected: FAIL or ERROR because config defaults and `safe_filename_part` do not exist yet.

- [ ] **Step 3: Add config defaults and properties**

In `config.py`, extend `DEFAULT_CONFIG`:

```python
DEFAULT_CONFIG = {
    "client_id": "",
    "client_secret": "",
    "tesseract_cmd": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    "ocr_languages": "eng+kor",
    "translate_source_lang": "en",
    "translate_target_lang": "ko",
    "translation_backend": "local_dummy",
    "local_model_path": "",
    "papago_enabled": False,
    "capture_interval_ms": 1000,
    "ocr_confidence_threshold": 70,
}
```

Add these properties to `Config` after `translate_target_lang`:

```python
    @property
    def translation_backend(self) -> str:
        return self.get("translation_backend", "local_dummy")

    @translation_backend.setter
    def translation_backend(self, value: str) -> None:
        self.set("translation_backend", value)

    @property
    def local_model_path(self) -> str:
        return self.get("local_model_path", "")

    @local_model_path.setter
    def local_model_path(self, value: str) -> None:
        self.set("local_model_path", value)

    @property
    def papago_enabled(self) -> bool:
        return bool(self.get("papago_enabled", False))

    @papago_enabled.setter
    def papago_enabled(self, value: bool) -> None:
        self.set("papago_enabled", bool(value))
```

- [ ] **Step 4: Replace `savecsv.py` with backend-aware cache implementation**

Replace `savecsv.py` with:

```python
"""
CSV-based translation cache.

Stores translated text in per-window, per-backend CSV files to avoid
redundant translation work and to prevent cache collisions across backends.
"""

from __future__ import annotations

import csv
import logging
import os

logger = logging.getLogger(__name__)

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CSV_DIR = os.path.join(_BASE_DIR, "CSV")
_INVALID_FILENAME_CHARS = '<>:"/\\|?*'


def safe_filename_part(value: str) -> str:
    """Return a filesystem-safe filename component."""
    cleaned = "".join("_" if char in _INVALID_FILENAME_CHARS else char for char in value)
    cleaned = cleaned.strip().rstrip(".")
    return cleaned or "window"


class SaveCsv:
    """Reads and writes a CSV translation cache for a window/backend/language pair."""

    def __init__(
        self,
        selected_window_name: str,
        backend: str = "papago",
        source_lang: str = "en",
        target_lang: str = "ko",
    ) -> None:
        window = safe_filename_part(selected_window_name)
        backend_name = safe_filename_part(backend)
        source = safe_filename_part(source_lang)
        target = safe_filename_part(target_lang)

        self._file_name = f"{window}.{backend_name}.{source}-{target}.csv"
        self._file_path = os.path.join(_CSV_DIR, self._file_name)

        os.makedirs(_CSV_DIR, exist_ok=True)

    @property
    def file_path(self) -> str:
        return self._file_path

    def save_dictionary(self, input_text: str, translated_text: str) -> None:
        """Append a translation pair to the CSV cache."""
        with open(self._file_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([input_text, translated_text])
        logger.debug("Cached: %s -> %s", input_text, translated_text)

    def search(self, input_text: str) -> str | bool:
        """Look up input_text in the cache."""
        if not os.path.isfile(self._file_path):
            return False

        with open(self._file_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            data = list(reader)

        for row in data:
            if row and row[0] == input_text:
                return row[1]

        return False
```

- [ ] **Step 5: Run config and cache tests and verify they pass**

Run:

```powershell
python -m unittest tests.test_config_and_cache -v
```

Expected: PASS.

- [ ] **Step 6: Run translation tests again**

Run:

```powershell
python -m unittest tests.test_translate_backends -v
```

Expected: PASS.

- [ ] **Step 7: Commit config and cache separation**

Run:

```powershell
git add -- config.py savecsv.py tests/test_config_and_cache.py
git commit -m "feat: separate translation cache by backend"
```

---

### Task 3: Platform Base Interfaces And Factory

**Files:**
- Create: `tests/test_platform_factory.py`
- Create: `platforms/__init__.py`
- Create: `platforms/base.py`
- Create: `platforms/factory.py`
- Create: `platforms/windows/__init__.py`

- [ ] **Step 1: Write failing platform factory tests**

Create `tests/test_platform_factory.py`:

```python
import unittest
from unittest.mock import patch

from platforms.base import PlatformNotSupportedError
from platforms.factory import create_capture_backend, create_overlay_backend


class PlatformFactoryTests(unittest.TestCase):
    def test_unsupported_capture_platform_raises_clear_error(self):
        with patch("sys.platform", "darwin"):
            with self.assertRaises(PlatformNotSupportedError) as ctx:
                create_capture_backend()

        self.assertIn("Unsupported platform", str(ctx.exception))

    def test_unsupported_overlay_platform_raises_clear_error(self):
        with patch("sys.platform", "linux"):
            with self.assertRaises(PlatformNotSupportedError) as ctx:
                create_overlay_backend()

        self.assertIn("Unsupported platform", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m unittest tests.test_platform_factory -v
```

Expected: FAIL or ERROR because the `platforms` package and factory do not exist.

- [ ] **Step 3: Create platform base interfaces**

Create `platforms/__init__.py`:

```python
"""Platform adapter package."""
```

Create `platforms/base.py`:

```python
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
```

Create `platforms/windows/__init__.py`:

```python
"""Windows platform adapters."""
```

- [ ] **Step 4: Create platform factory**

Create `platforms/factory.py`:

```python
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
```

- [ ] **Step 5: Run platform factory tests and verify remaining failure**

Run:

```powershell
python -m unittest tests.test_platform_factory -v
```

Expected: PASS.

- [ ] **Step 6: Commit platform base interfaces**

Run:

```powershell
git add -- platforms/__init__.py platforms/base.py platforms/factory.py platforms/windows/__init__.py tests/test_platform_factory.py
git commit -m "feat: add platform adapter interfaces"
```

---

### Task 4: Windows Capture And Overlay Adapters

**Files:**
- Create: `platforms/windows/capture.py`
- Create: `platforms/windows/overlay.py`
- Modify: `capture.py`
- Modify: `overlay.py`
- Modify: `tests/test_platform_factory.py`

- [ ] **Step 1: Extend platform tests for compatibility wrappers**

Append these tests to `PlatformFactoryTests` in `tests/test_platform_factory.py`:

```python
    def test_windows_capture_factory_returns_windows_backend(self):
        with patch("sys.platform", "win32"):
            backend = create_capture_backend()

        self.assertEqual(type(backend).__name__, "WindowsCaptureBackend")

    def test_capture_wrapper_exports_windows_backend(self):
        from capture import Capture
        from platforms.windows.capture import WindowsCaptureBackend

        self.assertIs(Capture, WindowsCaptureBackend)

    def test_overlay_wrapper_exports_windows_backend(self):
        from overlay import Overlay
        from platforms.windows.overlay import WindowsOverlayBackend

        self.assertIs(Overlay, WindowsOverlayBackend)
```

- [ ] **Step 2: Run platform tests and verify Windows adapter errors**

Run:

```powershell
python -m unittest tests.test_platform_factory -v
```

Expected: ERROR because `platforms.windows.capture` and `platforms.windows.overlay` do not exist.

- [ ] **Step 3: Create Windows capture adapter**

Create `platforms/windows/capture.py`:

```python
"""
Windows screen capture adapter using Win32 GDI APIs.
"""

from __future__ import annotations

import logging
import os
from typing import Sequence

import cv2
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

    def list_windows(self) -> list[WindowInfo]:
        """Return visible windows."""
        windows: list[WindowInfo] = []

        def _enum_handler(hwnd, _ctx):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append(WindowInfo(id=title, title=title))

        win32gui.EnumWindows(_enum_handler, None)
        return windows

    @staticmethod
    def list_window_names(target_list: list[str]) -> None:
        """Backward-compatible visible window title collector."""
        backend = WindowsCaptureBackend()
        target_list.extend(window.title for window in backend.list_windows())

    def select_window(self, window_id: str) -> None:
        """Select a visible window by title."""
        hwnd = win32gui.FindWindow(None, window_id)
        logger.info("Window handle for '%s': %s", window_id, hwnd)
        self._set_hwnd(hwnd, window_id)

    def get_screenshot(self) -> np.ndarray:
        """Return a BGR numpy array of the selected window content."""
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

        dc_obj.DeleteDC()
        c_dc.DeleteDC()
        win32gui.ReleaseDC(self._hwnd, w_dc)
        win32gui.DeleteObject(bitmap.GetHandle())

        img = img[..., :3]
        img = np.ascontiguousarray(img)

        screenshot_path = os.path.join(_BASE_DIR, "images", "img1.png")
        cv2.imwrite(screenshot_path, img)

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
```

- [ ] **Step 4: Create Windows overlay adapter**

Create `platforms/windows/overlay.py`:

```python
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
```

- [ ] **Step 5: Replace legacy modules with compatibility wrappers**

Replace `capture.py` with:

```python
"""
Backward-compatible capture module.

New code should import platform capture backends through platforms.factory.
"""

from platforms.windows.capture import WindowsCaptureBackend as Capture

__all__ = ["Capture"]
```

Replace `overlay.py` with:

```python
"""
Backward-compatible overlay module.

New code should import platform overlay backends through platforms.factory.
"""

from platforms.windows.overlay import WindowsOverlayBackend as Overlay

__all__ = ["Overlay"]
```

- [ ] **Step 6: Run platform factory tests and verify they pass**

Run:

```powershell
python -m unittest tests.test_platform_factory -v
```

Expected: PASS.

- [ ] **Step 7: Commit Windows platform adapters**

Run:

```powershell
git add -- capture.py overlay.py platforms/windows/capture.py platforms/windows/overlay.py tests/test_platform_factory.py
git commit -m "feat: add windows platform adapters"
```

---

### Task 5: Pipeline Dependency Injection And Adapter Use

**Files:**
- Create: `tests/test_pipeline_adapters.py`
- Modify: `pipeline.py`

- [ ] **Step 1: Write failing pipeline adapter test**

Create `tests/test_pipeline_adapters.py`:

```python
import unittest
from types import SimpleNamespace

import numpy as np

from platforms.base import CapturedFrame, OverlayText
from translate import TranslationResult
from pipeline import TranslationPipeline


class FakeCapture:
    def capture_frame(self):
        return CapturedFrame(
            image=np.zeros((10, 20, 3), dtype=np.uint8),
            screen_x=100,
            screen_y=200,
            width=20,
            height=10,
        )


class FakeOcr:
    def get_ocr_tesseract(self, screenshot):
        self.screenshot = screenshot
        return (
            {
                "text": ["Hello", ""],
                "conf": ["95", "-1"],
                "left": [5, 45],
                "top": [7, 7],
                "width": [30, 0],
                "height": [10, 10],
            },
            "Hello",
        )


class FakeTranslator:
    backend = "local_dummy"

    def __init__(self):
        self.calls = []

    def translate(self, text, source_lang, target_lang):
        self.calls.append((text, source_lang, target_lang))
        return TranslationResult(
            text=f"[테스트 번역] {text}",
            success=True,
            backend=self.backend,
        )


class FakeCache:
    def __init__(self):
        self.saved = []

    def search(self, text):
        return False

    def save_dictionary(self, source, translated):
        self.saved.append((source, translated))


class PipelineAdapterTests(unittest.TestCase):
    def test_pipeline_uses_injected_capture_translator_cache_and_overlay_text(self):
        config = SimpleNamespace(
            ocr_confidence_threshold=70,
            translate_source_lang="en",
            translate_target_lang="ko",
        )
        translator = FakeTranslator()
        cache = FakeCache()
        displayed = []

        pipeline = TranslationPipeline(
            "Demo",
            config=config,
            capture_backend=FakeCapture(),
            translator=translator,
            cache=cache,
            ocr=FakeOcr(),
        )

        pipeline.run_once(displayed.append)

        self.assertEqual(translator.calls, [("Hello", "en", "ko")])
        self.assertEqual(cache.saved, [("Hello", "[테스트 번역] Hello")])
        self.assertEqual(len(displayed), 1)
        self.assertIsInstance(displayed[0], OverlayText)
        self.assertEqual(displayed[0].text, "[테스트 번역] Hello")
        self.assertEqual(displayed[0].x, 105)
        self.assertEqual(displayed[0].y, 207)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m unittest tests.test_pipeline_adapters -v
```

Expected: FAIL or ERROR because `TranslationPipeline` does not accept injected dependencies and does not emit `OverlayText`.

- [ ] **Step 3: Update pipeline imports and constructor**

In `pipeline.py`, replace imports:

```python
import logging
from collections.abc import Callable

from config import Config
from ocr import Tesseract_Ocr
from platforms.base import CaptureBackend, OverlayText
from platforms.factory import create_capture_backend
from savecsv import SaveCsv
from translate import Translator, create_translator
```

Replace `TranslationPipeline.__init__` with:

```python
    def __init__(
        self,
        window_name: str,
        config: Config | None = None,
        capture_backend: CaptureBackend | None = None,
        translator: Translator | None = None,
        cache: SaveCsv | None = None,
        ocr: Tesseract_Ocr | None = None,
    ) -> None:
        self._config = config or Config()
        self._window_name = window_name
        self._capture = capture_backend or create_capture_backend(self._config, window_name)
        self._translator = translator or create_translator(self._config)
        self._ocr = ocr or Tesseract_Ocr()
        self._csv = cache or SaveCsv(
            window_name,
            backend=self._translator.backend,
            source_lang=self._config.translate_source_lang,
            target_lang=self._config.translate_target_lang,
        )
```

- [ ] **Step 4: Update `run_once` to use `CapturedFrame`, `Translator.translate`, and `OverlayText`**

In `pipeline.py`, change the `run_once` signature:

```python
    def run_once(self, display_callback: Callable[[OverlayText], None]) -> None:
```

Replace the capture lines:

```python
        frame = self._capture.capture_frame()
        screenshot = frame.image
        result, _ = self._ocr.get_ocr_tesseract(screenshot)
```

Replace translation handling inside the cache miss block:

```python
                        translation = self._translator.translate(
                            original, source_lang, target_lang
                        )
                        if translation.success:
                            self._csv.save_dictionary(original, translation.text)
                            final_result = translation.text
                        else:
                            logger.warning("Translation failed: %s", translation.error)
                            final_result = translation.text or original
```

Replace the `display_callback(...)` call:

```python
                    display_callback(
                        OverlayText(
                            text=final_result,
                            x=min_left + frame.screen_x,
                            y=min_top + frame.screen_y,
                            width=result["left"][i] - min_left + result["width"][i],
                            height=result["top"][i] - min_top + result["height"][i],
                            font_size=11,
                        )
                    )
```

- [ ] **Step 5: Run pipeline adapter test and verify it passes**

Run:

```powershell
python -m unittest tests.test_pipeline_adapters -v
```

Expected: PASS.

- [ ] **Step 6: Run previous test suites**

Run:

```powershell
python -m unittest tests.test_translate_backends tests.test_config_and_cache tests.test_platform_factory tests.test_pipeline_adapters -v
```

Expected: PASS.

- [ ] **Step 7: Commit pipeline adapter use**

Run:

```powershell
git add -- pipeline.py tests/test_pipeline_adapters.py
git commit -m "refactor: inject pipeline adapters"
```

---

### Task 6: Main UI Wiring For Platform And Translation Backends

**Files:**
- Create: `tests/test_main_backend_labels.py`
- Modify: `main.py`

- [ ] **Step 1: Write failing tests for backend label mapping**

Create `tests/test_main_backend_labels.py`:

```python
import unittest

import main


class MainBackendLabelTests(unittest.TestCase):
    def test_backend_labels_are_korean_and_map_to_config_values(self):
        self.assertEqual(main.BACKEND_LABEL_TO_VALUE["테스트 번역기"], "local_dummy")
        self.assertEqual(main.BACKEND_LABEL_TO_VALUE["Papago API"], "papago")
        self.assertEqual(main.BACKEND_LABEL_TO_VALUE["번역 비활성화"], "disabled")

    def test_backend_value_to_label_round_trip(self):
        for label, value in main.BACKEND_LABEL_TO_VALUE.items():
            self.assertEqual(main.BACKEND_VALUE_TO_LABEL[value], label)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m unittest tests.test_main_backend_labels -v
```

Expected: FAIL or ERROR because backend label constants do not exist.

- [ ] **Step 3: Update `main.py` imports and backend constants**

In `main.py`, replace:

```python
from capture import Capture
from overlay import Overlay
from pipeline import TranslationPipeline
```

with:

```python
from pipeline import TranslationPipeline
from platforms.base import OverlayBackend
from platforms.factory import create_capture_backend, create_overlay_backend
```

Add after `_IMAGE_DIR`:

```python
BACKEND_LABEL_TO_VALUE = {
    "테스트 번역기": "local_dummy",
    "Papago API": "papago",
    "번역 비활성화": "disabled",
}
BACKEND_VALUE_TO_LABEL = {value: label for label, value in BACKEND_LABEL_TO_VALUE.items()}
```

In `App.__init__`, change overlay type:

```python
        self._overlay: OverlayBackend | None = None
```

- [ ] **Step 4: Add translation backend selector to settings UI**

In `_build_settings_frame`, insert this block before the Client ID label:

```python
        customtkinter.CTkLabel(self._settings_frame, text="번역 방식:").grid(
            row=0, column=0, padx=20, pady=10,
        )
        selected_backend = BACKEND_VALUE_TO_LABEL.get(
            self._config.translation_backend,
            "테스트 번역기",
        )
        self._backend_menu = customtkinter.CTkOptionMenu(
            self._settings_frame,
            values=list(BACKEND_LABEL_TO_VALUE.keys()),
        )
        self._backend_menu.grid(row=1, column=0, padx=20, pady=10)
        self._backend_menu.set(selected_backend)
```

Then shift the existing Client ID/Secret widgets down so their rows become:

```python
Client ID label: row=2
Client ID entry: row=3
Client Secret label: row=4
Client Secret entry: row=5
Save button: row=6
```

- [ ] **Step 5: Update window detection to use capture factory**

Replace `_on_detect` with:

```python
    def _on_detect(self) -> None:
        logger.info("Detecting visible windows")
        capture_backend = create_capture_backend(self._config)
        window_names = [window.title for window in capture_backend.list_windows()]
        self._combo.configure(values=window_names)
        if window_names:
            self._combo.set(window_names[0])
            self._on_window_selected(window_names[0])
```

- [ ] **Step 6: Update overlay lifecycle to use overlay backend interface**

In `_on_start`, replace the overlay teardown and creation block with:

```python
        if self._overlay is not None:
            self._overlay.destroy()

        self._overlay = create_overlay_backend(self._config)
        self._pipeline = TranslationPipeline(self._window_name)

        interval = self._config.capture_interval_ms
        self._overlay.after(interval, self._pipeline_tick)
        self._overlay.run()
```

In `_pipeline_tick`, replace overlay calls:

```python
        self._overlay.clear()
        self._pipeline.run_once(self._overlay.show_text)
        self._overlay.update()

        interval = self._config.capture_interval_ms
        self._overlay.after(interval, self._pipeline_tick)
```

In `on_closing`, replace:

```python
            self._overlay.win.destroy()
```

with:

```python
            self._overlay.destroy()
```

- [ ] **Step 7: Save backend selection in settings**

Replace `_on_save_settings` with:

```python
    def _on_save_settings(self) -> None:
        backend_label = self._backend_menu.get()
        self._config.translation_backend = BACKEND_LABEL_TO_VALUE[backend_label]
        self._config.client_id = self._entry_id.get()
        self._config.client_secret = self._entry_secret.get()
        self._config.papago_enabled = self._config.translation_backend == "papago"
        logger.info("Settings saved")
```

- [ ] **Step 8: Run main label tests**

Run:

```powershell
python -m unittest tests.test_main_backend_labels -v
```

Expected: PASS.

- [ ] **Step 9: Run all unit tests**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 10: Commit main UI wiring**

Run:

```powershell
git add -- main.py tests/test_main_backend_labels.py
git commit -m "feat: wire backend selection UI"
```

---

### Task 7: Verification And Cleanup

**Files:**
- Modify only if verification exposes a concrete defect from earlier tasks.

- [ ] **Step 1: Run full unittest suite**

Run:

```powershell
python -m unittest discover -s tests -v
```

Expected: PASS.

- [ ] **Step 2: Run Python compilation check**

Run:

```powershell
python -m compileall -q .
```

Expected: exit code 0.

- [ ] **Step 3: Verify direct imports do not use concrete Win32 modules outside adapters**

Run:

```powershell
Select-String -Path *.py,platforms\\*.py,platforms\\windows\\*.py -Pattern "import win32|from win32|import pywintypes|from pywintypes"
```

Expected: matches only in `platforms/windows/capture.py` and `platforms/windows/overlay.py`.

- [ ] **Step 4: Verify pipeline and main do not import legacy wrappers**

Run:

```powershell
Select-String -Path main.py,pipeline.py -Pattern "from capture import|from overlay import|TranslatorPapago"
```

Expected: no matches.

- [ ] **Step 5: Check git status for unrelated dirty files**

Run:

```powershell
git status --short
```

Expected: only files intentionally changed by the implementation tasks are modified or staged. Existing unrelated `__pycache__` and pre-existing `savecsv.py` dirty state should not be reverted unless the task changed `savecsv.py` intentionally.

- [ ] **Step 6: Commit verification fixes if any were required**

If Step 1-4 required code fixes, run:

```powershell
git add -- main.py pipeline.py translate.py config.py savecsv.py capture.py overlay.py platforms tests
git commit -m "fix: complete backend adapter verification"
```

Expected: commit created only when code was changed during verification. If no files changed, skip this commit.
