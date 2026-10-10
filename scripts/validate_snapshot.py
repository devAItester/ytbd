#!/usr/bin/env python3
"""Проверяет сохранённые данные AsForJS без сетевых запросов."""
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
    for name in TAB_FILES:
        path = ROOT / name
        try:
            data = load_json(path)
            if not isinstance(data, dict):
                raise ValueError("верхний уровень JSON должен быть объектом")
            entries = data.get("entries")
            if not isinstance(entries, list):
                raise ValueError("отсутствует список entries")
            print(f"УСПЕХ {name}: записей — {len(entries)}")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"{name}: {exc}")
            print(f"ОШИБКА {name}: {exc}")

    tree_path = ROOT / "tree-data.json"
    try:
        tree = load_json(tree_path)
        if not isinstance(tree, dict):
            raise ValueError("верхний уровень JSON должен быть объектом")
        for field in ("tabs", "playlist_metadata", "playlist_contents", "errors"):
            if field not in tree:
                raise ValueError(f"отсутствует поле: {field}")
        if not isinstance(tree["playlist_contents"], dict):
            raise ValueError("playlist_contents должен быть объектом")
        if not isinstance(tree["errors"], dict):
            raise ValueError("errors должен быть объектом")
        print(
            "УСПЕХ tree-data.json: "
            f"раскрытых списков — {len(tree['playlist_contents'])}, "
            f"записанных ошибок — {len(tree['errors'])}"
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        failures.append(f"tree-data.json: {exc}")
        print(f"ОШИБКА tree-data.json: {exc}")

    if failures:
        print(f"\nПроверка не пройдена. Проблем: {len(failures)}.", file=sys.stderr)
        return 1
    print("\nПроверка пройдена. Сетевые запросы не выполнялись.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
