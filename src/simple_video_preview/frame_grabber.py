from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path

import objc
from AppKit import NSImage
from Foundation import NSDate, NSObject

from .capture_support import create_capture_session_for_device, normalize_resolution_value
from .devices import list_video_devices, resolve_device


def _avfoundation():
    from AVFoundation import (
        AVCaptureDevice,
        AVCaptureDeviceInput,
        AVCapturePhotoOutput,
        AVCapturePhotoQualityPrioritizationSpeed,
        AVCapturePhotoSettings,
        AVCaptureSession,
        AVCaptureSessionPreset1280x720,
        AVCaptureSessionPreset1920x1080,
        AVCaptureSessionPreset3840x2160,
        AVCaptureSessionPresetHigh,
        AVCaptureSessionPresetInputPriority,
        AVCaptureSessionPresetPhoto,
    )

    return {
        "AVCaptureDevice": AVCaptureDevice,
        "AVCaptureDeviceInput": AVCaptureDeviceInput,
        "AVCapturePhotoOutput": AVCapturePhotoOutput,
        "AVCapturePhotoQualityPrioritizationSpeed": AVCapturePhotoQualityPrioritizationSpeed,
        "AVCapturePhotoSettings": AVCapturePhotoSettings,
        "AVCaptureSession": AVCaptureSession,
        "AVCaptureSessionPreset1280x720": AVCaptureSessionPreset1280x720,
        "AVCaptureSessionPreset1920x1080": AVCaptureSessionPreset1920x1080,
        "AVCaptureSessionPreset3840x2160": AVCaptureSessionPreset3840x2160,
        "AVCaptureSessionPresetHigh": AVCaptureSessionPresetHigh,
        "AVCaptureSessionPresetInputPriority": AVCaptureSessionPresetInputPriority,
        "AVCaptureSessionPresetPhoto": AVCaptureSessionPresetPhoto,
    }


def _appkit():
    from AppKit import NSBitmapImageRep, NSBMPFileType, NSJPEGFileType, NSPNGFileType, NSTIFFFileType

    return {
        "NSBitmapImageRep": NSBitmapImageRep,
        "NSBMPFileType": NSBMPFileType,
        "NSJPEGFileType": NSJPEGFileType,
        "NSPNGFileType": NSPNGFileType,
        "NSTIFFFileType": NSTIFFFileType,
    }


FILE_TYPES = {
    ".png": "NSPNGFileType",
    ".jpg": "NSJPEGFileType",
    ".jpeg": "NSJPEGFileType",
    ".bmp": "NSBMPFileType",
    ".tif": "NSTIFFFileType",
    ".tiff": "NSTIFFFileType",
}

ALLOWED_RESOLUTIONS = {"auto", "4k", "2160p", "1080p", "720p", "high", "photo", "input-priority"}


class PhotoCaptureDelegate(NSObject):
    def initWithOutputPath_appkit_doneEvent_(self, output_path, appkit, done_event):
        self = objc.super(PhotoCaptureDelegate, self).init()
        if self is None:
            return None
        self._output_path = output_path
        self._appkit = appkit
        self._done_event = done_event
        self._error = None
        self._captured_size = None
        return self

    @objc.typedSelector(b"v@:@@@")
    def captureOutput_didFinishProcessingPhoto_error_(self, _output, photo, error):
        try:
            if error is not None:
                raise RuntimeError(str(error))
            self._write_photo(photo)
        except Exception as exc:  # noqa: BLE001
            self._error = exc
        finally:
            self._done_event.set()

    def _write_photo(self, photo) -> None:
        photo_data = photo.fileDataRepresentation()
        if photo_data is None:
            raise RuntimeError("Failed to extract photo data representation")

        bitmap_rep = _bitmap_rep_from_data(photo_data, self._appkit)
        if bitmap_rep is None:
            raise RuntimeError("Failed to create bitmap representation from captured photo")

        self._captured_size = (int(bitmap_rep.pixelsWide()), int(bitmap_rep.pixelsHigh()))
        if _bitmap_rep_looks_black(bitmap_rep):
            raise RuntimeError("Captured frame is black")

        output_type = _output_type_for_path(self._output_path)
        encoded_data = bitmap_rep.representationUsingType_properties_(
            self._appkit[output_type],
            {},
        )
        if encoded_data is None:
            raise RuntimeError(f"Failed to encode image for {self._output_path}")

        if not encoded_data.writeToFile_atomically_(str(self._output_path), True):
            raise RuntimeError(f"Failed to write output file {self._output_path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture one frame from a macOS video device.")
    parser.add_argument("--device-name", required=True, help="Exact video device name.")
    parser.add_argument(
        "--resolution",
        required=True,
        help="Requested resolution or preset. Supported values: auto, 4k, 2160p, 1080p, 720p, high, photo, input-priority, 3840x2160, 1920x1080, 1280x720.",
    )
    parser.add_argument("--output", required=True, type=Path, help="Output image path (.png, .jpg, .jpeg, .bmp, .tif, .tiff).")
    parser.add_argument("--timeout", type=float, default=10.0, help="Seconds to wait for the first frame.")
    parser.add_argument("--warmup", type=float, default=1.0, help="Seconds to let the camera warm up before capture.")
    parser.add_argument("--attempts", type=int, default=3, help="Maximum capture attempts if the camera returns black frames.")
    parser.add_argument(
        "--retry-on-black",
        action="store_true",
        help="Retry if the captured frame looks black. Disabled by default because a black image may be a valid signal.",
    )
    return parser


def capture_one_frame(
    device_name: str,
    resolution: str,
    output_path: Path,
    timeout: float = 10.0,
    warmup: float = 1.0,
    attempts: int = 3,
    retry_on_black: bool = False,
) -> tuple[int, int]:
    avfoundation = _avfoundation()
    appkit = _appkit()

    requested_preset = normalize_resolution_value(resolution)
    if requested_preset not in ALLOWED_RESOLUTIONS:
        raise ValueError(f"Unsupported resolution value {resolution!r}")
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if warmup < 0:
        raise ValueError("warmup must be non-negative")

    devices = list_video_devices()
    selected = resolve_device(devices, device_id=None, device_name=device_name, device_index=None)
    session, _device_input = create_capture_session_for_device(avfoundation, selected.unique_id, requested_preset)

    photo_output = avfoundation["AVCapturePhotoOutput"].alloc().init()
    if not session.canAddOutput_(photo_output):
        raise RuntimeError("Capture session cannot add photo output")
    session.addOutput_(photo_output)

    if hasattr(photo_output, "setLivePhotoCaptureEnabled_") and photo_output.isLivePhotoCaptureSupported():
        photo_output.setLivePhotoCaptureEnabled_(False)
    if hasattr(photo_output, "setMaxPhotoQualityPrioritization_"):
        photo_output.setMaxPhotoQualityPrioritization_(
            avfoundation["AVCapturePhotoQualityPrioritizationSpeed"]
        )

    settings = avfoundation["AVCapturePhotoSettings"].photoSettings()
    if hasattr(settings, "setPhotoQualityPrioritization_"):
        settings.setPhotoQualityPrioritization_(
            avfoundation["AVCapturePhotoQualityPrioritizationSpeed"]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    done_event = threading.Event()
    delegate = PhotoCaptureDelegate.alloc().initWithOutputPath_appkit_doneEvent_(
        output_path,
        appkit,
        done_event,
    )

    session.startRunning()
    try:
        from Foundation import NSRunLoop

        if warmup:
            deadline = time.monotonic() + warmup
            while time.monotonic() < deadline:
                NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.05))

        last_error: Exception | None = None
        for attempt_index in range(attempts):
            photo_output.capturePhotoWithSettings_delegate_(settings, delegate)

            deadline = time.monotonic() + timeout
            while not done_event.is_set():
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out after {timeout:.1f}s waiting for captured frame")
                NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.05))

            if delegate._error is None and delegate._captured_size is not None:
                if retry_on_black:
                    bitmap_rep = _bitmap_rep_from_path(output_path, appkit)
                    if bitmap_rep is not None and _bitmap_rep_looks_black(bitmap_rep):
                        last_error = RuntimeError("Captured frame is black")
                    else:
                        return delegate._captured_size
                else:
                    return delegate._captured_size

            if delegate._error is not None:
                last_error = delegate._error
            elif last_error is None:
                last_error = RuntimeError("Failed to capture frame")

            if attempt_index + 1 < attempts:
                if output_path.exists():
                    output_path.unlink()
                done_event.clear()
                delegate = PhotoCaptureDelegate.alloc().initWithOutputPath_appkit_doneEvent_(
                    output_path,
                    appkit,
                    done_event,
                )
                NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.25))

        raise RuntimeError(str(last_error) if last_error is not None else "Failed to capture frame")
    finally:
        session.stopRunning()


def main() -> int:
    args = build_parser().parse_args()
    width, height = capture_one_frame(
        args.device_name,
        args.resolution,
        args.output,
        args.timeout,
        args.warmup,
        args.attempts,
        args.retry_on_black,
    )
    print(f"Saved {args.output} ({width}x{height})")
    return 0


def _output_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in FILE_TYPES:
        supported = ", ".join(sorted(FILE_TYPES))
        raise ValueError(f"Unsupported output file extension {suffix!r}. Supported: {supported}")
    return FILE_TYPES[suffix]


def _bitmap_rep_from_data(photo_data, appkit: dict[str, object]):
    image = NSImage.alloc().initWithData_(photo_data)
    if image is None:
        return None

    tiff_data = image.TIFFRepresentation()
    if tiff_data is None:
        return None

    return appkit["NSBitmapImageRep"].imageRepWithData_(tiff_data)


def _bitmap_rep_from_path(path: Path, appkit: dict[str, object]):
    data = path.read_bytes()
    return appkit["NSBitmapImageRep"].imageRepWithData_(data)


def _bitmap_rep_looks_black(bitmap_rep, *, samples_per_axis: int = 8, threshold: float = 0.02) -> bool:
    width = max(1, int(bitmap_rep.pixelsWide()))
    height = max(1, int(bitmap_rep.pixelsHigh()))

    total = 0.0
    count = 0
    for ix in range(samples_per_axis):
        x = min(width - 1, round(ix * (width - 1) / max(1, samples_per_axis - 1)))
        for iy in range(samples_per_axis):
            y = min(height - 1, round(iy * (height - 1) / max(1, samples_per_axis - 1)))
            color = bitmap_rep.colorAtX_y_(x, y)
            if color is None:
                continue
            converted = color.colorUsingColorSpaceName_("NSCalibratedRGBColorSpace")
            if converted is None:
                continue
            total += (
                float(converted.redComponent())
                + float(converted.greenComponent())
                + float(converted.blueComponent())
            ) / 3.0
            count += 1

    if count == 0:
        return True
    return (total / count) <= threshold
