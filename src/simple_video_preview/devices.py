from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VideoDevice:
    index: int
    name: str
    unique_id: str
    model_id: str | None


def _video_devices_api():
    from AVFoundation import AVCaptureDevice, AVMediaTypeVideo

    return AVCaptureDevice, AVMediaTypeVideo


def list_video_devices() -> list[VideoDevice]:
    capture_device_cls, media_type_video = _video_devices_api()
    devices = capture_device_cls.devicesWithMediaType_(media_type_video)
    return [
        VideoDevice(
            index=index,
            name=str(device.localizedName()),
            unique_id=str(device.uniqueID()),
            model_id=str(device.modelID()) if device.modelID() is not None else None,
        )
        for index, device in enumerate(devices)
    ]


def resolve_device(
    devices: list[VideoDevice],
    *,
    device_id: str | None,
    device_name: str | None,
    device_index: int | None,
) -> VideoDevice:
    if not devices:
        raise ValueError("No video devices found")

    if device_id:
        for device in devices:
            if device.unique_id == device_id:
                return device
        raise ValueError(f"No device found for device_id={device_id!r}")

    if device_name:
        for device in devices:
            if device.name == device_name:
                return device
        raise ValueError(f"No device found for device_name={device_name!r}")

    if device_index is not None:
        for device in devices:
            if device.index == device_index:
                return device
        raise ValueError(f"No device found for device_index={device_index}")

    return devices[0]


def find_device_by_unique_id(devices: list[VideoDevice], unique_id: str) -> VideoDevice | None:
    for device in devices:
        if device.unique_id == unique_id:
            return device
    return None
