from __future__ import annotations

PRESET_ALIASES = {
    "4k": "AVCaptureSessionPreset3840x2160",
    "2160p": "AVCaptureSessionPreset3840x2160",
    "1080p": "AVCaptureSessionPreset1920x1080",
    "720p": "AVCaptureSessionPreset1280x720",
    "high": "AVCaptureSessionPresetHigh",
    "photo": "AVCaptureSessionPresetPhoto",
    "input-priority": "AVCaptureSessionPresetInputPriority",
}

AUTO_PRESET_ORDER = [
    "AVCaptureSessionPreset3840x2160",
    "AVCaptureSessionPreset1920x1080",
    "AVCaptureSessionPreset1280x720",
    "AVCaptureSessionPresetHigh",
]

PRESET_MENU_ITEMS = [
    ("auto", "Auto"),
    ("4k", "4K"),
    ("1080p", "1080p"),
    ("720p", "720p"),
    ("high", "High"),
    ("photo", "Photo"),
    ("input-priority", "Input Priority"),
]

RESOLUTION_ALIASES = {
    "3840x2160": "4k",
    "1920x1080": "1080p",
    "1280x720": "720p",
}


def normalize_resolution_value(value: str) -> str:
    normalized = value.strip().lower()
    return RESOLUTION_ALIASES.get(normalized, normalized)


def configure_session_preset(session, avfoundation: dict[str, object], requested_preset: str) -> None:
    for preset_name in preset_candidates(requested_preset):
        preset_value = avfoundation[preset_name]
        if session.canSetSessionPreset_(preset_value):
            session.setSessionPreset_(preset_value)
            return

    if requested_preset != "auto":
        raise RuntimeError(f"Selected device does not support session preset {requested_preset!r}")


def create_capture_session_for_device(avfoundation: dict[str, object], unique_id: str, requested_preset: str):
    device = avfoundation["AVCaptureDevice"].deviceWithUniqueID_(unique_id)
    if device is None:
        raise RuntimeError(f"Unable to access device {unique_id!r}")

    device_input, error = avfoundation["AVCaptureDeviceInput"].deviceInputWithDevice_error_(device, None)
    if device_input is None:
        message = str(error) if error is not None else "unknown error"
        raise RuntimeError(f"Unable to create capture input: {message}")

    session = avfoundation["AVCaptureSession"].alloc().init()
    if not session.canAddInput_(device_input):
        raise RuntimeError("Capture session cannot add selected device input")

    session.addInput_(device_input)
    configure_session_preset(session, avfoundation, requested_preset)
    return session, device_input


def preset_candidates(requested_preset: str) -> list[str]:
    if requested_preset == "auto":
        return AUTO_PRESET_ORDER

    preset_name = PRESET_ALIASES[requested_preset]
    return [preset_name]


def supported_session_presets(avfoundation: dict[str, object], unique_id: str) -> set[str]:
    try:
        device = avfoundation["AVCaptureDevice"].deviceWithUniqueID_(unique_id)
        if device is None:
            return set()

        device_input, _error = avfoundation["AVCaptureDeviceInput"].deviceInputWithDevice_error_(device, None)
        if device_input is None:
            return set()

        session = avfoundation["AVCaptureSession"].alloc().init()
        if not session.canAddInput_(device_input):
            return set()

        session.addInput_(device_input)
        supported = set()
        for preset in PRESET_ALIASES:
            preset_name = PRESET_ALIASES[preset]
            if session.canSetSessionPreset_(avfoundation[preset_name]):
                supported.add(preset)
        return supported
    except Exception:
        return set()
