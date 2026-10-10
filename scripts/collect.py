#!/usr/bin/env python3
"""Получает выбранные данные публичного YouTube-канала через yt-dlp."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

DATA_TYPES = ("channel", "videos", "playlists", "streams", "podcasts")
CHANNEL_SUFFIXES = {
    "channel": "",
    "videos": "/videos",
    "playlists": "/playlists",
    "streams": "/streams",
    "podcasts": "/podcasts",
}


def normalize_channel_url(value: str) -> str:
    """Проверяет URL канала и убирает завершающий слеш."""
    value = value.strip()
    if not value:
        raise ValueError("Укажи URL YouTube-канала.")
    if "://" not in value:
        value = "https://" + value
    parts = urlsplit(value)
    host = (parts.hostname or "").lower()
    if host not in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        raise ValueError("Пока поддерживаются URL каналов youtube.com.")
    path = parts.path.rstrip("/")
    if not (
        path.startswith("/@")
        or path.startswith("/channel/")
        or path.startswith("/c/")
        or path.startswith("/user/")
    ):
        raise ValueError(
            "Нужен URL канала вида youtube.com/@handle или "
            "youtube.com/channel/ID, а не URL видео или плейлиста."
        )
    return urlunsplit(("https", "www.youtube.com", path, "", ""))


def build_source_url(channel_url: str, data_type: str) -> str:
    """Строит URL выбранной вкладки канала без привязки к конкретному каналу."""
    return normalize_channel_url(channel_url) + CHANNEL_SUFFIXES[data_type]


def build_command(url: str) -> list[str]:
    """Формирует аргументы yt-dlp; shell для запуска не используется."""
    return [
        "yt-dlp",
        "--ignore-errors",
        "--skip-download",
        "--flat-playlist",
        "--dump-single-json",
        url,
    ]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Собрать выбранные общедоступные данные YouTube-канала."
    )
    parser.add_argument("--url", required=True, help="URL YouTube-канала")
    parser.add_argument(
        "--data",
        default="channel,videos",
        help="Типы через запятую: " + ", ".join(DATA_TYPES),
    )
    parser.add_argument(
        "--method",
        choices=("yt-dlp",),
        default="yt-dlp",
        help="Метод получения данных (пока реализован только yt-dlp)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data"),
        help="Каталог для результатов (по умолчанию: ./data)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        channel_url = normalize_channel_url(args.url)
    except ValueError as exc:
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        return 2

    selected = list(dict.fromkeys(
        item.strip() for item in args.data.split(",") if item.strip()
    ))
    unknown = [item for item in selected if item not in DATA_TYPES]
    if unknown:
        print(
            "ОШИБКА: неизвестные типы данных: "
            + ", ".join(unknown)
            + ". Доступны: "
            + ", ".join(DATA_TYPES),
            file=sys.stderr,
        )
        return 2
    if not selected:
        print("ОШИБКА: выбери хотя бы один тип данных через --data.", file=sys.stderr)
        return 2
    if shutil.which("yt-dlp") is None:
        print("ОШИБКА: yt-dlp не найден. Установи его и повтори запуск.", file=sys.stderr)
        return 2

    try:
        args.output.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"ОШИБКА: не удалось создать каталог результатов: {exc}", file=sys.stderr)
        return 1

    failures = 0
    for data_type in selected:
        source_url = build_source_url(channel_url, data_type)
        destination = args.output / f"{data_type}.json"
        print(f"Получение: {data_type} — {source_url}")
        result = None
        try:
            result = subprocess.run(
                build_command(source_url),
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if not result.stdout.strip():
                raise RuntimeError(
                    result.stderr.strip()
                    or f"yt-dlp не вернул JSON (код {result.returncode})."
                )
            payload = json.loads(result.stdout)
            temporary = destination.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary.replace(destination)
            print(f"УСПЕХ: {destination}")
            if result.returncode != 0:
                print(
                    f"ПРЕДУПРЕЖДЕНИЕ: yt-dlp завершился с кодом {result.returncode}.",
                    file=sys.stderr,
                )
                if result.stderr.strip():
                    print(result.stderr.strip(), file=sys.stderr)
        except (OSError, json.JSONDecodeError, RuntimeError) as exc:
            failures += 1
            print(f"ОШИБКА {data_type}: {exc}", file=sys.stderr)
            if result is not None and result.stderr.strip():
                print(result.stderr.strip(), file=sys.stderr)

    if failures:
        print(f"Сбор завершён с ошибками: {failures} из {len(selected)} задач.", file=sys.stderr)
        return 1
    print(f"Сбор завершён: успешно выполнено задач — {len(selected)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
