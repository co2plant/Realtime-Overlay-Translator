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
