from __future__ import annotations

import unittest

from simple_video_preview.devices import VideoDevice, resolve_device


class ResolveDeviceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.devices = [
            VideoDevice(index=0, name="Built-in", unique_id="cam-0", model_id=None),
            VideoDevice(index=1, name="USB", unique_id="cam-1", model_id=None),
        ]

    def test_resolve_defaults_to_first_device(self) -> None:
        device = resolve_device(self.devices, device_id=None, device_name=None, device_index=None)
        self.assertEqual(device.unique_id, "cam-0")

    def test_resolve_by_id(self) -> None:
        device = resolve_device(self.devices, device_id="cam-1", device_name=None, device_index=None)
        self.assertEqual(device.name, "USB")

    def test_resolve_by_name(self) -> None:
        device = resolve_device(self.devices, device_id=None, device_name="USB", device_index=None)
        self.assertEqual(device.index, 1)

    def test_resolve_by_index(self) -> None:
        device = resolve_device(self.devices, device_id=None, device_name=None, device_index=0)
        self.assertEqual(device.name, "Built-in")

    def test_resolve_raises_for_missing_device(self) -> None:
        with self.assertRaisesRegex(ValueError, "No device found"):
            resolve_device(self.devices, device_id="missing", device_name=None, device_index=None)


if __name__ == "__main__":
    unittest.main()
