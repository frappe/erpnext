# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest
from unittest.mock import patch

import frappe

from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import (
	execute_repost_item_valuation,
	get_recipients,
	in_configured_timeslot,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestStockRepostingSettings(ERPNextTestSuite):
	def test_widened_overnight_timeslot_runs_past_midnight(self):
		settings = frappe.get_doc("Stock Reposting Settings")
		settings.update({"limit_reposting_timeslot": 1, "start_time": "22:00:00", "end_time": "06:00:00"})
		settings.limits_dont_apply_on = None
		settings.validate()

		self.assertEqual(settings.end_time, "08:00:00")
		self.assertTrue(in_configured_timeslot(settings, "23:30:00"))
		self.assertTrue(in_configured_timeslot(settings, "03:00:00"))
		self.assertTrue(in_configured_timeslot(settings, "07:30:00"))
		self.assertFalse(in_configured_timeslot(settings, "12:00:00"))

	def test_timeslot_compares_unpadded_end_time(self):
		settings = frappe._dict(
			limit_reposting_timeslot=1, start_time="22:00:00", end_time="8:0:0", limits_dont_apply_on=None
		)

		self.assertTrue(in_configured_timeslot(settings, "03:00:00"))

	def test_manual_start_outside_timeslot_is_not_reported_as_started(self):
		module = "erpnext.stock.doctype.repost_item_valuation.repost_item_valuation"
		with (
			patch(f"{module}.in_configured_timeslot", return_value=False),
			patch(
				"frappe.core.doctype.scheduled_job_type.scheduled_job_type.ScheduledJobType.enqueue"
			) as enqueue,
		):
			self.assertFalse(execute_repost_item_valuation())

		enqueue.assert_not_called()


class TestStockRepostingSettingsNotification(ERPNextTestSuite):
	def test_notify_reposting_error_to_role(self):
		role = "Notify Reposting Role"

		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)

		user = "notify_reposting_error@test.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Test",
					"language": "en",
					"time_zone": "Asia/Kolkata",
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			).insert(ignore_permissions=True)

		frappe.db.set_single_value("Stock Reposting Settings", "notify_reposting_error_to_role", "")

		users = get_recipients()
		self.assertFalse(user in users)

		frappe.db.set_single_value("Stock Reposting Settings", "notify_reposting_error_to_role", role)

		users = get_recipients()
		self.assertTrue(user in users)
