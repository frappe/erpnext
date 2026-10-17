# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from unittest.mock import patch

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestVideoSettings(ERPNextTestSuite):
	def test_tracking_needs_api_key_and_frequency(self):
		for values in ({"api_key": None, "frequency": "1 hr"}, {"api_key": "test-key", "frequency": None}):
			settings = frappe.get_doc("Video Settings")
			settings.update({"enable_youtube_tracking": 1, **values})
			with patch("erpnext.utilities.doctype.video_settings.video_settings.Api"):
				self.assertRaises(frappe.ValidationError, settings.save)

	def test_video_saves_when_the_youtube_client_fails(self):
		frappe.db.set_single_value("Video Settings", {"enable_youtube_tracking": 1, "api_key": None})
		video = frappe.get_doc(
			{
				"doctype": "Video",
				"title": "Test Video Without API Key",
				"provider": "YouTube",
				"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
				"description": "Test",
			}
		)
		with patch.object(video, "log_error") as log_error:
			video.insert()
		log_error.assert_called_once()
