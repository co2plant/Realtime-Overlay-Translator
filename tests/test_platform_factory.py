import sys
import unittest
from unittest.mock import Mock, patch

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
        class FakeWindowsCaptureBackend:
            def __init__(self, window_id=None):
                self.window_id = window_id

        with (
            patch("sys.platform", "win32"),
            patch(
                "platforms.windows.capture.WindowsCaptureBackend",
                FakeWindowsCaptureBackend,
            ),
        ):
            backend = create_capture_backend()

        self.assertIsInstance(backend, FakeWindowsCaptureBackend)

    def test_windows_overlay_factory_returns_windows_backend(self):
        class FakeWindowsOverlayBackend:
            pass

        with (
            patch("sys.platform", "win32"),
            patch(
                "platforms.windows.overlay.WindowsOverlayBackend",
                FakeWindowsOverlayBackend,
            ),
        ):
            backend = create_overlay_backend()

        self.assertIsInstance(backend, FakeWindowsOverlayBackend)

    def test_windows_capture_screenshot_releases_gdi_resources_on_error(self):
        from platforms.windows import capture as windows_capture
        from platforms.windows.capture import WindowsCaptureBackend

        backend = WindowsCaptureBackend.__new__(WindowsCaptureBackend)
        backend._hwnd = 10
        backend._width = 2
        backend._height = 2
        backend._cropped_x = 0
        backend._cropped_y = 0

        dc_obj = Mock()
        compatible_dc = Mock()
        bitmap = Mock()
        dc_obj.CreateCompatibleDC.return_value = compatible_dc
        bitmap.GetBitmapBits.side_effect = RuntimeError("bitmap read failed")
        bitmap.GetHandle.return_value = 20

        with (
            patch.dict(sys.modules, {"cv2": Mock()}),
            patch.object(windows_capture.win32gui, "GetWindowDC", return_value=30),
            patch.object(windows_capture.win32ui, "CreateDCFromHandle", return_value=dc_obj),
            patch.object(windows_capture.win32ui, "CreateBitmap", return_value=bitmap),
            patch.object(windows_capture.win32gui, "ReleaseDC") as release_dc,
            patch.object(windows_capture.win32gui, "DeleteObject") as delete_object,
        ):
            with self.assertRaisesRegex(RuntimeError, "bitmap read failed"):
                backend.get_screenshot()

        dc_obj.DeleteDC.assert_called_once_with()
        compatible_dc.DeleteDC.assert_called_once_with()
        release_dc.assert_called_once_with(10, 30)
        delete_object.assert_called_once_with(20)

    def test_windows_capture_cleanup_failure_does_not_mask_capture_error(self):
        from platforms.windows import capture as windows_capture
        from platforms.windows.capture import WindowsCaptureBackend

        backend = WindowsCaptureBackend.__new__(WindowsCaptureBackend)
        backend._hwnd = 10
        backend._width = 2
        backend._height = 2
        backend._cropped_x = 0
        backend._cropped_y = 0

        dc_obj = Mock()
        compatible_dc = Mock()
        bitmap = Mock()
        dc_obj.CreateCompatibleDC.return_value = compatible_dc
        bitmap.GetBitmapBits.side_effect = RuntimeError("bitmap read failed")
        bitmap.GetHandle.return_value = 20
        compatible_dc.DeleteDC.side_effect = RuntimeError("cleanup failed")

        with (
            patch.dict(sys.modules, {"cv2": Mock()}),
            patch.object(windows_capture.win32gui, "GetWindowDC", return_value=30),
            patch.object(windows_capture.win32ui, "CreateDCFromHandle", return_value=dc_obj),
            patch.object(windows_capture.win32ui, "CreateBitmap", return_value=bitmap),
            patch.object(windows_capture.win32gui, "ReleaseDC") as release_dc,
            patch.object(windows_capture.win32gui, "DeleteObject") as delete_object,
            patch.object(windows_capture.logger, "warning") as warning,
        ):
            with self.assertRaisesRegex(RuntimeError, "bitmap read failed"):
                backend.get_screenshot()

        compatible_dc.DeleteDC.assert_called_once_with()
        dc_obj.DeleteDC.assert_called_once_with()
        release_dc.assert_called_once_with(10, 30)
        delete_object.assert_called_once_with(20)
        warning.assert_called_once()

    def test_windows_capture_list_window_names_does_not_construct_backend(self):
        from platforms.windows import capture as windows_capture
        from platforms.windows.capture import WindowsCaptureBackend

        def enum_windows(callback, ctx):
            callback(1, ctx)
            callback(2, ctx)

        names = []

        with (
            patch.object(
                WindowsCaptureBackend,
                "__init__",
                side_effect=AssertionError("should not construct backend"),
            ),
            patch.object(windows_capture.win32gui, "EnumWindows", side_effect=enum_windows),
            patch.object(windows_capture.win32gui, "IsWindowVisible", return_value=True),
            patch.object(windows_capture.win32gui, "GetWindowText", side_effect=["Alpha", "Beta"]),
        ):
            WindowsCaptureBackend.list_window_names(names)

        self.assertEqual(names, ["Alpha", "Beta"])

    def test_windows_capture_list_windows_uses_hwnd_ids_for_duplicate_titles(self):
        from platforms.windows import capture as windows_capture
        from platforms.windows.capture import WindowsCaptureBackend

        def enum_windows(callback, ctx):
            callback(101, ctx)
            callback(202, ctx)

        with (
            patch.object(windows_capture.win32gui, "EnumWindows", side_effect=enum_windows),
            patch.object(windows_capture.win32gui, "IsWindowVisible", return_value=True),
            patch.object(windows_capture.win32gui, "GetWindowText", side_effect=["Game", "Game"]),
        ):
            windows = WindowsCaptureBackend._list_windows()

        self.assertEqual([window.id for window in windows], ["101", "202"])
        self.assertEqual([window.title for window in windows], ["Game", "Game"])

    def test_windows_capture_select_window_accepts_hwnd_string_without_title_lookup(self):
        from platforms.windows import capture as windows_capture
        from platforms.windows.capture import WindowsCaptureBackend

        backend = WindowsCaptureBackend.__new__(WindowsCaptureBackend)

        with (
            patch.object(windows_capture.win32gui, "IsWindow", return_value=True),
            patch.object(windows_capture.win32gui, "FindWindow") as find_window,
            patch.object(backend, "_set_hwnd") as set_hwnd,
        ):
            backend.select_window("12345")

        find_window.assert_not_called()
        set_hwnd.assert_called_once_with(12345, "12345")

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
