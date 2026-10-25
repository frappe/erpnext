# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import patch

import frappe
from frappe.tests.classes.context_managers import freeze_time

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.doctype.video.video import (
	batch_update_youtube_data,
	get_id_from_url,
	update_youtube_data,
)


class FakeYouTubeApi:
	"""Stands in for `pyyoutube.Api`, returning the statistics in `views` per video id."""

	views: ClassVar[dict[str, int]] = {}
	fail = False

	def __init__(self, api_key: str | None = None):
		pass

	def get_video_by_id(self, video_id: str):
		if self.fail:
			raise Exception("quotaExceeded")
		return SimpleNamespace(items=[self.item(id) for id in video_id.split(",") if id in self.views])

	def item(self, video_id: str) -> SimpleNamespace:
		data = {"id": video_id, "statistics": {"viewCount": self.views[video_id]}}
		return SimpleNamespace(to_dict=lambda: data)


class TestVideo(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value("Video Settings", {"enable_youtube_tracking": 1, "api_key": "test-key"})
		FakeYouTubeApi.views = {"dQw4w9WgXcQ": 1000, "9bZkp7q1z0E": 7}
		FakeYouTubeApi.fail = False
		patcher = patch("erpnext.utilities.doctype.video.video.Api", FakeYouTubeApi)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_batch_update_sets_statistics_on_the_video(self):
		video = make_video("Test Batch Update", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
		self.assertEqual(video.view_count, 1000)

		FakeYouTubeApi.views["dQw4w9WgXcQ"] = 5000
		batch_update_youtube_data()
		self.assertEqual(frappe.db.get_value("Video", video.name, "view_count"), 5000)

	def test_batch_update_skips_videos_without_id_and_survives_api_errors(self):
		make_video("Test Vimeo Video", "https://vimeo.com/76979871", provider="Vimeo")
		video = make_video("Test YouTube Video", "https://youtu.be/dQw4w9WgXcQ")

		FakeYouTubeApi.views["dQw4w9WgXcQ"] = 5000
		batch_update_youtube_data()
		self.assertEqual(frappe.db.get_value("Video", video.name, "view_count"), 5000)

		FakeYouTubeApi.fail = True
		with patch("frappe.log_error"):
			batch_update_youtube_data()

	def test_scheduled_update_follows_the_frequency(self):
		frappe.db.set_single_value("Video Settings", {"frequency": "6 hrs", "last_youtube_update": None})
		self.assert_scheduled_updates(
			{
				"2026-01-01 06:40": True,
				"2026-01-01 11:59": False,
				"2026-01-01 12:20": True,
				"2026-01-01 12:50": False,
			}
		)

		# sites still set to the removed "30 mins" option update hourly
		frappe.db.set_single_value("Video Settings", "frequency", "30 mins")
		self.assert_scheduled_updates({"2026-01-01 13:05": True, "2026-01-01 13:35": False})

	def assert_scheduled_updates(self, expected_runs: dict[str, bool]):
		with patch("erpnext.utilities.doctype.video.video.batch_update_youtube_data") as batch_update:
			for time, should_run in expected_runs.items():
				batch_update.reset_mock()
				with freeze_time(time):
					update_youtube_data()
				self.assertEqual(batch_update.called, should_run, time)

	def test_video_id_from_url(self):
		for url in (
			"https://youtu.be/dQw4w9WgXcQ",
			"https://www.youtube.com/watch?v=dQw4w9WgXcQ",
			"https://www.youtube.com/watch?feature=share&v=dQw4w9WgXcQ",
			"https://www.youtube.com/shorts/dQw4w9WgXcQ",
			"https://www.youtube.com/live/dQw4w9WgXcQ",
			"https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
			"HTTPS://WWW.YOUTUBE.COM/watch?v=dQw4w9WgXcQ",
		):
			self.assertEqual(get_id_from_url(url), "dQw4w9WgXcQ", url)

		for url in ("https://www.youtube.com/", "https://example.com/video.mp4"):
			self.assertRaises(frappe.ValidationError, get_id_from_url, url)

	def test_changing_url_refreshes_video_id_and_statistics(self):
		video = make_video("Test URL Change", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
		video.url = "https://www.youtube.com/watch?v=9bZkp7q1z0E"
		video.save()

		self.assertEqual(video.youtube_video_id, "9bZkp7q1z0E")
		self.assertEqual(video.view_count, 7)

	def test_video_id_is_saved_with_tracking_off(self):
		frappe.db.set_single_value("Video Settings", "enable_youtube_tracking", 0)
		for title, url in (
			("Test Nocookie Embed", "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"),
			("Test Shorts", "https://www.youtube.com/shorts/9bZkp7q1z0E"),
		):
			video = make_video(title, url)
			self.assertEqual(video.youtube_video_id, url[-11:], url)
			self.assertFalse(video.view_count)

		self.assertRaises(frappe.ValidationError, make_video, "Test Bad URL", "https://www.youtube.com/")

	def test_batch_update_needs_video_settings_permission(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "test-video-website-user@example.com",
				"first_name": "Test Video",
				"user_type": "Website User",
				"send_welcome_email": 0,
			}
		).insert(ignore_if_duplicate=True)
		with self.set_user(user.name):
			self.assertRaises(frappe.PermissionError, batch_update_youtube_data)


def make_video(title: str, url: str, provider: str = "YouTube"):
	return frappe.get_doc(
		{"doctype": "Video", "title": title, "provider": provider, "url": url, "description": "Test"}
	).insert()
