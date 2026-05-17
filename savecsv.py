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
            if len(row) >= 2 and row[0] == input_text:
                return row[1]

        return False
