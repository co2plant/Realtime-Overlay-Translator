"""
Translation module using Naver Papago API.
"""

import urllib.request
import urllib.parse
import json
import logging

from config import Config

logger = logging.getLogger(__name__)


class TranslatorPapago:
    """Translator that delegates to the Naver Papago NMT API."""

    def __init__(self) -> None:
        self._config = Config()

    # -- credential access (backed by Config singleton) ----------------

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

    # -- translation ---------------------------------------------------

    def get_translate(
        self,
        input_text: str,
        native_language: str | None = None,
        target_language: str | None = None,
    ) -> str | None:
        """Translate *input_text* from *native_language* to *target_language*.

        Returns the translated string on success, or ``None`` on failure.
        """
        if native_language is None:
            native_language = self._config.translate_source_lang
        if target_language is None:
            target_language = self._config.translate_target_lang

        logger.info("Translating: %s (%s → %s)", input_text, native_language, target_language)

        enc_text = urllib.parse.quote(input_text)
        data = f"source={native_language}&target={target_language}&text={enc_text}"
        url = "https://openapi.naver.com/v1/papago/n2mt"

        try:
            request = urllib.request.Request(url)
            request.add_header("X-Naver-Client-Id", self.client_id)
            request.add_header("X-Naver-Client-Secret", self.client_secret)
            response = urllib.request.urlopen(request, data=data.encode("utf-8"))
        except Exception as exc:
            logger.error("Translation request failed: %s", exc)
            return None

        response_code = response.getcode()
        if response_code == 200:
            response_body = response.read()
            decoded = json.loads(response_body.decode("utf-8"))
            result = decoded["message"]["result"]["translatedText"]
            return result
        else:
            logger.error("Translation API returned error code: %s", response_code)
            return None