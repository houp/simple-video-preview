from __future__ import annotations

import unittest
from pathlib import Path

from simple_video_preview.capture_support import normalize_resolution_value
from simple_video_preview.frame_grabber import _output_type_for_path


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


if __name__ == "__main__":
    unittest.main()
