# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import patch

import frappe

from erpnext.tests.utils import ERPNextTestSuite
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


def make_video(title: str, url: str, provider: str = "YouTube"):
	return frappe.get_doc(
		{"doctype": "Video", "title": title, "provider": provider, "url": url, "description": "Test"}
	).insert()
