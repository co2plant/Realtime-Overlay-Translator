import unittest
from unittest.mock import patch

from platforms.base import PlatformNotSupportedError
from platforms.factory import create_capture_backend, create_overlay_backend


class PlatformFactoryTests(unittest.TestCase):
    def test_unsupported_capture_platform_raises_clear_error(self):
        with patch("sys.platform", "darwin"):
            with self.assertRaises(PlatformNotSupportedError) as ctx:
                create_capture_backend()

        self.assertIn("Unsupported platform", str(ctx.exception))

    def test_unsupported_overlay_platform_raises_clear_error(self):
        with patch("sys.platform", "linux"):
            with self.assertRaises(PlatformNotSupportedError) as ctx:
                create_overlay_backend()

        self.assertIn("Unsupported platform", str(ctx.exception))

    def test_windows_capture_factory_returns_windows_backend(self):
        with patch("sys.platform", "win32"):
            backend = create_capture_backend()

        self.assertEqual(type(backend).__name__, "WindowsCaptureBackend")

    def test_capture_wrapper_exports_windows_backend(self):
        from capture import Capture
        from platforms.windows.capture import WindowsCaptureBackend

        self.assertIs(Capture, WindowsCaptureBackend)

    def test_overlay_wrapper_exports_windows_backend(self):
        from overlay import Overlay
        from platforms.windows.overlay import WindowsOverlayBackend

        self.assertIs(Overlay, WindowsOverlayBackend)


if __name__ == "__main__":
    unittest.main()
