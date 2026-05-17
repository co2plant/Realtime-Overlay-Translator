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


if __name__ == "__main__":
    unittest.main()
