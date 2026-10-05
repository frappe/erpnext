# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from erpnext.crm.doctype.utils import get_scheduled_employees_for_popup
from erpnext.setup.doctype.employee.test_employee import make_employee
from erpnext.tests.utils import ERPNextTestSuite


class TestCommunicationMedium(ERPNextTestSuite):
	def setUp(self):
		self.day_group = make_employee_group("_Test Medium Day Group", "medium-day@example.com")
		self.fallback_group = make_employee_group("_Test Medium Fallback Group", "medium-fallback@example.com")

	def test_disabled_medium_shows_no_popup(self):
		medium = make_medium([make_slot("09:00:00", "18:00:00", self.day_group)], self.fallback_group)

		self.assertEqual(popup_users_at(medium, "10:00:00"), {"medium-day@example.com"})

		medium.db_set("disabled", 1)
		self.assertEqual(popup_users_at(medium, "10:00:00"), [])

	def test_catch_all_used_outside_timeslots(self):
		medium = make_medium([make_slot("09:00:00", "18:00:00", self.day_group)], self.fallback_group)

		self.assertEqual(popup_users_at(medium, "20:30:00"), {"medium-fallback@example.com"})

	def test_reversed_timeslot_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			make_medium([make_slot("22:00:00", "06:00:00", self.day_group)])


def make_employee_group(name: str, user: str) -> str:
	if not frappe.db.exists("Employee Group", name):
		frappe.get_doc(
			{
				"doctype": "Employee Group",
				"employee_group_name": name,
				"employee_list": [{"employee": make_employee(user, company="_Test Company")}],
			}
		).insert()
	return name


def make_slot(from_time: str, to_time: str, employee_group: str) -> dict:
	return {
		"day_of_week": "Monday",
		"from_time": from_time,
		"to_time": to_time,
		"employee_group": employee_group,
	}


def make_medium(timeslots: list[dict], catch_all: str | None = None):
	return frappe.get_doc(
		{
			"doctype": "Communication Medium",
			"__newname": frappe.generate_hash(length=10),
			"communication_medium_type": "Voice",
			"catch_all": catch_all,
			"timeslots": timeslots,
		}
	).insert()


def popup_users_at(medium, time: str) -> set | list:
	with (
		patch("frappe.utils.nowtime", return_value=time),
		patch("frappe.utils.get_weekday", return_value="Monday"),
	):
		return get_scheduled_employees_for_popup(medium.name)
