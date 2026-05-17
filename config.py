"""
Configuration manager for the Realtime-Overlay-Translator application.
Handles loading and saving settings to a JSON file.
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

# Resolve the base directory relative to this file, not the working directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

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


class Config:
    """Singleton configuration manager that persists settings to config.json."""

    _instance: "Config | None" = None
    _data: dict

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = {}
            cls._instance._load()
        return cls._instance

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load configuration from disk, falling back to defaults."""
        if os.path.isfile(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.info("Configuration loaded from %s", CONFIG_FILE)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to read config file, using defaults: %s", exc)
                self._data = dict(DEFAULT_CONFIG)
        else:
            self._data = dict(DEFAULT_CONFIG)
            self._save()  # create the file with defaults on first run

    def _save(self) -> None:
        """Write current configuration to disk."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
            logger.info("Configuration saved to %s", CONFIG_FILE)
        except OSError as exc:
            logger.error("Failed to save config file: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str, default=None):
        """Get a configuration value."""
        return self._data.get(key, DEFAULT_CONFIG.get(key, default))

    def set(self, key: str, value) -> None:
        """Set a configuration value and persist to disk."""
        self._data[key] = value
        self._save()

    def update(self, mapping: dict) -> None:
        """Bulk-update configuration values and persist to disk."""
        self._data.update(mapping)
        self._save()

    # -- convenience properties ----------------------------------------

    @property
    def client_id(self) -> str:
        return self.get("client_id", "")

    @client_id.setter
    def client_id(self, value: str) -> None:
        self.set("client_id", value)

    @property
    def client_secret(self) -> str:
        return self.get("client_secret", "")

    @client_secret.setter
    def client_secret(self, value: str) -> None:
        self.set("client_secret", value)

    @property
    def tesseract_cmd(self) -> str:
        return self.get("tesseract_cmd", "")

    @property
    def ocr_languages(self) -> str:
        return self.get("ocr_languages", "eng+kor")

    @property
    def translate_source_lang(self) -> str:
        return self.get("translate_source_lang", "en")

    @property
    def translate_target_lang(self) -> str:
        return self.get("translate_target_lang", "ko")

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

    @property
    def capture_interval_ms(self) -> int:
        return self.get("capture_interval_ms", 1000)

    @property
    def ocr_confidence_threshold(self) -> int:
        return self.get("ocr_confidence_threshold", 70)
