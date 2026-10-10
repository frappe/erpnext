# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestIncomingCallSettings(ERPNextTestSuite):
	def setUp(self):
		self.agent_group = "_Test Incoming Call Agents"
		if not frappe.db.exists("Employee Group", self.agent_group):
			frappe.get_doc({"doctype": "Employee Group", "employee_group_name": self.agent_group}).insert()

	def test_saved_settings_can_be_saved_again(self):
		settings = make_settings(
			[("09:00:00", "13:00:00", self.agent_group), ("14:00:00", "18:00:00", self.agent_group)]
		)

		settings = frappe.get_doc("Incoming Call Settings", settings.name)
		settings.greeting_message = "Hello"
		settings.save()

		self.assertEqual(
			frappe.db.get_value("Incoming Call Settings", settings.name, "greeting_message"), "Hello"
		)

	def test_schedule_times_in_other_formats_and_overnight_slots(self):
		make_settings([("09:00", "17:00", self.agent_group), ("17:00:00.000000", "21:00", self.agent_group)])

		with self.assertRaisesRegex(frappe.ValidationError, "overnight"):
			make_settings([("22:00:00", "06:00:00", self.agent_group)])


def make_settings(slots: list[tuple[str, str, str]]):
	return frappe.get_doc(
		{
			"doctype": "Incoming Call Settings",
			"__newname": frappe.generate_hash(length=10),
			"call_handling_schedule": [
				{"day_of_week": "Monday", "from_time": from_time, "to_time": to_time, "agent_group": group}
				for from_time, to_time, group in slots
			],
		}
	).insert()
