import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from platforms.base import CapturedFrame, OverlayText
from translate import TranslationResult
from pipeline import TranslationPipeline


TRANSLATION_PREFIX = "[테스트 번역]"


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
    def __init__(self, result=None, text="Hello"):
        self._result = result or {
            "text": ["Hello", ""],
            "conf": ["95", "-1"],
            "left": [5, 45],
            "top": [7, 7],
            "width": [30, 0],
            "height": [10, 10],
        }
        self._text = text

    def get_ocr_tesseract(self, screenshot):
        self.screenshot = screenshot
        return self._result, self._text


class FakeTranslator:
    backend = "local_dummy"

    def __init__(self):
        self.calls = []

    def translate(self, text, source_lang, target_lang):
        self.calls.append((text, source_lang, target_lang))
        return TranslationResult(
            text=f"{TRANSLATION_PREFIX} {text}",
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


def config():
    return SimpleNamespace(
        ocr_confidence_threshold=70,
        translate_source_lang="en",
        translate_target_lang="ko",
    )


class PipelineAdapterTests(unittest.TestCase):
    def test_pipeline_uses_injected_capture_translator_cache_and_overlay_text(self):
        translator = FakeTranslator()
        cache = FakeCache()
        displayed = []

        pipeline = TranslationPipeline(
            "Demo",
            config=config(),
            capture_backend=FakeCapture(),
            translator=translator,
            cache=cache,
            ocr=FakeOcr(),
        )

        pipeline.run_once(displayed.append)

        self.assertEqual(translator.calls, [("Hello", "en", "ko")])
        self.assertEqual(cache.saved, [("Hello", f"{TRANSLATION_PREFIX} Hello")])
        self.assertEqual(len(displayed), 1)
        self.assertIsInstance(displayed[0], OverlayText)
        self.assertEqual(displayed[0].text, f"{TRANSLATION_PREFIX} Hello")
        self.assertEqual(displayed[0].x, 105)
        self.assertEqual(displayed[0].y, 207)
        self.assertEqual(displayed[0].width, 40)
        self.assertEqual(displayed[0].height, 10)
        self.assertEqual(displayed[0].font_size, 11)

    def test_pipeline_supports_legacy_six_argument_display_callback(self):
        displayed = []

        def legacy_callback(text, x, y, width, height, font_size):
            displayed.append((text, x, y, width, height, font_size))

        pipeline = TranslationPipeline(
            "Demo",
            config=config(),
            capture_backend=FakeCapture(),
            translator=FakeTranslator(),
            cache=FakeCache(),
            ocr=FakeOcr(),
        )

        pipeline.run_once(legacy_callback)

        self.assertEqual(
            displayed,
            [(f"{TRANSLATION_PREFIX} Hello", 105, 207, 40, 10, 11)],
        )

    def test_pipeline_starts_new_phrase_with_boundary_word(self):
        result = {
            "text": ["Hello", "World", ""],
            "conf": ["95", "96", "-1"],
            "left": [5, 100, 130],
            "top": [7, 7, 7],
            "width": [30, 25, 0],
            "height": [10, 10, 10],
        }
        translator = FakeTranslator()
        displayed = []
        pipeline = TranslationPipeline(
            "Demo",
            config=config(),
            capture_backend=FakeCapture(),
            translator=translator,
            cache=FakeCache(),
            ocr=FakeOcr(result=result, text="Hello World"),
        )

        pipeline.run_once(displayed.append)

        self.assertEqual(
            translator.calls,
            [("Hello", "en", "ko"), ("World", "en", "ko")],
        )
        self.assertEqual(
            [item.text for item in displayed],
            [f"{TRANSLATION_PREFIX} Hello", f"{TRANSLATION_PREFIX} World"],
        )

    def test_default_construction_uses_adapter_factories_and_backend_cache(self):
        cfg = config()
        capture = FakeCapture()
        translator = FakeTranslator()
        cache = Mock()
        ocr = Mock()

        with (
            patch("pipeline.create_capture_backend", return_value=capture) as create_capture,
            patch("pipeline.create_translator", return_value=translator) as create_translator,
            patch("pipeline.SaveCsv", return_value=cache) as save_csv,
            patch("pipeline.Tesseract_Ocr", return_value=ocr) as tesseract_ocr,
        ):
            pipeline = TranslationPipeline("Demo", config=cfg)

        create_capture.assert_called_once_with(cfg, "Demo")
        create_translator.assert_called_once_with(cfg)
        save_csv.assert_called_once_with(
            "Demo",
            backend=translator.backend,
            source_lang="en",
            target_lang="ko",
        )
        tesseract_ocr.assert_called_once_with()
        self.assertIs(pipeline._capture, capture)
        self.assertIs(pipeline._translator, translator)
        self.assertIs(pipeline._csv, cache)
        self.assertIs(pipeline._ocr, ocr)


if __name__ == "__main__":
    unittest.main()
