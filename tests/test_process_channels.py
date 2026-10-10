import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jinja2 import Environment, FileSystemLoader, select_autoescape

from scripts.process_channels import (
    discover_tabs,
    folder_name,
    merge_archive,
    normalize_channel_url,
    prepare_items,
    process_channel,
    read_channel_urls,
    subtitle_to_text,
    video_folder_name,
    write_json_if_changed,
)


class ChannelInputTests(unittest.TestCase):
    def test_normalizes_channel_url(self):
        self.assertEqual(
            normalize_channel_url("youtube.com/@AsForJS/"),
            "https://www.youtube.com/@AsForJS",
        )

    def test_rejects_non_youtube_and_video_urls(self):
        with self.assertRaises(ValueError):
            normalize_channel_url("https://example.com/@someone")
        with self.assertRaises(ValueError):
            normalize_channel_url("https://www.youtube.com/watch?v=abc")

    def test_reads_all_unique_noncomment_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "channels.txt"
            path.write_text(
                "# channels\nhttps://www.youtube.com/@first\n\n"
                "https://www.youtube.com/@second\nhttps://www.youtube.com/@first\n",
                encoding="utf-8",
            )
            self.assertEqual(
                read_channel_urls(path),
                [
                    "https://www.youtube.com/@first",
                    "https://www.youtube.com/@second",
                ],
            )

    def test_reports_invalid_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "channels.txt"
            path.write_text("# comment\nhttps://example.com/nope\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Строка 2"):
                read_channel_urls(path)

    def test_folder_name_uses_handle(self):
        self.assertEqual(folder_name("https://www.youtube.com/@AsForJS"), "AsForJS")

    def test_discovers_only_channel_navigation_links(self):
        html = b"""
        <a href="/@Example/videos">Videos</a>
        <a href="/@Example/shorts">Shorts</a>
        <a href="/@Example/playlists">Playlists</a>
        <a href="/@Example/watch?v=not-a-tab">Video content</a>
        <a href="/@Other/videos">Other channel</a>
        """
        with patch("scripts.process_channels.urlopen", return_value=io.BytesIO(html)):
            tabs = discover_tabs("https://www.youtube.com/@Example")
        self.assertEqual([tab[0] for tab in tabs], ["videos", "shorts", "playlists"])

    def test_discovers_tabs_embedded_in_initial_data(self):
        html = b'<script>var ytInitialData = {"url":"/@Example/videos","other":"/@Example/shorts"};</script>'
        with patch("scripts.process_channels.urlopen", return_value=io.BytesIO(html)):
            tabs = discover_tabs("https://www.youtube.com/@Example")
        self.assertEqual([tab[0] for tab in tabs], ["videos", "shorts"])


class TemplateTests(unittest.TestCase):
    def test_all_repository_templates_render_without_network(self):
        templates_dir = Path(__file__).resolve().parents[1] / "templates"
        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html", "htm", "xml")),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        context = {
            "title": "Test <channel>",
            "channel_url": "https://www.youtube.com/@Test",
            "channel_id": "UC1",
            "checked_at": "2026-10-10 12:00:00 UTC",
            "template_name": "outline.md",
            "channel_data": {"id": "UC1", "title": "Test <channel>", "_type": "channel"},
            "local_media": {},
            "errors": ["temporary <error>"],
            "sections": [{
                "key": "videos",
                "title": "Видео",
                "current_count": 1,
                "archive_count": 1,
                "items": [{
                    "id": "video1",
                    "title": "Title <script>alert(1)</script>",
                    "display_url": "https://www.youtube.com/watch?v=video1",
                    "upload_date": "20261010",
                    "release_date": "",
                    "duration": 120,
                    "description": "Description <unsafe>",
                }],
            }],
        }
        for name in ("outline.md", "archive.md", "index.md", "full.md"):
            rendered = env.get_template(name).render(**context)
            self.assertIn("Test &lt;channel&gt;", rendered)
            self.assertIn("Title &lt;script&gt;", rendered)
            self.assertIn("temporary &lt;error&gt;", rendered)
            self.assertIn("video1", rendered)
        full = env.get_template("full.md").render(**context)
        self.assertIn("Метаданные канала", full)
        self.assertIn('"_type": "channel"', full)
        self.assertIn('"id": "video1"', full)
        self.assertIn("Локальные файлы", full)
        self.assertIn("<details>", env.get_template("outline.md").render(**context))
        self.assertIn("<details>", env.get_template("archive.md").render(**context))
        outline = env.get_template("outline.md").render(**context)
        archive = env.get_template("archive.md").render(**context)
        self.assertIn("- **ID:** UC1\n- **Последняя проверка:**", outline)
        self.assertIn("- **ID:** UC1\n- **Последняя проверка:**", archive)


class ArchiveTests(unittest.TestCase):
    def test_video_folder_name_uses_utc_timestamp_and_title(self):
        from datetime import datetime, timezone

        timestamp = int(datetime(2026, 3, 8, 14, 25, tzinfo=timezone.utc).timestamp())
        self.assertEqual(
            video_folder_name({"id": "abc", "title": "Название видео", "timestamp": timestamp}),
            "20260308-1425-Название-видео",
        )

    def test_subtitle_to_text_removes_timestamps_and_markup(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "captions.srt"
            target = Path(tmp) / "transcript.txt"
            source.write_text(
                "1\n00:00:01,000 --> 00:00:02,000\n<v Speaker>Привет</v>\n\n"
                "2\n00:00:03,000 --> 00:00:04,000\nМир\n",
                encoding="utf-8",
            )
            subtitle_to_text(source, target)
            self.assertEqual(target.read_text(encoding="utf-8"), "Привет\nМир\n")

    def test_prepare_items_adds_watch_url(self):
        items = prepare_items({"entries": [{"id": "abc123", "title": "Example video"}]})
        self.assertEqual(items[0]["display_url"], "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(items[0]["title"], "Example video")

    def test_prepare_items_rejects_missing_entries(self):
        with self.assertRaises(ValueError):
            prepare_items({"title": "Channel"})

    def test_merge_archive_updates_and_preserves_missing_items(self):
        previous = {
            "items": [
                {"id": "old", "title": "Old title"},
                {"id": "changed", "title": "Before"},
            ],
            "current_count": 2,
            "updated_at": "yesterday",
        }
        incoming = [
            {"id": "changed", "title": "After"},
            {"id": "new", "title": "New item"},
        ]
        merged = merge_archive(previous, incoming, "videos", "2026-10-10 12:00:00 UTC")
        by_id = {item["id"]: item for item in merged["items"]}
        self.assertEqual(merged["current_count"], 2)
        self.assertEqual(merged["archive_count"], 3)
        self.assertEqual(by_id["changed"]["title"], "After")
        self.assertEqual(by_id["old"]["title"], "Old title")
        self.assertEqual([item["id"] for item in merged["items"]], ["changed", "new", "old"])
        self.assertNotEqual(merged["updated_at"], "yesterday")

    def test_unchanged_archive_keeps_its_timestamp(self):
        previous = {
            "items": [{"id": "same", "title": "Same"}],
            "current_count": 1,
            "updated_at": "previous timestamp",
        }
        merged = merge_archive(previous, [{"id": "same", "title": "Same"}], "videos", "new timestamp")
        self.assertEqual(merged["updated_at"], "previous timestamp")

    def test_write_json_if_changed_avoids_rewriting_identical_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            self.assertTrue(write_json_if_changed(path, {"value": 1}))
            before = path.stat().st_mtime_ns
            self.assertFalse(write_json_if_changed(path, {"value": 1}))
            self.assertEqual(path.stat().st_mtime_ns, before)

    def test_markdown_template_renders_and_failed_tab_keeps_previous_archive(self):
        url = "https://www.youtube.com/@Example"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            templates = root / "templates"
            templates.mkdir()
            (templates / "outline.md").write_text(
                "<h1>{{ title }}</h1>{% for section in sections %}"
                "<details><summary>{{ section.title }}</summary>{% if section.collection_error %}сохранённый архив может быть устаревшим{% endif %}"
                "{% for item in section[\"items\"] %}<a href=\"{{ item.display_url }}\">{{ item.title }}</a>"
                "{% endfor %}</details>{% endfor %}"
                "{% for error in errors %}<p>{{ error }}</p>{% endfor %}",
                encoding="utf-8",
            )
            success_responses = [
                ({"title": "Example channel", "id": "UC1"}, None, ""),
                ({"entries": [{"id": "video1", "title": "Video one"}]}, None, ""),
                ({"entries": [{"id": "stream1", "title": "Stream one"}]}, None, ""),
                ({"entries": [{"id": "podcast1", "title": "Podcast one"}]}, None, ""),
                ({"entries": [{"id": "playlist1", "title": "Playlist one"}]}, None, ""),
            ]
            discovered_tabs = [
                ("videos", "Видео", "videos"),
                ("streams", "Трансляции", "streams"),
                ("podcasts", "Подкасты", "podcasts"),
                ("playlists", "Плейлисты", "playlists"),
            ]
            with patch("scripts.process_channels.discover_tabs", return_value=discovered_tabs), patch(
                "scripts.process_channels.fetch_json", side_effect=success_responses
            ):
                ok, errors = process_channel(
                    url, "outline.md", templates, root / "data/channels", root / "data/output"
                )
            self.assertTrue(ok)
            self.assertEqual(errors, [])
            channel_dir = root / "data/channels/Example"
            old_archive = (channel_dir / "archive/streams.json").read_text(encoding="utf-8")
            output_path = root / "data/output/Example/outline.md"
            self.assertIn("<details>", output_path.read_text(encoding="utf-8"))
            self.assertIn("Video one", output_path.read_text(encoding="utf-8"))

            second_responses = [
                ({"title": "Example channel", "id": "UC1"}, None, ""),
                ({"entries": [{"id": "video1", "title": "Video one updated"}]}, None, ""),
                (None, "source temporarily unavailable", "source temporarily unavailable"),
                ({"entries": [{"id": "podcast1", "title": "Podcast one"}]}, None, ""),
                ({"entries": [{"id": "playlist1", "title": "Playlist one"}]}, None, ""),
            ]
            with patch("scripts.process_channels.discover_tabs", return_value=discovered_tabs), patch(
                "scripts.process_channels.fetch_json", side_effect=second_responses
            ):
                ok, errors = process_channel(
                    url, "outline.md", templates, root / "data/channels", root / "data/output"
                )
            self.assertTrue(ok)
            self.assertTrue(any("streams:" in error for error in errors))
            self.assertEqual(
                (channel_dir / "archive/streams.json").read_text(encoding="utf-8"),
                old_archive,
            )
            self.assertIn("source temporarily unavailable", output_path.read_text(encoding="utf-8"))
            self.assertIn("сохранённый архив может быть устаревшим", output_path.read_text(encoding="utf-8"))
            status = json.loads((channel_dir / "status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["tabs"]["streams"]["status"], "error-or-not-yet-collected")


if __name__ == "__main__":
    unittest.main()
