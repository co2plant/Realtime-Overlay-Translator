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
