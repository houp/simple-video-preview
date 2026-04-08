from __future__ import annotations

from PyObjCTools import AppHelper

from .capture_support import (
    PRESET_ALIASES,
    PRESET_MENU_ITEMS,
    create_capture_session_for_device,
    normalize_resolution_value,
    preset_candidates,
    supported_session_presets,
)
from .config import PreviewConfig
from .devices import find_device_by_unique_id, list_video_devices, resolve_device


def _appkit():
    from AppKit import (
        NSApplicationActivateIgnoringOtherApps,
        NSApp,
        NSApplication,
        NSApplicationActivationPolicyRegular,
        NSBackingStoreBuffered,
        NSControlStateValueOff,
        NSControlStateValueOn,
        NSEventModifierFlagCommand,
        NSMakeRect,
        NSMenu,
        NSMenuItem,
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
        "NSControlStateValueOff": NSControlStateValueOff,
        "NSControlStateValueOn": NSControlStateValueOn,
        "NSEventModifierFlagCommand": NSEventModifierFlagCommand,
        "NSMakeRect": NSMakeRect,
        "NSMenu": NSMenu,
        "NSMenuItem": NSMenuItem,
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


def run_preview(config: PreviewConfig) -> None:
    devices = list_video_devices()
    selected = resolve_device(devices, **_selector_args(config))

    appkit = _appkit()
    foundation = _foundation()
    objc_api = _objc()
    avfoundation = _avfoundation()

    session, _device_input = _create_capture_session_for_device(
        avfoundation,
        selected.unique_id,
        config.session_preset,
    )

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

    class PreviewApplicationController(NSObject):
        def initWithSession_previewLayer_avfoundation_appkit_config_currentDevice_(
            self,
            capture_session,
            preview_layer_obj,
            av_api,
            appkit_api,
            preview_config,
            current_device,
        ):
            self = objc.super(PreviewApplicationController, self).init()
            if self is None:
                return None
            self._session = capture_session
            self._preview_layer = preview_layer_obj
            self._avfoundation = av_api
            self._appkit = appkit_api
            self._config = preview_config
            self._current_device_id = current_device.unique_id
            self._video_menu = None
            self._preset_menu = None
            return self

        def applicationShouldTerminateAfterLastWindowClosed_(self, _app):
            return True

        def applicationWillTerminate_(self, _notification):
            self._session.stopRunning()

        def terminateApp_(self, _sender):
            self._appkit["NSApp"]().terminate_(None)

        def selectVideoDevice_(self, sender):
            unique_id = str(sender.representedObject())
            if unique_id == self._current_device_id:
                return
            self._replace_active_session(unique_id, self._config.session_preset)

        def selectSessionPreset_(self, sender):
            preset = str(sender.representedObject())
            if preset == self._config.session_preset:
                return
            self._replace_active_session(self._current_device_id, preset)

        def menuNeedsUpdate_(self, menu):
            if self._video_menu is not None and menu == self._video_menu:
                self._reload_video_menu()
            if self._preset_menu is not None and menu == self._preset_menu:
                self._reload_preset_menu()

        def _replace_active_session(self, unique_id: str, session_preset: str) -> None:
            try:
                replacement_session, _replacement_input = _create_capture_session_for_device(
                    self._avfoundation,
                    unique_id,
                    session_preset,
                )
            except RuntimeError as error:
                print(f"Unable to apply device={unique_id} preset={session_preset}: {error}")
                return

            previous_session = self._session
            try:
                previous_session.stopRunning()
                self._preview_layer.setSession_(replacement_session)
                replacement_session.startRunning()
                self._session = replacement_session
                self._current_device_id = unique_id
                self._config.session_preset = session_preset
            except Exception:
                self._preview_layer.setSession_(previous_session)
                previous_session.startRunning()
                raise

            self._reload_video_menu()
            self._reload_preset_menu()

        def _reload_video_menu(self) -> None:
            if self._video_menu is None:
                return

            self._video_menu.removeAllItems()
            devices = list_video_devices()
            for device in devices:
                item = self._appkit["NSMenuItem"].alloc().initWithTitle_action_keyEquivalent_(
                    _device_menu_title(device, devices),
                    "selectVideoDevice:",
                    "",
                )
                item.setTarget_(self)
                item.setRepresentedObject_(device.unique_id)
                item.setState_(
                    self._appkit["NSControlStateValueOn"]
                    if device.unique_id == self._current_device_id
                    else self._appkit["NSControlStateValueOff"]
                )
                self._video_menu.addItem_(item)

            current_device = find_device_by_unique_id(devices, self._current_device_id)
            if current_device is None and devices:
                self._current_device_id = devices[0].unique_id
                self._reload_video_menu()

        def _reload_preset_menu(self) -> None:
            if self._preset_menu is None:
                return

            self._preset_menu.removeAllItems()
            supported_presets = _supported_session_presets(self._avfoundation, self._current_device_id)
            for preset, title in PRESET_MENU_ITEMS:
                item = self._appkit["NSMenuItem"].alloc().initWithTitle_action_keyEquivalent_(
                    title,
                    "selectSessionPreset:",
                    "",
                )
                item.setTarget_(self)
                item.setRepresentedObject_(preset)
                item.setEnabled_(preset == "auto" or preset in supported_presets)
                item.setState_(
                    self._appkit["NSControlStateValueOn"]
                    if preset == self._config.session_preset
                    else self._appkit["NSControlStateValueOff"]
                )
                self._preset_menu.addItem_(item)

        def attachVideoMenu_(self, menu):
            self._video_menu = menu
            self._reload_video_menu()

        def attachPresetMenu_(self, menu):
            self._preset_menu = menu
            self._reload_preset_menu()

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
    app_delegate = PreviewApplicationController.alloc().initWithSession_previewLayer_avfoundation_appkit_config_currentDevice_(
        session,
        preview_layer,
        avfoundation,
        appkit,
        config,
        selected,
    )
    app.setDelegate_(app_delegate)
    app.setMainMenu_(_build_main_menu(appkit, app_delegate, config.title))
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
    configure_session_preset(session, avfoundation, requested_preset)


def _create_capture_session_for_device(avfoundation: dict[str, object], unique_id: str, requested_preset: str):
    return create_capture_session_for_device(avfoundation, unique_id, requested_preset)


def _preset_candidates(requested_preset: str) -> list[str]:
    return preset_candidates(requested_preset)


def _backing_scale_for_view(view) -> float:
    window = view.window()
    if window is None:
        return 2.0
    screen = window.screen()
    if screen is not None:
        return float(screen.backingScaleFactor())
    return float(window.backingScaleFactor())


def _build_main_menu(appkit: dict[str, object], controller, app_name: str):
    menu_bar = appkit["NSMenu"].alloc().init()

    app_menu_item = appkit["NSMenuItem"].alloc().init()
    app_menu_item.setTitle_(app_name)
    menu_bar.addItem_(app_menu_item)

    app_menu = appkit["NSMenu"].alloc().initWithTitle_(app_name)
    quit_item = appkit["NSMenuItem"].alloc().initWithTitle_action_keyEquivalent_(
        f"Quit {app_name}",
        "terminateApp:",
        "q",
    )
    quit_item.setTarget_(controller)
    quit_item.setKeyEquivalentModifierMask_(appkit["NSEventModifierFlagCommand"])
    app_menu.addItem_(quit_item)
    app_menu_item.setSubmenu_(app_menu)

    video_menu_item = appkit["NSMenuItem"].alloc().init()
    menu_bar.addItem_(video_menu_item)

    video_menu = appkit["NSMenu"].alloc().initWithTitle_("Video")
    video_menu.setDelegate_(controller)
    video_menu_item.setSubmenu_(video_menu)
    video_menu_item.setTitle_("Video")
    controller.attachVideoMenu_(video_menu)

    preset_menu_item = appkit["NSMenuItem"].alloc().init()
    menu_bar.addItem_(preset_menu_item)

    preset_menu = appkit["NSMenu"].alloc().initWithTitle_("Resolution")
    preset_menu.setDelegate_(controller)
    preset_menu_item.setSubmenu_(preset_menu)
    preset_menu_item.setTitle_("Resolution")
    controller.attachPresetMenu_(preset_menu)

    return menu_bar


def _device_menu_title(device, devices: list) -> str:
    name_count = sum(1 for candidate in devices if candidate.name == device.name)
    if name_count > 1:
        return f"{device.name} ({device.index})"
    return device.name


def _supported_session_presets(avfoundation: dict[str, object], unique_id: str) -> set[str]:
    return supported_session_presets(avfoundation, unique_id)
