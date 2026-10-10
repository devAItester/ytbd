#!/usr/bin/env python3
"""Validate the saved AsForJS fixture without network access."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "examples" / "AsForJS"
TAB_FILES = ("videos.json", "streams.json", "podcasts.json", "playlists.json")


def load_json(path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def main():
    failures = []
    tab_data = {}
    for name in TAB_FILES:
        path = ROOT / name
        try:
            data = load_json(path)
            if not isinstance(data, dict):
                raise ValueError("top-level JSON value must be an object")
            entries = data.get("entries")
            if not isinstance(entries, list):
                raise ValueError("missing list field: entries")
            tab_data[name] = data
            print(f"PASS {name}: {len(entries)} entries")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"{name}: {exc}")
            print(f"FAIL {name}: {exc}")

    tree_path = ROOT / "tree-data.json"
    try:
        tree = load_json(tree_path)
        if not isinstance(tree, dict):
            raise ValueError("top-level JSON value must be an object")
        for field in ("tabs", "playlist_metadata", "playlist_contents", "errors"):
            if field not in tree:
                raise ValueError(f"missing field: {field}")
        if not isinstance(tree["playlist_contents"], dict):
            raise ValueError("playlist_contents must be an object")
        if not isinstance(tree["errors"], dict):
            raise ValueError("errors must be an object")
        print(
            "PASS tree-data.json: "
            f"{len(tree['playlist_contents'])} expanded lists, "
            f"{len(tree['errors'])} recorded errors"
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"tree-data.json: {exc}")
        print(f"FAIL tree-data.json: {exc}")

    if failures:
        print(f"\nValidation failed: {len(failures)} problem(s).", file=sys.stderr)
        return 1
    print("\nValidation passed. No network requests were made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
