from __future__ import annotations

import unittest

from simple_video_preview.app import _preset_candidates


class SessionPresetTests(unittest.TestCase):
    def test_auto_tries_highest_presets_first(self) -> None:
        self.assertEqual(
            _preset_candidates("auto"),
            [
                "AVCaptureSessionPreset3840x2160",
                "AVCaptureSessionPreset1920x1080",
                "AVCaptureSessionPreset1280x720",
                "AVCaptureSessionPresetHigh",
            ],
        )

    def test_named_preset_maps_to_single_constant(self) -> None:
        self.assertEqual(_preset_candidates("4k"), ["AVCaptureSessionPreset3840x2160"])
        self.assertEqual(_preset_candidates("1080p"), ["AVCaptureSessionPreset1920x1080"])


if __name__ == "__main__":
    unittest.main()
