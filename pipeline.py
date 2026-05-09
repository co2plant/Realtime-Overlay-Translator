"""
Translation pipeline – orchestrates capture → OCR → translate → overlay.

This module encapsulates the business logic that was previously inside
the global ``while_loop()`` function in *main.py*, making it testable
and independent of the GUI layer.
"""

import logging
from typing import Callable

from capture import Capture
from ocr import Tesseract_Ocr
from translate import TranslatorPapago
from savecsv import SaveCsv
from config import Config

logger = logging.getLogger(__name__)

# Upper bound used when no position has been determined yet.
_POSITION_SENTINEL = 10_000


class TranslationPipeline:
    """Runs one capture→OCR→translate→overlay cycle and schedules the next."""

    def __init__(self, window_name: str) -> None:
        self._config = Config()
        self._window_name = window_name
        self._capture = Capture(window_name)
        self._csv = SaveCsv(window_name)
        self._translator = TranslatorPapago()
        self._ocr = Tesseract_Ocr()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self, display_callback: Callable) -> None:
        """Execute a single pipeline cycle.

        Parameters
        ----------
        display_callback:
            ``display_callback(text, x, y, width, height, font_size)``
            — called for every translated text block that should be rendered.
        """
        logger.debug("Pipeline cycle start")

        arr = self._capture.get_rect()
        screenshot = self._capture.get_screenshot()
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
                        translated = self._translator.get_translate(
                            original, source_lang, target_lang
                        )
                        if translated:
                            self._csv.save_dictionary(original, translated)
                            final_result = translated
                else:
                    final_result = cached

                if len(final_result) >= 1:
                    display_callback(
                        final_result,
                        min_left + arr[0],
                        min_top + arr[1],
                        result["left"][i] - min_left + result["width"][i],
                        result["top"][i] - min_top + result["height"][i],
                        11,
                    )

                min_left = _POSITION_SENTINEL
                min_top = _POSITION_SENTINEL

            elif conf > confidence_threshold:
                # Keep only ASCII characters (strip non-ASCII)
                clean = "".join(c if ord(c) < 128 else "" for c in text).strip()
                if result["left"][i] < min_left:
                    min_left = result["left"][i]
                if result["top"][i] < min_top:
                    min_top = result["top"][i]
                detected_words.append(clean)

        logger.debug("Pipeline cycle complete")
