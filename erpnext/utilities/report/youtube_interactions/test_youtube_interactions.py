# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.report.youtube_interactions.youtube_interactions import execute


class TestYoutubeInteractions(ERPNextTestSuite):
	def test_open_ended_date_range(self):
		frappe.db.set_single_value("Video Settings", "enable_youtube_tracking", 1)
		frappe.db.delete("Video", {"publish_date": [">=", "2025-03-01"]})

		for title, publish_date in (("_Test March Video", "2025-03-01"), ("_Test April Video", "2025-04-01")):
			frappe.get_doc(
				{
					"doctype": "Video",
					"title": title,
					"provider": "Vimeo",
					"url": f"https://vimeo.com/{publish_date}",
					"description": title,
					"publish_date": publish_date,
					"view_count": 10,
				}
			).insert()

		def titles(**filters) -> set[str]:
			return {row.get("title") for row in execute(frappe._dict(filters))[1]}

		self.assertEqual(titles(from_date="2025-03-01"), {"_Test March Video", "_Test April Video"})
		until_march = titles(to_date="2025-03-31")
		self.assertIn("_Test March Video", until_march)
		self.assertNotIn("_Test April Video", until_march)
		self.assertEqual(titles(from_date="2025-03-01", to_date="2025-03-31"), {"_Test March Video"})
