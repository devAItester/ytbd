import unittest

from scripts.collect import DATA_TYPES, build_command, build_source_url, normalize_channel_url


class ChannelUrlTests(unittest.TestCase):
    def test_handle_url_is_normalized(self):
        self.assertEqual(
            normalize_channel_url("https://youtube.com/@AsForJS/"),
            "https://www.youtube.com/@AsForJS",
        )

    def test_channel_id_url_is_supported(self):
        self.assertEqual(
            normalize_channel_url("youtube.com/channel/UC123"),
            "https://www.youtube.com/channel/UC123",
        )

    def test_video_url_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_channel_url("https://www.youtube.com/watch?v=abc")

    def test_other_host_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_channel_url("https://example.com/@channel")

    def test_each_data_type_uses_channel_page(self):
        base = "https://www.youtube.com/@AsForJS"
        expected = {
            "channel": base,
            "videos": base + "/videos",
            "playlists": base + "/playlists",
            "streams": base + "/streams",
            "podcasts": base + "/podcasts",
        }
        self.assertEqual(set(DATA_TYPES), set(expected))
        for data_type, url in expected.items():
            with self.subTest(data_type=data_type):
                self.assertEqual(build_source_url(base, data_type), url)

    def test_command_does_not_use_shell(self):
        command = build_command("https://www.youtube.com/@Example/videos")
        self.assertEqual(command[0], "yt-dlp")
        self.assertIn("--dump-single-json", command)
        self.assertEqual(command[-1], "https://www.youtube.com/@Example/videos")


if __name__ == "__main__":
    unittest.main()
