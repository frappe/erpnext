# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestVideoSettings(ERPNextTestSuite):
	def test_removed_frequency_is_saved_as_hourly(self):
		frappe.db.set_single_value("Video Settings", "frequency", "30 mins")
		settings = frappe.get_doc("Video Settings")
		settings.enable_youtube_tracking = 0
		settings.save()
		self.assertEqual(frappe.db.get_single_value("Video Settings", "frequency"), "1 hr")
