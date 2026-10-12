# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe

from erpnext.manufacturing.doctype.workstation.test_workstation import make_workstation
from erpnext.tests.utils import ERPNextTestSuite


class TestDowntimeEntry(ERPNextTestSuite):
	def setUp(self):
		self.workstation = make_workstation(workstation_name="_Test Downtime Workstation").name
		self.operator = frappe.db.get_value("Employee", {"status": "Active"}, "name")

	def test_overlapping_downtime_refused(self):
		make_downtime_entry(self.workstation, self.operator, "2031-01-06 13:00:00", "2031-01-06 15:00:00")

		for from_time, to_time in (
			("2031-01-06 14:00:00", "2031-01-06 15:00:00"),
			("2031-01-06 13:00:00", "2031-01-06 15:00:00"),
		):
			self.assertRaises(
				frappe.ValidationError,
				make_downtime_entry,
				self.workstation,
				self.operator,
				from_time,
				to_time,
			)

		make_downtime_entry(self.workstation, self.operator, "2031-01-06 15:00:00", "2031-01-06 16:00:00")


def make_downtime_entry(workstation, operator, from_time, to_time):
	return frappe.get_doc(
		{
			"doctype": "Downtime Entry",
			"workstation": workstation,
			"operator": operator,
			"from_time": from_time,
			"to_time": to_time,
			"stop_reason": "Machine malfunction",
		}
	).insert()
