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

try:
    from scripts.media import download_video_subtitles, download_video_thumbnail
except ModuleNotFoundError:
    from media import download_video_subtitles, download_video_thumbnail

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
        key = suffix
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
        + r"/(videos|shorts|streams|podcasts|playlists|community|channels|about)"
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


def build_command(url: str, playlist_items: int = 0) -> list[str]:
    # Channel/tab scan: metadata only and flat entries. Optional playlist preview avoids
    # expanding huge playlists during a bounded real-data test.
    command = [
        "yt-dlp", "--ignore-errors", "--skip-download", "--flat-playlist",
        "--dump-single-json",
    ]
    if playlist_items > 0:
        command.extend(["--playlist-items", f"1-{playlist_items}"])
    command.append(url)
    return command


def fetch_json(url: str, playlist_items: int = 0) -> tuple[dict | None, str | None, str]:
    result = subprocess.run(
        build_command(url, playlist_items), capture_output=True, text=True,
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




def fetch_video_details(
    url: str,
    media_dir: Path | None = None,
    cookies_file: Path | None = None,
    cookies_from_browser: str | None = None,
) -> tuple[dict | None, str | None, str]:
    """Fetch metadata only; media downloads are handled by scripts.media."""
    command = [
        "yt-dlp", "--skip-download", "--no-playlist", "--dump-json",
    ]
    if cookies_file is not None:
        command.extend(["--cookies", str(cookies_file)])
    elif cookies_from_browser:
        command.extend(["--cookies-from-browser", cookies_from_browser])
    command.append(url)
    try:
        result = subprocess.run(
            command, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False, timeout=120,
        )
    except subprocess.TimeoutExpired:
        return None, "yt-dlp не завершился за 120 секунд.", ""
    diagnostic = result.stderr.strip()
    if not result.stdout.strip():
        return None, diagnostic or f"yt-dlp не вернул метаданные (код {result.returncode}).", diagnostic
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return None, f"Некорректный JSON видео: {exc}", diagnostic
    if payload is None:
        return None, "yt-dlp вернул null; это бывает у предстоящих трансляций или видео, недоступных экстрактору.", diagnostic
    if not isinstance(payload, dict):
        return None, f"yt-dlp вернул JSON типа {type(payload).__name__}: {payload!r}.", diagnostic
    if not payload.get("id"):
        keys = ", ".join(sorted(str(key) for key in payload)[:20])
        kind = payload.get("_type", "")
        return None, f"yt-dlp вернул объект без ID видео (type={kind!r}; keys={keys}).", diagnostic
    if result.returncode != 0:
        return None, diagnostic or f"yt-dlp завершился с кодом {result.returncode}.", diagnostic
    return payload, None, diagnostic


def video_folder_name(metadata: dict) -> str:
    timestamp = metadata.get("release_timestamp") or metadata.get("timestamp")
    if isinstance(timestamp, (int, float)):
        date_prefix = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y%m%d-%H%M")
    else:
        date_value = str(metadata.get("release_date") or metadata.get("upload_date") or "")
        date_prefix = f"{date_value[:8]}-0000" if re.fullmatch(r"\d{8}", date_value[:8]) else "00000000-0000"
    title = str(metadata.get("title") or metadata.get("id") or "video")
    slug = re.sub(r"[^\w.-]+", "-", title, flags=re.UNICODE).strip("._-")[:100].strip("._-")
    return f"{date_prefix}-{slug or metadata.get('id', 'video')}"


def subtitle_to_text(source: Path, destination: Path) -> None:
    """Convert an SRT/VTT subtitle file to readable plain text without timestamps."""
    lines = []
    for line in source.read_text(encoding="utf-8-sig", errors="replace").replace("\r", "").splitlines():
        value = line.strip()
        if not value or value == "WEBVTT" or re.fullmatch(r"\d+", value):
            continue
        if "-->" in value or re.match(r"^(NOTE|STYLE|REGION)\b", value):
            continue
        value = re.sub(r"<[^>]+>", "", value)
        value = re.sub(r"\{\\[^}]+\}", "", value).strip()
        if value:
            lines.append(value)
    if lines:
        destination.write_text("\n".join(lines) + "\n", encoding="utf-8")




def download_channel_images(channel_data: dict, channel_output_dir: Path) -> dict[str, str]:
    """Save the largest available channel banner and profile image from yt-dlp metadata."""
    thumbnails = channel_data.get("thumbnails", [])
    if not isinstance(thumbnails, list):
        return {}
    candidates = [item for item in thumbnails if isinstance(item, dict) and item.get("url")]
    if not candidates:
        return {}

    def dimensions(item: dict) -> tuple[int, int]:
        return int(item.get("width") or 0), int(item.get("height") or 0)

    banner_candidates = [
        item for item in candidates
        if "banner" in str(item.get("id", "")).lower()
        or (dimensions(item)[1] > 0 and dimensions(item)[0] / dimensions(item)[1] > 2.5)
    ]
    profile_candidates = [
        item for item in candidates
        if "avatar" in str(item.get("id", "")).lower()
        or (dimensions(item)[1] > 0 and 0.8 <= dimensions(item)[0] / dimensions(item)[1] <= 1.2)
    ]
    selected = {}
    if banner_candidates:
        selected["banner"] = max(banner_candidates, key=lambda item: dimensions(item)[0])
    if profile_candidates:
        selected["profile"] = max(profile_candidates, key=lambda item: dimensions(item)[0])

    result = {}
    destination = channel_output_dir / "media" / "channels"
    for name, item in selected.items():
        url = str(item["url"])
        extension = Path(urlsplit(url).path).suffix.lower()
        if extension not in {".jpg", ".jpeg", ".png", ".webp"}:
            extension = ".jpg"
        path = destination / f"{name}{extension}"
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ytbd metadata collector)"})
            with urlopen(request, timeout=20) as response:
                payload = response.read()
            if payload:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
                result[name] = path.relative_to(channel_output_dir).as_posix()
        except OSError:
            continue
    return result


def collect_video_details(
    channel_dir: Path,
    channel_output_dir: Path,
    active_tabs: list[tuple[str, str, str]],
    detail_limit: int,
    download_media: bool,
    cookies_file: Path | None = None,
    cookies_from_browser: str | None = None,
) -> tuple[dict[str, dict], list[str]]:
    """Enrich flat archive records with full video JSON and return local-file links by video ID."""
    video_tabs = {"videos", "shorts", "streams", "podcasts"}
    archives: dict[str, dict] = {}
    references: dict[str, list[dict]] = {}
    errors: list[str] = []
    for key, _title, _suffix in active_tabs:
        if key not in video_tabs and key != "playlists":
            continue
        archive = read_json(channel_dir / "archive" / f"{key}.json", {})
        if not isinstance(archive, dict) or not isinstance(archive.get("items"), list):
            continue
        archives[key] = archive
        for item in archive["items"]:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            if key == "playlists":
                playlist_id = str(item["id"])
                playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
                playlist_data, playlist_error, playlist_diagnostic = fetch_json(
                    playlist_url, playlist_items=detail_limit
                )
                if playlist_data is None:
                    errors.append(f"playlist {playlist_id}: {playlist_error}")
                    if playlist_diagnostic:
                        log_path = channel_dir / "logs" / "playlist-details.txt"
                        log_path.parent.mkdir(parents=True, exist_ok=True)
                        log_path.write_text(playlist_diagnostic + "\n", encoding="utf-8")
                    continue
                save_raw_snapshot(channel_dir / "raw" / "playlist-details", playlist_id, playlist_data)
                item.update(playlist_data)
                entries = playlist_data.get("entries", [])
                item["entries"] = entries if isinstance(entries, list) else []
                for entry in item["entries"]:
                    if isinstance(entry, dict) and entry.get("id"):
                        references.setdefault(str(entry["id"]), []).append(entry)
            elif key in video_tabs:
                references.setdefault(str(item["id"]), []).append(item)

    local_root = channel_output_dir / "media" / "videos"
    details_root = channel_dir / "raw" / "video-details"
    local_thumbnails: dict[str, str] = {}
    local_subtitles: dict[str, list[str]] = {}
    media_ids = list(references)[:detail_limit] if detail_limit else list(references)
    if download_media:
        for video_id in media_ids:
            source_item = references[video_id][0]
            candidate_url = str(source_item.get("display_url") or source_item.get("webpage_url") or "")
            if "youtube.com/watch?" not in candidate_url and "youtu.be/" not in candidate_url:
                candidate_url = f"https://www.youtube.com/watch?v={video_id}"
            thumbnail_path, thumbnail_error = download_video_thumbnail(video_id, source_item, channel_output_dir)
            if thumbnail_path:
                local_thumbnails[video_id] = thumbnail_path
            if thumbnail_error:
                errors.append(f"thumbnail {video_id}: {thumbnail_error}")
            subtitle_dir = channel_output_dir / "media" / "subtitles" / video_id
            subtitle_files, subtitle_error, subtitle_diagnostic = download_video_subtitles(candidate_url, subtitle_dir, cookies_file, cookies_from_browser)
            for subtitle in subtitle_files:
                subtitle_to_text(subtitle, subtitle.with_suffix(".txt"))
            if subtitle_files:
                first_text = subtitle_files[0].with_suffix(".txt")
                if first_text.exists():
                    (subtitle_dir / "transcript.txt").write_text(first_text.read_text(encoding="utf-8"), encoding="utf-8")
                local_subtitles[video_id] = [path.relative_to(channel_output_dir).as_posix() for path in sorted(subtitle_dir.iterdir()) if path.is_file() and path.suffix.lower() in {".srt", ".vtt", ".txt"}]
            elif subtitle_error:
                errors.append(f"subtitles {video_id}: {subtitle_error}")
                if subtitle_diagnostic:
                    log_path = channel_dir / "logs" / "subtitle-download.txt"
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    log_path.write_text(subtitle_diagnostic + "\n", encoding="utf-8")

    attempted = 0
    for video_id, items in references.items():
        # A prior successful detail extraction remains useful if a later run is limited.
        cached = read_json(details_root / f"{video_id}.json", None)
        already_detailed = isinstance(cached, dict) and cached.get("id")
        if detail_limit and attempted >= detail_limit:
            if already_detailed:
                for item in items:
                    item.update(cached)
            continue
        attempted += 1

        source_item = items[0]
        candidate_url = str(source_item.get("display_url") or source_item.get("webpage_url") or "")
        if "youtube.com/watch?" in candidate_url or "youtu.be/" in candidate_url:
            url = candidate_url
        else:
            url = f"https://www.youtube.com/watch?v={video_id}"
        metadata, error, diagnostic = fetch_video_details(
            url, None, cookies_file=cookies_file,
            cookies_from_browser=cookies_from_browser,
        )
        if metadata is None:
            errors.append(f"video {video_id}: {error}" + (f" ({diagnostic[-500:]})" if diagnostic else ""))
            if diagnostic:
                log_path = channel_dir / "logs" / "video-details.txt"
                log_path.parent.mkdir(parents=True, exist_ok=True)
                log_path.write_text(diagnostic + "\n", encoding="utf-8")
            if already_detailed:
                metadata = cached
            else:
                continue
        save_raw_snapshot(details_root, video_id, metadata)
        for item in items:
            item.update(metadata)
        if download_media and metadata is not None:
            video_dir = local_root / video_folder_name(metadata)
            write_json_if_changed(video_dir / "meta.json", metadata)

    for key, archive in archives.items():
        write_json_if_changed(channel_dir / "archive" / f"{key}.json", archive)

    local_media: dict[str, dict] = {}
    if local_root.is_dir():
        for video_dir in sorted(path for path in local_root.iterdir() if path.is_dir()):
            metadata = read_json(video_dir / "meta.json", {})
            video_id = str(metadata.get("id") or "")
            if not video_id:
                continue
            files = sorted(path for path in video_dir.iterdir() if path.is_file())
            rel = lambda path: path.relative_to(channel_output_dir).as_posix()
            thumbnails = [rel(path) for path in files if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
            subtitles = [rel(path) for path in files if path.suffix.lower() in {".srt", ".vtt"}]
            transcripts = [rel(path) for path in files if path.name == "transcript.txt" or (path.suffix == ".txt" and path.name != "meta.json")]
            local_media[video_id] = {
                "directory": video_dir.relative_to(channel_output_dir).as_posix(),
                "metadata": rel(video_dir / "meta.json") if (video_dir / "meta.json").exists() else "",
                "thumbnails": thumbnails,
                "subtitles": subtitles,
                "transcripts": sorted(set(transcripts)),
            }
    for video_id in set(local_thumbnails) | set(local_subtitles):
        entry = local_media.setdefault(video_id, {
            "directory": "", "metadata": "", "thumbnails": [], "subtitles": [], "transcripts": []
        })
        if video_id in local_thumbnails and local_thumbnails[video_id] not in entry["thumbnails"]:
            entry["thumbnails"].append(local_thumbnails[video_id])
        for path in local_subtitles.get(video_id, []):
            target = "transcripts" if path.endswith(".txt") else "subtitles"
            if path not in entry[target]:
                entry[target].append(path)
    return local_media, errors



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
                    data_root: Path, output_root: Path, detail_limit: int = 0,
                    download_media: bool = False, cookies_file: Path | None = None,
                    cookies_from_browser: str | None = None) -> tuple[bool, list[str]]:
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

    local_media: dict[str, dict] = {}
    detail_errors: list[str] = []
    channel_data = read_json(channel_dir / "channel.json", {})
    if template_name == "full.md":
        local_media, detail_errors = collect_video_details(
            channel_dir, output_root / handle, active_tabs, detail_limit, download_media,
            cookies_file=cookies_file, cookies_from_browser=cookies_from_browser,
        )
        if download_media and isinstance(channel_data, dict):
            local_media["_channel"] = download_channel_images(channel_data, output_root / handle)
        status["errors"] = errors
        status["detail_errors"] = detail_errors
        write_json_if_changed(channel_dir / "status.json", status)
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
        channel_data=channel_data,
        local_media=local_media,
        detail_errors=detail_errors,
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
    parser.add_argument(
        "--test-detail-limit", type=int, default=0,
        help="ТЕСТ: максимум уникальных видео для подробного сбора на канал; 0 означает все видео",
    )
    parser.add_argument(
        "--download-media", action="store_true",
        help="Для подробных видео сохранять обложки, субтитры и текстовые транскрипты (без видеофайлов)",
    )
    cookies = parser.add_mutually_exclusive_group()
    cookies.add_argument("--cookies", type=Path, help="Локальный файл cookies.txt для yt-dlp; не добавляй его в Git")
    cookies.add_argument(
        "--cookies-from-browser",
        help="Локальный браузер для извлечения cookies, например firefox или chrome",
    )
    args = parser.parse_args(argv)
    if args.test_detail_limit < 0:
        print("ОШИБКА настроек: --test-detail-limit не может быть отрицательным.", file=sys.stderr)
        return 2

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
            process_channel(
                url, args.template, args.templates, args.data, args.output,
                detail_limit=args.test_detail_limit, download_media=args.download_media,
                cookies_file=args.cookies, cookies_from_browser=args.cookies_from_browser,
            )
        except (OSError, ValueError, RuntimeError) as exc:
            # Isolate failures: one channel must not stop the rest.
            print(f"ОШИБКА {url}: {exc}", file=sys.stderr)
    print(f"Проверено каналов: {len(urls)}. Подробности и частичные ошибки находятся в status.json.")
    # Network failures are recorded as data; do not prevent committing other successful results.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
