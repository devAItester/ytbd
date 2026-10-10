#!/usr/bin/env python3
"""End-to-end smoke test against one public YouTube channel; writes only to a temp directory."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANNEL_URL = "https://www.youtube.com/@RTFMurych"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ytbd-live-smoke-") as temporary:
        temp = Path(temporary)
        input_path = temp / "channels.txt"
        input_path.write_text(CHANNEL_URL + "\n", encoding="utf-8")
        command = [
            sys.executable,
            str(ROOT / "scripts/process_channels.py"),
            "--input", str(input_path),
            "--template", "outline.md",
            "--data", str(temp / "data"),
            "--output", str(temp / "output"),
        ]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        if result.returncode:
            return result.returncode

        channel_dir = temp / "data" / "RTFMurych"
        status = json.loads((channel_dir / "status.json").read_text(encoding="utf-8"))
        tabs = json.loads((channel_dir / "tabs.json").read_text(encoding="utf-8"))
        output_path = temp / "output" / "RTFMurych" / "outline.md"
        output = output_path.read_text(encoding="utf-8")

        if status.get("errors"):
            raise SystemExit("Collection reported errors: " + repr(status["errors"]))
        if not tabs:
            raise SystemExit("No channel tabs were discovered.")
        for tab in tabs:
            if status["tabs"].get(tab["key"], {}).get("status") != "ok":
                raise SystemExit("Tab collection did not succeed: " + tab["key"])
            if f'<summary>{tab["title"]} —' not in output:
                raise SystemExit("Discovered tab missing from Markdown: " + tab["key"])
        if "</a>- <a" in output:
            raise SystemExit("Markdown list entries are glued together.")

        print("Discovered tabs:", [tab["key"] for tab in tabs])
        print("Rendered Markdown passed structural checks.")
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
