# simple-video-preview

Minimal macOS camera preview app in Python.

## Status

- All code in this repository is fully AI-generated.
- It has only been tested on an up-to-date macOS installation: macOS 26.4 (build 25E246).
- It has not been tested on older macOS releases, non-macOS systems, or a broad range of capture hardware.

Features:

- plain resizable window
- native fullscreen support
- camera selection by index, name, or unique device id
- configuration from CLI flags or JSON file
- highest supported capture preset by default, with optional override
- no in-window controls

## Requirements

- macOS
- `uv`
- Python 3.14

## Setup

```bash
UV_CACHE_DIR=.uv-cache uv venv --python /opt/homebrew/bin/python3.14
UV_CACHE_DIR=.uv-cache uv sync
```

## Usage

List devices:

```bash
UV_CACHE_DIR=.uv-cache uv run video-preview list-devices
```

Preview with the first device:

```bash
UV_CACHE_DIR=.uv-cache uv run video-preview preview
```

Preview while explicitly requesting 4K capture if the source supports it:

```bash
UV_CACHE_DIR=.uv-cache uv run video-preview preview --session-preset 4k
```

Preview with a specific device name:

```bash
UV_CACHE_DIR=.uv-cache uv run video-preview preview --device-name "FaceTime HD Camera"
```

Preview with a JSON config:

```json
{
  "device_name": "FaceTime HD Camera",
  "width": 1280,
  "height": 720,
  "title": "Preview",
  "session_preset": "4k"
}
```

```bash
cp preview.example.json preview.json
UV_CACHE_DIR=.uv-cache uv run video-preview preview --config preview.json
```

## Notes

- The window is intentionally empty other than the live preview layer.
- Use standard macOS fullscreen controls or shortcuts to enter fullscreen.
- If more than one selector is provided, resolution order is: `device_id`, `device_name`, `device_index`.
- `session_preset` can be `auto`, `4k`, `2160p`, `1080p`, `720p`, `high`, `photo`, or `input-priority`.
- `auto` prefers `4k`, then `1080p`, then `720p`, then `high`.
