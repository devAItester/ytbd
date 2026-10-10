import tempfile
import unittest
from pathlib import Path

from scripts.process_channels import folder_name, normalize_channel_url, read_last_urls, render_items


class ChannelInputTests(unittest.TestCase):
    def test_reads_last_nonempty_noncomment_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "channels.txt"
            path.write_text(
                "# list\nhttps://www.youtube.com/@first\n\n"
                "https://www.youtube.com/@second\nhttps://www.youtube.com/@third\n",
                encoding="utf-8",
            )
            self.assertEqual(
                read_last_urls(path, 2),
                [
                    "https://www.youtube.com/@second",
                    "https://www.youtube.com/@third",
                ],
            )

    def test_rejects_non_youtube_address(self):
        with self.assertRaises(ValueError):
            normalize_channel_url("https://example.com/@someone")

    def test_rejects_video_url(self):
        with self.assertRaises(ValueError):
            normalize_channel_url("https://www.youtube.com/watch?v=abc")

    def test_channel_folder_name_uses_handle(self):
        self.assertEqual(folder_name("https://www.youtube.com/@AsForJS"), "AsForJS")

    def test_renders_entries(self):
        rendered = render_items({
            "entries": [
                {"id": "abc123", "title": "Example video"},
            ]
        })
        self.assertIn("Example video", rendered)
        self.assertIn("youtube.com/watch?v=abc123", rendered)


if __name__ == "__main__":
    unittest.main()
