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
