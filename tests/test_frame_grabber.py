from __future__ import annotations

import unittest
from pathlib import Path

from simple_video_preview.capture_support import normalize_resolution_value
from simple_video_preview.frame_grabber import _extract_still_image_callback_args, _output_type_for_path


class NormalizeResolutionTests(unittest.TestCase):
    def test_maps_common_dimension_strings(self) -> None:
        self.assertEqual(normalize_resolution_value("3840x2160"), "4k")
        self.assertEqual(normalize_resolution_value("1920x1080"), "1080p")
        self.assertEqual(normalize_resolution_value("1280x720"), "720p")

    def test_preserves_named_presets(self) -> None:
        self.assertEqual(normalize_resolution_value("photo"), "photo")


class OutputTypeTests(unittest.TestCase):
    def test_png_maps_to_png_file_type(self) -> None:
        self.assertEqual(_output_type_for_path(Path("frame.png")), "NSPNGFileType")

    def test_bmp_maps_to_bmp_file_type(self) -> None:
        self.assertEqual(_output_type_for_path(Path("frame.bmp")), "NSBMPFileType")

    def test_unsupported_extension_raises(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported output file extension"):
            _output_type_for_path(Path("frame.gif"))


class StillImageCallbackTests(unittest.TestCase):
    def test_accepts_two_argument_callback_shape(self) -> None:
        sample_buffer = object()
        error = object()
        self.assertEqual(
            _extract_still_image_callback_args((sample_buffer, error)),
            (sample_buffer, error),
        )

    def test_accepts_three_argument_callback_shape(self) -> None:
        block = object()
        sample_buffer = object()
        error = object()
        self.assertEqual(
            _extract_still_image_callback_args((block, sample_buffer, error)),
            (sample_buffer, error),
        )

    def test_rejects_unexpected_callback_shape(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Unexpected still image callback arguments"):
            _extract_still_image_callback_args((object(),))


if __name__ == "__main__":
    unittest.main()
