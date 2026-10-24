# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from unittest.mock import patch

import frappe
from frappe.tests.classes.context_managers import freeze_time

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.utilities.doctype.video.video import update_youtube_data


class TestVideo(ERPNextTestSuite):
	def test_scheduled_update_follows_the_frequency(self):
		frappe.db.set_single_value(
			"Video Settings",
			{"enable_youtube_tracking": 1, "frequency": "6 hrs", "last_youtube_update": None},
		)
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
