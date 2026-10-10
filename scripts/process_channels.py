#!/usr/bin/env python3
"""Инкрементальный сбор публичных метаданных YouTube и вывод через Markdown-шаблоны."""
from __future__ import annotations

import argparse
import json
import hashlib
import re
from html.parser import HTMLParser
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "config/channels.txt"
DEFAULT_TEMPLATES = ROOT / "templates"
DEFAULT_DATA = ROOT / "data/channels"
DEFAULT_OUTPUT = ROOT / "data/output"
ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}
# Recognized tab types; the active list is discovered from the channel page.
TABS = {
    "videos": ("Видео", "videos"),
    "shorts": ("Shorts", "shorts"),
    "streams": ("Трансляции", "streams"),
    "live": ("Трансляции", "live"),
    "podcasts": ("Подкасты", "podcasts"),
    "playlists": ("Плейлисты", "playlists"),
    "community": ("Сообщество", "community"),
    "channels": ("Каналы", "channels"),
    "about": ("О канале", "about"),
}


class _NavigationParser(HTMLParser):
    def __init__(self, base_path: str):
        super().__init__(convert_charrefs=True)
        self.base_path = base_path.rstrip("/")
        self.found: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if not href:
            return
        path = urlsplit(href).path.rstrip("/")
        prefix = self.base_path + "/"
        if not path.startswith(prefix):
            return
        suffix = path[len(prefix):]
        if "/" in suffix or suffix not in TABS:
            return
        key = "streams" if suffix == "live" else suffix
        if key not in self.found:
            self.found.append(key)


def discover_tabs(url: str) -> list[tuple[str, str, str]]:
    """Read only channel-navigation links from public HTML; do not crawl page content."""
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; ytbd metadata collector)"},
    )
    with urlopen(request, timeout=20) as response:
        html = response.read().decode("utf-8", errors="replace")
    parser = _NavigationParser(urlsplit(url).path)
    parser.feed(html)

    # YouTube often serializes navigation endpoints inside ytInitialData rather
    # than emitting ordinary <a href="..."> elements in the initial HTML.
    # Inspect only exact paths for this channel and known tab suffixes.
    normalized_html = html.replace("\\/", "/")
    tab_pattern = re.compile(
        re.escape(parser.base_path)
        + r"/(videos|shorts|streams|live|podcasts|playlists|community|channels|about)"
        + r"(?=[/?#\"'\\])"
    )
    for match in tab_pattern.finditer(normalized_html):
        suffix = match.group(1)
        key = "streams" if suffix == "live" else suffix
        if key not in parser.found:
            parser.found.append(key)

    if not parser.found:
        raise ValueError(
            "В HTML канала не найдены распознаваемые вкладки навигации; "
            "возможно, YouTube вернул страницу согласия, блокировку или изменил формат."
        )
    return [(key, TABS[key][0], TABS[key][1]) for key in parser.found]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


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


def read_channel_urls(path: Path) -> list[str]:
    urls: list[str] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        try:
            url = normalize_channel_url(value)
        except ValueError as exc:
            raise ValueError(f"Строка {number}: {exc}") from exc
        if url not in urls:
            urls.append(url)
    return urls


def folder_name(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    last = path.rsplit("/", 1)[-1].lstrip("@")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", last).strip(".-_")
    if not slug:
        raise ValueError(f"Не удалось определить имя каталога для {url}")
    return slug[:80]


def build_command(url: str) -> list[str]:
    # Only metadata and flat lists: no video files, thumbnails, subtitles, or comments.
    return [
        "yt-dlp", "--ignore-errors", "--skip-download", "--flat-playlist",
        "--dump-single-json", url,
    ]


def fetch_json(url: str) -> tuple[dict | None, str | None, str]:
    result = subprocess.run(
        build_command(url), capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )
    diagnostic = result.stderr.strip()
    if not result.stdout.strip():
        return None, diagnostic or f"yt-dlp не вернул данные (код {result.returncode}).", diagnostic
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return None, f"Некорректный JSON: {exc}", diagnostic
    if not isinstance(payload, dict):
        return None, "Ожидался JSON-объект.", diagnostic
    if result.returncode != 0:
        # A partial response must not replace the last accepted snapshot.
        return None, diagnostic or f"yt-dlp завершился с кодом {result.returncode}.", diagnostic
    return payload, None, diagnostic


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json_if_changed(path: Path, payload) -> bool:
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == encoded:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(path)
    return True


def save_raw_snapshot(raw_dir: Path, name: str, payload: dict) -> None:
    """Keep the latest successful response and a content-addressed history copy."""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    write_json_if_changed(raw_dir / f"{name}.json", payload)
    write_json_if_changed(raw_dir / "history" / name / f"{digest}.json", payload)


def item_key(item: dict) -> str | None:
    value = item.get("id") or item.get("url") or item.get("webpage_url")
    return str(value) if value else None


def prepare_items(data: dict) -> list[dict]:
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("В ответе отсутствует корректный список entries.")
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = item_key(entry)
        if not key:
            continue
        item = dict(entry)
        item["id"] = str(item.get("id") or key)
        item["title"] = str(item.get("title") or item["id"])
        url = item.get("webpage_url")
        if not url:
            raw_url = item.get("url")
            if isinstance(raw_url, str) and raw_url.startswith(("http://", "https://")):
                url = raw_url
            elif item.get("id"):
                url = f"https://www.youtube.com/watch?v={item['id']}"
        item["display_url"] = url or ""
        result.append(item)
    return result


def merge_archive(previous: dict, incoming: list[dict], tab: str, checked_at: str) -> dict:
    old_items = previous.get("items", []) if isinstance(previous, dict) else []
    by_key: dict[str, dict] = {}
    order: list[str] = []
    for item in old_items if isinstance(old_items, list) else []:
        if isinstance(item, dict) and item_key(item):
            key = item_key(item)
            if key not in by_key:
                order.append(key)
                by_key[key] = item
    current_order = []
    for item in incoming:
        key = item_key(item)
        if not key:
            continue
        current_order.append(key)
        if key in by_key:
            by_key[key] = {**by_key[key], **item}
        else:
            by_key[key] = item
    # Show currently listed items first, then retain entries missing from this scan.
    merged_order = list(dict.fromkeys(current_order + order))
    items = [by_key[key] for key in merged_order]
    current_count = len(incoming)
    previous_items = previous.get("items", []) if isinstance(previous, dict) else []
    previous_current_count = previous.get("current_count") if isinstance(previous, dict) else None
    changed = items != previous_items or current_count != previous_current_count
    return {
        "tab": tab,
        "updated_at": checked_at if changed or not previous else previous.get("updated_at", checked_at),
        "current_count": current_count,
        "archive_count": len(items),
        "items": items,
    }


def make_sections(channel_dir: Path, active_tabs: list[tuple[str, str, str]],
                  failed_tabs: set[str] | None = None) -> list[dict]:
    sections = []
    failed_tabs = failed_tabs or set()
    for key, title, _suffix in active_tabs:
        archive = read_json(channel_dir / "archive" / f"{key}.json", {})
        items = archive.get("items", []) if isinstance(archive, dict) else []
        sections.append({
            "key": key,
            "title": title,
            "items": items if isinstance(items, list) else [],
            "current_count": archive.get("current_count", 0) if isinstance(archive, dict) else 0,
            "archive_count": len(items) if isinstance(items, list) else 0,
            "collection_error": key in failed_tabs,
        })
    return sections


def process_channel(url: str, template_name: str, templates_dir: Path,
                    data_root: Path, output_root: Path) -> tuple[bool, list[str]]:
    handle = folder_name(url)
    channel_dir = data_root / handle
    raw_dir = channel_dir / "raw"
    archive_dir = channel_dir / "archive"
    raw_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    checked_at = utc_now()
    errors: list[str] = []
    failed_tabs: set[str] = set()

    channel_data, error, diagnostic = fetch_json(url)
    if channel_data is not None:
        write_json_if_changed(channel_dir / "channel.json", channel_data)
        save_raw_snapshot(raw_dir, "channel", channel_data)
        channel_error_log = channel_dir / "logs" / "channel.txt"
        if channel_error_log.exists():
            channel_error_log.unlink()
    else:
        errors.append(f"channel: {error}")
        if diagnostic:
            write_json_if_changed(channel_dir / "logs" / "channel.txt", diagnostic + "\n")

    navigation_path = channel_dir / "tabs.json"
    try:
        active_tabs = discover_tabs(url)
        write_json_if_changed(navigation_path, [
            {"key": key, "title": title, "suffix": suffix}
            for key, title, suffix in active_tabs
        ])
    except (OSError, ValueError) as exc:
        errors.append(f"navigation: {exc}")
        previous_tabs = read_json(navigation_path, [])
        if isinstance(previous_tabs, list) and previous_tabs:
            active_tabs = [
                (entry["key"], entry["title"], entry["suffix"])
                for entry in previous_tabs
                if isinstance(entry, dict)
                and entry.get("key") in TABS
                and all(entry.get(field) for field in ("title", "suffix"))
            ]
        else:
            # Do not invent tabs when navigation has never been discovered.
            active_tabs = []

    for key, _title, suffix in active_tabs:
        source_url = url + "/" + suffix
        payload, error, diagnostic = fetch_json(source_url)
        if payload is None:
            failed_tabs.add(key)
            errors.append(f"{key}: {error}")
            if diagnostic:
                write_json_if_changed(channel_dir / "logs" / f"{key}.txt", diagnostic + "\n")
            continue
        try:
            incoming = prepare_items(payload)
        except ValueError as exc:
            failed_tabs.add(key)
            errors.append(f"{key}: {exc}")
            continue

        # Keep the latest successful raw response, but do not touch it on a failed request.
        save_raw_snapshot(raw_dir, key, payload)
        previous = read_json(archive_dir / f"{key}.json", {})
        merged = merge_archive(previous, incoming, key, checked_at)
        write_json_if_changed(archive_dir / f"{key}.json", merged)
        # A successful check supersedes an old error log.
        error_log = channel_dir / "logs" / f"{key}.txt"
        if error_log.exists():
            error_log.unlink()

    if channel_data is None and not any((archive_dir / f"{key}.json").exists() for key, _title, _suffix in active_tabs):
        status_ok = False
    else:
        status_ok = True

    status = {
        "channel_url": url,
        "checked_at": checked_at,
        "channel_status": "ok" if channel_data is not None else "error",
        "tabs": {},
        "errors": errors,
    }
    for key, _title, _suffix in active_tabs:
        raw_path = raw_dir / f"{key}.json"
        archive = read_json(archive_dir / f"{key}.json", {})
        status["tabs"][key] = {
            "status": "ok" if raw_path.exists() and key not in failed_tabs else "error-or-not-yet-collected",
            "current_count": archive.get("current_count", 0) if isinstance(archive, dict) else 0,
            "archive_count": archive.get("archive_count", 0) if isinstance(archive, dict) else 0,
        }
    write_json_if_changed(channel_dir / "status.json", status)

    channel_data = read_json(channel_dir / "channel.json", {})
    title = str(channel_data.get("title") or channel_data.get("channel") or handle)
    channel_id = str(channel_data.get("channel_id") or channel_data.get("id") or "")
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(enabled_extensions=("html", "htm", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)
    rendered = template.render(
        title=title,
        channel_url=url,
        channel_id=channel_id,
        checked_at=checked_at,
        sections=make_sections(
            channel_dir,
            active_tabs,
            failed_tabs,
        ),
        errors=errors,
        template_name=template_name,
    )
    output_path = output_root / handle / (Path(template_name).stem + ".md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not output_path.exists() or output_path.read_text(encoding="utf-8") != rendered:
        output_path.write_text(rendered, encoding="utf-8")
    print(f"{'УСПЕХ' if not errors else 'ЧАСТИЧНО'}: {url} -> {output_path}; ошибок: {len(errors)}")
    return status_ok, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Обновить YouTube-архив и сформировать Markdown из шаблона.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Файл со списком URL каналов")
    parser.add_argument("--template", default="outline.md", help="Имя Markdown-шаблона из templates/")
    parser.add_argument("--templates", type=Path, default=DEFAULT_TEMPLATES, help="Каталог Markdown-шаблонов")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, help="Каталог сырых данных и архива")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Каталог Markdown-результатов")
    args = parser.parse_args(argv)

    if shutil.which("yt-dlp") is None:
        print("ОШИБКА: yt-dlp не установлен.", file=sys.stderr)
        return 2
    try:
        urls = read_channel_urls(args.input)
        if not urls:
            raise ValueError("В файле не найдено ни одного URL канала.")
        if not (args.templates / args.template).is_file():
            raise ValueError(f"Шаблон не найден: {args.templates / args.template}")
    except (OSError, ValueError) as exc:
        print(f"ОШИБКА настроек: {exc}", file=sys.stderr)
        return 2

    for url in urls:
        try:
            process_channel(url, args.template, args.templates, args.data, args.output)
        except (OSError, ValueError, RuntimeError) as exc:
            # Isolate failures: one channel must not stop the rest.
            print(f"ОШИБКА {url}: {exc}", file=sys.stderr)
    print(f"Проверено каналов: {len(urls)}. Подробности и частичные ошибки находятся в status.json.")
    # Network failures are recorded as data; do not prevent committing other successful results.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
