# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.report.youtube_interactions.youtube_interactions import execute


class TestYoutubeInteractions(ERPNextTestSuite):
	def test_zero_view_video_is_listed(self):
		"""The original report filtered `WHERE view_count is not null`. The conversion keeps that exact
		semantics with `.where(video.view_count.isnotnull())` (IS NOT NULL), NOT a `<> 0` test, so a
		video with exactly 0 views is still reported. This guards against a regression to `!= 0`
		(which would silently drop 0-view videos) and confirms the filter renders identically on both
		engines."""
		frappe.db.set_single_value("Video Settings", "enable_youtube_tracking", 1)

		for title, views in (("_Test Zero Views Video", 0.0), ("_Test Ten Views Video", 10.0)):
			if frappe.db.exists("Video", title):
				frappe.delete_doc("Video", title, force=True)
			frappe.get_doc(
				{
					"doctype": "Video",
					"title": title,
					"provider": "Vimeo",  # skips the YouTube API call in validate()
					"url": f"https://vimeo.com/{int(views)}",
					"description": title,
					"publish_date": "2024-01-15",
					"view_count": views,
				}
			).insert()

		_columns, data, *_rest = execute(frappe._dict({"from_date": "2024-01-01", "to_date": "2024-12-31"}))
		titles = {row.get("title") for row in data}
		self.assertIn("_Test Ten Views Video", titles)
		# a real, freshly-synced video with 0 views must still be reported
		self.assertIn("_Test Zero Views Video", titles)
