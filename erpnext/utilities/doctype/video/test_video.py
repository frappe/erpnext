# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.utilities.doctype.video.video import batch_update_youtube_data


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


class TestVideo(FrappeTestCase):
	def setUp(self):
		frappe.db.set_single_value("Video Settings", {"enable_youtube_tracking": 1, "api_key": "test-key"})
		FakeYouTubeApi.views = {"dQw4w9WgXcQ": 1000, "9bZkp7q1z0E": 7}
		FakeYouTubeApi.fail = False
		patcher = patch("erpnext.utilities.doctype.video.video.Api", FakeYouTubeApi)
		patcher.start()
		self.addCleanup(patcher.stop)

	def tearDown(self):
		frappe.db.rollback()

	def test_batch_update_sets_statistics_on_the_video(self):
		video = make_video("Test Batch Update", "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
		self.assertEqual(video.view_count, 1000)

		FakeYouTubeApi.views["dQw4w9WgXcQ"] = 5000
		batch_update_youtube_data()
		self.assertEqual(frappe.db.get_value("Video", video.name, "view_count"), 5000)

	def test_video_url_must_be_a_web_link(self):
		with self.set_user(make_desk_user()):
			self.assert_video_urls()

	def assert_video_urls(self):
		for title, url in (
			("Test Vimeo Link", "https://vimeo.com/76979871"),
			("Test Drive Link", "https://drive.google.com/file/d/abc123/view"),
		):
			self.assertEqual(make_video(title, url, provider="Vimeo").url, url)

		for provider in ("Vimeo", "YouTube"):
			for url in (
				'V01X" style="animation:spinner-border 1s" onanimationstart="alert(1)',
				"javascript:alert(1)",
				'https://x" onmouseover="alert(1)',
			):
				self.assertRaises(frappe.ValidationError, make_video, "Test Bad Link", url, provider=provider)

	def test_video_without_url_asks_for_it(self):
		self.assertRaises(frappe.MandatoryError, make_video, "Test No URL", None, provider="Vimeo")


def make_video(title: str, url: str, provider: str = "YouTube"):
	return frappe.get_doc(
		{"doctype": "Video", "title": title, "provider": provider, "url": url, "description": "Test"}
	).insert()


def make_desk_user():
	return (
		frappe.get_doc(
			{
				"doctype": "User",
				"email": "test-video-desk-user@example.com",
				"first_name": "Test Video Desk",
				"send_welcome_email": 0,
				"roles": [{"role": "Stock User"}],
			}
		)
		.insert(ignore_if_duplicate=True)
		.name
	)
