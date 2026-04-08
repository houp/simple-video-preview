from __future__ import annotations

from PyObjCTools import AppHelper

from .config import PreviewConfig
from .devices import list_video_devices, resolve_device


def _appkit():
    from AppKit import (
        NSApplicationActivateIgnoringOtherApps,
        NSApp,
        NSApplication,
        NSApplicationActivationPolicyRegular,
        NSBackingStoreBuffered,
        NSMakeRect,
        NSView,
        NSRunningApplication,
        NSWindow,
        NSWindowCollectionBehaviorFullScreenPrimary,
        NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable,
        NSWindowStyleMaskResizable,
        NSWindowStyleMaskTitled,
    )

    return {
        "NSApplicationActivateIgnoringOtherApps": NSApplicationActivateIgnoringOtherApps,
        "NSApp": NSApp,
        "NSApplication": NSApplication,
        "NSApplicationActivationPolicyRegular": NSApplicationActivationPolicyRegular,
        "NSBackingStoreBuffered": NSBackingStoreBuffered,
        "NSMakeRect": NSMakeRect,
        "NSView": NSView,
        "NSRunningApplication": NSRunningApplication,
        "NSWindow": NSWindow,
        "NSWindowCollectionBehaviorFullScreenPrimary": NSWindowCollectionBehaviorFullScreenPrimary,
        "NSWindowStyleMaskClosable": NSWindowStyleMaskClosable,
        "NSWindowStyleMaskMiniaturizable": NSWindowStyleMaskMiniaturizable,
        "NSWindowStyleMaskResizable": NSWindowStyleMaskResizable,
        "NSWindowStyleMaskTitled": NSWindowStyleMaskTitled,
    }


def _foundation():
    from Foundation import NSObject

    return {"NSObject": NSObject}


def _objc():
    import objc

    return {"objc": objc}


def _avfoundation():
    from AVFoundation import (
        AVCaptureDevice,
        AVCaptureDeviceInput,
        AVCaptureSession,
        AVCaptureSessionPreset1920x1080,
        AVCaptureSessionPreset1280x720,
        AVCaptureSessionPreset3840x2160,
        AVCaptureSessionPresetHigh,
        AVCaptureSessionPresetInputPriority,
        AVCaptureSessionPresetPhoto,
        AVCaptureVideoPreviewLayer,
        AVLayerVideoGravityResizeAspect,
    )

    return {
        "AVCaptureDevice": AVCaptureDevice,
        "AVCaptureDeviceInput": AVCaptureDeviceInput,
        "AVCaptureSession": AVCaptureSession,
        "AVCaptureSessionPreset1280x720": AVCaptureSessionPreset1280x720,
        "AVCaptureSessionPreset1920x1080": AVCaptureSessionPreset1920x1080,
        "AVCaptureSessionPreset3840x2160": AVCaptureSessionPreset3840x2160,
        "AVCaptureSessionPresetHigh": AVCaptureSessionPresetHigh,
        "AVCaptureSessionPresetInputPriority": AVCaptureSessionPresetInputPriority,
        "AVCaptureSessionPresetPhoto": AVCaptureSessionPresetPhoto,
        "AVCaptureVideoPreviewLayer": AVCaptureVideoPreviewLayer,
        "AVLayerVideoGravityResizeAspect": AVLayerVideoGravityResizeAspect,
    }


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


def run_preview(config: PreviewConfig) -> None:
    devices = list_video_devices()
    selected = resolve_device(devices, **_selector_args(config))

    appkit = _appkit()
    foundation = _foundation()
    objc_api = _objc()
    avfoundation = _avfoundation()

    device = avfoundation["AVCaptureDevice"].deviceWithUniqueID_(selected.unique_id)
    if device is None:
        raise RuntimeError(f"Unable to access device {selected.unique_id!r}")

    device_input, error = avfoundation["AVCaptureDeviceInput"].deviceInputWithDevice_error_(device, None)
    if device_input is None:
        message = str(error) if error is not None else "unknown error"
        raise RuntimeError(f"Unable to create capture input: {message}")

    session = avfoundation["AVCaptureSession"].alloc().init()
    if not session.canAddInput_(device_input):
        raise RuntimeError("Capture session cannot add selected device input")
    session.addInput_(device_input)
    _configure_session_preset(session, avfoundation, config.session_preset)

    preview_layer = avfoundation["AVCaptureVideoPreviewLayer"].layerWithSession_(session)
    preview_layer.setVideoGravity_(avfoundation["AVLayerVideoGravityResizeAspect"])

    NSObject = foundation["NSObject"]
    objc = objc_api["objc"]

    class PreviewHostView(appkit["NSView"]):
        def initWithPreviewLayer_frame_(self, layer, frame):
            self = objc.super(PreviewHostView, self).initWithFrame_(frame)
            if self is None:
                return None
            self._preview_layer = layer
            self.setWantsLayer_(True)
            self.setLayer_(layer)
            self._refresh_preview_layer()
            return self

        def layout(self):
            objc.super(PreviewHostView, self).layout()
            self._refresh_preview_layer()

        def viewDidChangeBackingProperties(self):
            objc.super(PreviewHostView, self).viewDidChangeBackingProperties()
            self._refresh_preview_layer()

        def viewDidMoveToWindow(self):
            objc.super(PreviewHostView, self).viewDidMoveToWindow()
            self._refresh_preview_layer()

        def _refresh_preview_layer(self):
            self._preview_layer.setFrame_(self.bounds())
            self._preview_layer.setContentsScale_(_backing_scale_for_view(self))

    class ApplicationDelegate(NSObject):
        def initWithSession_(self, capture_session):
            self = objc.super(ApplicationDelegate, self).init()
            if self is None:
                return None
            self._session = capture_session
            return self

        def applicationShouldTerminateAfterLastWindowClosed_(self, _app):
            return True

        def applicationWillTerminate_(self, _notification):
            self._session.stopRunning()

    app = appkit["NSApplication"].sharedApplication()
    app.setActivationPolicy_(appkit["NSApplicationActivationPolicyRegular"])

    frame = appkit["NSMakeRect"](0, 0, config.width, config.height)
    style_mask = (
        appkit["NSWindowStyleMaskTitled"]
        | appkit["NSWindowStyleMaskClosable"]
        | appkit["NSWindowStyleMaskMiniaturizable"]
        | appkit["NSWindowStyleMaskResizable"]
    )
    window = appkit["NSWindow"].alloc().initWithContentRect_styleMask_backing_defer_(
        frame,
        style_mask,
        appkit["NSBackingStoreBuffered"],
        False,
    )
    window.setTitle_(config.title)
    window.setCollectionBehavior_(appkit["NSWindowCollectionBehaviorFullScreenPrimary"])
    window.center()

    content_view = PreviewHostView.alloc().initWithPreviewLayer_frame_(preview_layer, frame)
    window.setContentView_(content_view)
    app_delegate = ApplicationDelegate.alloc().initWithSession_(session)
    app.setDelegate_(app_delegate)
    window.makeKeyAndOrderFront_(None)

    appkit["NSRunningApplication"].currentApplication().activateWithOptions_(
        appkit["NSApplicationActivateIgnoringOtherApps"]
    )
    session.startRunning()
    AppHelper.installMachInterrupt()
    try:
        app.run()
    finally:
        session.stopRunning()


def _selector_args(config: PreviewConfig) -> dict[str, str | int | None]:
    return {
        "device_id": config.device_id,
        "device_name": config.device_name,
        "device_index": config.device_index,
    }


def _configure_session_preset(session, avfoundation: dict[str, object], requested_preset: str) -> None:
    for preset_name in _preset_candidates(requested_preset):
        preset_value = avfoundation[preset_name]
        if session.canSetSessionPreset_(preset_value):
            session.setSessionPreset_(preset_value)
            return

    if requested_preset != "auto":
        raise RuntimeError(f"Selected device does not support session preset {requested_preset!r}")


def _preset_candidates(requested_preset: str) -> list[str]:
    if requested_preset == "auto":
        return AUTO_PRESET_ORDER

    preset_name = PRESET_ALIASES[requested_preset]
    return [preset_name]


def _backing_scale_for_view(view) -> float:
    window = view.window()
    if window is None:
        return 2.0
    screen = window.screen()
    if screen is not None:
        return float(screen.backingScaleFactor())
    return float(window.backingScaleFactor())
