import tempfile
import unittest
from pathlib import Path

from scripts.process_channels import (
    folder_name,
    merge_archive,
    normalize_channel_url,
    prepare_items,
    read_channel_urls,
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


class ArchiveTests(unittest.TestCase):
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
            ]
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

    def test_write_json_if_changed_avoids_rewriting_identical_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            self.assertTrue(write_json_if_changed(path, {"value": 1}))
            before = path.stat().st_mtime_ns
            self.assertFalse(write_json_if_changed(path, {"value": 1}))
            self.assertEqual(path.stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()
