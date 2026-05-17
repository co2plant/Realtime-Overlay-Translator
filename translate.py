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
        ...


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
        except (KeyError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
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
