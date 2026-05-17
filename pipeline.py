"""
Translation pipeline – orchestrates capture → OCR → translate → overlay.

This module encapsulates the business logic that was previously inside
the global ``while_loop()`` function in *main.py*, making it testable
and independent of the GUI layer.
"""

import logging
from collections.abc import Callable

from config import Config
from ocr import Tesseract_Ocr
from platforms.base import CaptureBackend, OverlayText
from platforms.factory import create_capture_backend
from savecsv import SaveCsv
from translate import Translator, create_translator

logger = logging.getLogger(__name__)

# Upper bound used when no position has been determined yet.
_POSITION_SENTINEL = 10_000


class TranslationPipeline:
    """Runs one capture→OCR→translate→overlay cycle and schedules the next."""

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self, display_callback: Callable[[OverlayText], None]) -> None:
        """Execute a single pipeline cycle.

        Parameters
        ----------
        display_callback:
            ``display_callback(text, x, y, width, height, font_size)``
            — called for every translated text block that should be rendered.
        """
        logger.debug("Pipeline cycle start")

        frame = self._capture.capture_frame()
        screenshot = frame.image
        result, _ = self._ocr.get_ocr_tesseract(screenshot)

        detected_words: list[str] = []
        min_left = _POSITION_SENTINEL
        min_top = _POSITION_SENTINEL
        confidence_threshold = self._config.ocr_confidence_threshold
        source_lang = self._config.translate_source_lang
        target_lang = self._config.translate_target_lang

        total = len(result["text"])
        for i in range(total):
            text = result["text"][i]
            conf = int(result["conf"][i])

            # Detect sentence boundaries: large horizontal/vertical gap or end of data
            is_boundary = False
            if i > 0:
                prev_right = result["left"][i - 1] + result["width"][i - 1] + result["height"][i - 1]
                prev_bottom = result["top"][i - 1] + result["height"][i - 1] * 1.2
                if prev_right < result["left"][i] or prev_bottom < result["top"][i]:
                    is_boundary = True

            if not is_boundary and conf > confidence_threshold:
                # Keep only ASCII characters (strip non-ASCII)
                clean = "".join(c if ord(c) < 128 else "" for c in text).strip()
                if result["left"][i] < min_left:
                    min_left = result["left"][i]
                if result["top"][i] < min_top:
                    min_top = result["top"][i]
                detected_words.append(clean)

            if is_boundary or i == total - 1:
                final_result = " ".join(detected_words)
                detected_words.clear()

                if not final_result or len(final_result) <= 1 or final_result.isspace():
                    continue

                # Look up cache first, translate on miss
                cached = self._csv.search(final_result)
                if cached is False:
                    original = final_result
                    if len(original) > 1:
                        translation = self._translator.translate(
                            original, source_lang, target_lang
                        )
                        if translation.success:
                            self._csv.save_dictionary(original, translation.text)
                            final_result = translation.text
                        else:
                            logger.warning("Translation failed: %s", translation.error)
                            final_result = translation.text or original
                else:
                    final_result = cached

                if len(final_result) >= 1:
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

                min_left = _POSITION_SENTINEL
                min_top = _POSITION_SENTINEL

        logger.debug("Pipeline cycle complete")
