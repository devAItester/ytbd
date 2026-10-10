#!/usr/bin/env python3
"""Обрабатывает последние N непустых URL из config/channels.txt."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config/channels.txt"
DEFAULT_TEMPLATE = ROOT / "templates/channel.md"
DEFAULT_OUTPUT = ROOT / "data/channels"
ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}


def normalize_channel_url(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Пустой адрес канала.")
    if "://" not in value:
        value = "https://" + value
    parts = urlsplit(value)
    if (parts.hostname or "").lower() not in ALLOWED_HOSTS:
        raise ValueError("Разрешены только адреса каналов youtube.com.")
    path = parts.path.rstrip("/")
    if not (path.startswith("/@") or path.startswith("/channel/") or path.startswith("/c/") or path.startswith("/user/")):
        raise ValueError("Нужен URL канала вида youtube.com/@handle или youtube.com/channel/ID.")
    return urlunsplit(("https", "www.youtube.com", path, "", ""))


def read_last_urls(path: Path, count: int) -> list[str]:
    if count < 1:
        raise ValueError("Количество последних строк должно быть не меньше 1.")
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    candidates = [line for line in lines if line and not line.startswith("#")]
    result = []
    for line in candidates[-count:]:
        url = normalize_channel_url(line)
        if url not in result:
            result.append(url)
    return result


def folder_name(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    last = path.rsplit("/", 1)[-1].lstrip("@")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", last).strip(".-_")
    if not slug:
        raise ValueError(f"Не удалось определить имя каталога для {url}")
    return slug[:80]


def fetch_channel(url: str) -> dict:
    command = ["yt-dlp", "--ignore-errors", "--skip-download", "--flat-playlist", "--dump-single-json", url]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if not result.stdout.strip():
        raise RuntimeError(result.stderr.strip() or f"yt-dlp не вернул данные (код {result.returncode}).")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"yt-dlp вернул некорректный JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Ожидался JSON-объект с данными канала.")
    if result.returncode and not data:
        raise RuntimeError(result.stderr.strip() or f"yt-dlp завершился с кодом {result.returncode}.")
    return data


def render_items(data: dict) -> str:
    entries = data.get("entries") or []
    lines = []
    for entry in entries[:20]:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or entry.get("id") or "Без названия").replace("[", "\\[").replace("]", "\\]")
        url = entry.get("url") or entry.get("webpage_url")
        item_id = entry.get("id")
        if not url and item_id:
            url = f"https://www.youtube.com/watch?v={item_id}"
        lines.append(f"- [{title}]({url})" if url else f"- {title}")
    return "\n".join(lines) if lines else "_В ответе источника нет списка элементов._"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Создать каталоги каналов по последним строкам списка.")
    parser.add_argument("--last-lines", type=int, default=4, help="Сколько последних непустых строк обработать")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Файл со списком URL")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Шаблон Markdown канала")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Каталог результатов")
    args = parser.parse_args(argv)
    if shutil.which("yt-dlp") is None:
        print("ОШИБКА: yt-dlp не установлен.", file=sys.stderr)
        return 2
    try:
        urls = read_last_urls(args.input, args.last_lines)
        template = args.template.read_text(encoding="utf-8")
        args.output.mkdir(parents=True, exist_ok=True)
    except (OSError, ValueError) as exc:
        print(f"ОШИБКА настроек: {exc}", file=sys.stderr)
        return 2
    if not urls:
        print("Нет URL для обработки.", file=sys.stderr)
        return 2
    failures = 0
    for url in urls:
        try:
            data = fetch_channel(url)
            folder = args.output / folder_name(url)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "channel.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            title = str(data.get("title") or data.get("channel") or folder.name)
            channel_id = str(data.get("channel_id") or data.get("id") or "не указан")
            entries = data.get("entries") or []
            rendered = template.replace("{{title}}", title).replace("{{url}}", url).replace("{{channel_id}}", channel_id).replace("{{updated_at}}", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")).replace("{{item_count}}", str(len(entries))).replace("{{items}}", render_items(data))
            (folder / "README.md").write_text(rendered, encoding="utf-8")
            print(f"УСПЕХ: {url} -> {folder}")
        except (OSError, ValueError, RuntimeError) as exc:
            failures += 1
            print(f"ОШИБКА {url}: {exc}", file=sys.stderr)
    print(f"Обработано адресов: {len(urls) - failures} из {len(urls)}.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
