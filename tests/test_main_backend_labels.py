import unittest
from unittest.mock import patch

import main
from platforms.base import WindowInfo


DUMMY_LABEL = "\ud14c\uc2a4\ud2b8 \ubc88\uc5ed\uae30"
DISABLED_LABEL = "\ubc88\uc5ed \ube44\ud65c\uc131\ud654"


class FakeCombo:
    def __init__(self):
        self.values = None
        self.selected = None

    def configure(self, **kwargs):
        self.values = kwargs["values"]

    def set(self, value):
        self.selected = value


class FakeButton:
    def __init__(self):
        self.state = "disabled"

    def cget(self, name):
        if name == "state":
            return self.state
        raise KeyError(name)

    def configure(self, **kwargs):
        self.state = kwargs["state"]


class FakeCaptureBackend:
    def list_windows(self):
        return [WindowInfo(id="opaque-id", title="Display Title")]


class FakeDuplicateTitleCaptureBackend:
    def list_windows(self):
        return [
            WindowInfo(id="a", title="Chrome"),
            WindowInfo(id="b", title="Chrome"),
        ]


class FakeGeneratedLabelCollisionCaptureBackend:
    def list_windows(self):
        return [
            WindowInfo(id="a", title="Chrome"),
            WindowInfo(id="b", title="Chrome (2)"),
            WindowInfo(id="c", title="Chrome"),
        ]


class FakeEntry:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeBackendMenu:
    def get(self):
        return "Papago API"


class FakeConfig:
    def __init__(self):
        self.capture_interval_ms = 1000
        self.translation_backend = "local_dummy"
        self.client_id = ""
        self.client_secret = ""
        self.papago_enabled = False

    def update(self, mapping):
        for key, value in mapping.items():
            setattr(self, key, value)


class FakeOverlay:
    def __init__(self):
        self.calls = []
        self.after_delay = None
        self.after_callback = None

    def clear(self):
        self.calls.append("clear")

    def show_text(self, item):
        self.calls.append(("show_text", item))

    def update(self):
        self.calls.append("update")

    def after(self, delay_ms, callback):
        self.after_delay = delay_ms
        self.after_callback = callback


class FakePipeline:
    def __init__(self):
        self.callback = None

    def run_once(self, callback):
        self.callback = callback


class MainBackendLabelTests(unittest.TestCase):
    def test_backend_labels_are_korean_and_map_to_config_values(self):
        self.assertEqual(main.BACKEND_LABEL_TO_VALUE[DUMMY_LABEL], "local_dummy")
        self.assertEqual(main.BACKEND_LABEL_TO_VALUE["Papago API"], "papago")
        self.assertEqual(main.BACKEND_LABEL_TO_VALUE[DISABLED_LABEL], "disabled")

    def test_backend_value_to_label_round_trip(self):
        for label, value in main.BACKEND_LABEL_TO_VALUE.items():
            self.assertEqual(main.BACKEND_VALUE_TO_LABEL[value], label)

    def test_on_detect_displays_titles_but_stores_selected_window_id(self):
        app = main.App.__new__(main.App)
        app._config = FakeConfig()
        app._combo = FakeCombo()
        app._start_btn = FakeButton()

        with patch.object(main, "create_capture_backend", return_value=FakeCaptureBackend()):
            app._on_detect()

        self.assertEqual(app._combo.values, ["Display Title"])
        self.assertEqual(app._combo.selected, "Display Title")
        self.assertEqual(app._window_name, "opaque-id")

    def test_on_detect_disambiguates_duplicate_titles(self):
        app = main.App.__new__(main.App)
        app._config = FakeConfig()
        app._combo = FakeCombo()
        app._start_btn = FakeButton()

        with patch.object(
            main,
            "create_capture_backend",
            return_value=FakeDuplicateTitleCaptureBackend(),
        ):
            app._on_detect()

        self.assertEqual(app._combo.values, ["Chrome", "Chrome (2)"])
        self.assertEqual(app._window_title_to_id["Chrome"], "a")
        self.assertEqual(app._window_title_to_id["Chrome (2)"], "b")
        self.assertEqual(app._window_name, "a")

        app._on_window_selected("Chrome (2)")

        self.assertEqual(app._window_name, "b")

    def test_on_detect_avoids_collision_with_existing_generated_label(self):
        app = main.App.__new__(main.App)
        app._config = FakeConfig()
        app._combo = FakeCombo()
        app._start_btn = FakeButton()

        with patch.object(
            main,
            "create_capture_backend",
            return_value=FakeGeneratedLabelCollisionCaptureBackend(),
        ):
            app._on_detect()

        self.assertEqual(app._combo.values, ["Chrome", "Chrome (2)", "Chrome (3)"])
        self.assertEqual(app._window_title_to_id["Chrome"], "a")
        self.assertEqual(app._window_title_to_id["Chrome (2)"], "b")
        self.assertEqual(app._window_title_to_id["Chrome (3)"], "c")

        app._on_window_selected("Chrome (3)")

        self.assertEqual(app._window_name, "c")

    def test_on_save_settings_stores_backend_credentials_and_papago_enabled(self):
        app = main.App.__new__(main.App)
        app._config = FakeConfig()
        app._backend_menu = FakeBackendMenu()
        app._entry_id = FakeEntry("client-id")
        app._entry_secret = FakeEntry("client-secret")

        app._on_save_settings()

        self.assertEqual(app._config.translation_backend, "papago")
        self.assertEqual(app._config.client_id, "client-id")
        self.assertEqual(app._config.client_secret, "client-secret")
        self.assertIs(app._config.papago_enabled, True)

    def test_pipeline_tick_passes_overlay_show_text_to_pipeline(self):
        app = main.App.__new__(main.App)
        app._config = FakeConfig()
        app._overlay = FakeOverlay()
        app._pipeline = FakePipeline()

        app._pipeline_tick()

        self.assertEqual(app._overlay.calls, ["clear", "update"])
        self.assertEqual(app._pipeline.callback, app._overlay.show_text)
        self.assertEqual(app._overlay.after_delay, 1000)
        self.assertEqual(app._overlay.after_callback, app._pipeline_tick)


if __name__ == "__main__":
    unittest.main()
