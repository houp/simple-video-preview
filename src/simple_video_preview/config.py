from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ALLOWED_SESSION_PRESETS = {"auto", "4k", "2160p", "1080p", "720p", "high", "photo", "input-priority"}
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_TITLE = "Video Preview"
DEFAULT_SESSION_PRESET = "auto"


@dataclass(slots=True)
class PreviewConfig:
    device_id: str | None = None
    device_name: str | None = None
    device_index: int | None = None
    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    title: str = DEFAULT_TITLE
    session_preset: str = DEFAULT_SESSION_PRESET

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "PreviewConfig":
        unknown_keys = sorted(set(data) - set(cls.__dataclass_fields__))
        if unknown_keys:
            joined = ", ".join(unknown_keys)
            raise ValueError(f"Unknown config key(s): {joined}")

        device_index = data.get("device_index")
        if device_index is not None:
            device_index = int(device_index)

        width = int(data.get("width", DEFAULT_WIDTH))
        height = int(data.get("height", DEFAULT_HEIGHT))
        if width <= 0 or height <= 0:
            raise ValueError("width and height must be positive integers")

        session_preset = str(data.get("session_preset", DEFAULT_SESSION_PRESET))
        if session_preset not in ALLOWED_SESSION_PRESETS:
            allowed = ", ".join(sorted(ALLOWED_SESSION_PRESETS))
            raise ValueError(f"session_preset must be one of: {allowed}")

        return cls(
            device_id=data.get("device_id"),
            device_name=data.get("device_name"),
            device_index=device_index,
            width=width,
            height=height,
            title=str(data.get("title", DEFAULT_TITLE)),
            session_preset=session_preset,
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> "PreviewConfig":
        raw = json.loads(Path(path).read_text())
        if not isinstance(raw, dict):
            raise ValueError("Config file must contain a JSON object")
        return cls.from_mapping(raw)

    def merged_with_cli(self, args: argparse.Namespace) -> "PreviewConfig":
        merged = asdict(self)
        for field_name in self.__dataclass_fields__:
            value = getattr(args, field_name, None)
            if value is not None:
                merged[field_name] = value
        return PreviewConfig.from_mapping(merged)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-preview",
        description="Minimal macOS camera preview window.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-devices", help="List available video devices.")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Print device list as JSON.",
    )

    preview_parser = subparsers.add_parser("preview", help="Open the preview window.")
    preview_parser.add_argument("--config", type=Path, help="Path to a JSON config file.")
    preview_parser.add_argument("--device-id", dest="device_id", help="AVFoundation device unique id.")
    preview_parser.add_argument("--device-name", dest="device_name", help="Exact device name.")
    preview_parser.add_argument("--device-index", dest="device_index", type=int, help="Zero-based device index.")
    preview_parser.add_argument("--width", type=int, help="Initial window width.")
    preview_parser.add_argument("--height", type=int, help="Initial window height.")
    preview_parser.add_argument("--title", help="Window title.")
    preview_parser.add_argument(
        "--session-preset",
        dest="session_preset",
        choices=["auto", "4k", "2160p", "1080p", "720p", "high", "photo", "input-priority"],
        help="Preferred capture session preset.",
    )

    return parser
