from __future__ import annotations

import unittest

from simple_video_preview.app import _device_menu_title, _preset_candidates
from simple_video_preview.devices import VideoDevice


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


class DeviceMenuTitleTests(unittest.TestCase):
    def test_unique_names_stay_plain(self) -> None:
        devices = [
            VideoDevice(index=0, name="Built-in", unique_id="cam-0", model_id=None),
            VideoDevice(index=1, name="USB", unique_id="cam-1", model_id=None),
        ]
        self.assertEqual(_device_menu_title(devices[0], devices), "Built-in")

    def test_duplicate_names_include_index(self) -> None:
        devices = [
            VideoDevice(index=0, name="USB Camera", unique_id="cam-0", model_id=None),
            VideoDevice(index=1, name="USB Camera", unique_id="cam-1", model_id=None),
        ]
        self.assertEqual(_device_menu_title(devices[1], devices), "USB Camera (1)")


if __name__ == "__main__":
    unittest.main()
