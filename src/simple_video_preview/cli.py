from __future__ import annotations

from dataclasses import asdict
import json
import sys

from .app import run_preview
from .config import PreviewConfig, build_parser
from .devices import list_video_devices


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list-devices":
        devices = list_video_devices()
        if args.json:
            print(json.dumps([asdict(device) for device in devices], indent=2))
        else:
            for device in devices:
                print(f"[{device.index}] {device.name} ({device.unique_id})")
        return 0

    if args.command == "preview":
        config = PreviewConfig()
        if args.config is not None:
            config = PreviewConfig.from_json_file(args.config)
        config = config.merged_with_cli(args)
        run_preview(config)
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
