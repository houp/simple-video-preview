from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from simple_video_preview.config import PreviewConfig, build_parser


class PreviewConfigTests(unittest.TestCase):
    def test_from_mapping_accepts_expected_fields(self) -> None:
        config = PreviewConfig.from_mapping(
            {
                "device_name": "External Camera",
                "width": 1920,
                "height": 1080,
                "title": "Demo",
                "session_preset": "4k",
            }
        )
        self.assertEqual(config.device_name, "External Camera")
        self.assertEqual(config.width, 1920)
        self.assertEqual(config.height, 1080)
        self.assertEqual(config.title, "Demo")
        self.assertEqual(config.session_preset, "4k")

    def test_from_mapping_rejects_unknown_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown config key"):
            PreviewConfig.from_mapping({"bogus": True})

    def test_from_mapping_rejects_invalid_session_preset(self) -> None:
        with self.assertRaisesRegex(ValueError, "session_preset must be one of"):
            PreviewConfig.from_mapping({"session_preset": "ultra"})

    def test_from_json_file_reads_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "preview.json"
            path.write_text('{"device_index": 1, "width": 800, "height": 600}')
            config = PreviewConfig.from_json_file(path)

        self.assertEqual(config.device_index, 1)
        self.assertEqual(config.width, 800)
        self.assertEqual(config.height, 600)

    def test_cli_values_override_json_values(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["preview", "--width", "1024", "--title", "CLI"])
        config = PreviewConfig.from_mapping({"width": 800, "height": 600, "title": "File"})
        merged = config.merged_with_cli(args)

        self.assertEqual(merged.width, 1024)
        self.assertEqual(merged.height, 600)
        self.assertEqual(merged.title, "CLI")
        self.assertEqual(merged.session_preset, "auto")


if __name__ == "__main__":
    unittest.main()
