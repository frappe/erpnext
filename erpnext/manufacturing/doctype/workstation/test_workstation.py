# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.manufacturing.doctype.workstation.workstation import check_if_within_operating_hours, NotInWorkingHoursError, WorkstationHolidayError

test_dependencies = ["Warehouse"]
test_records = frappe.get_test_records('Workstation')

class TestWorkstation(unittest.TestCase):

	def test_validate_timings(self):
		check_if_within_operating_hours("_Test Workstation 1", "Operation 1", "2013-02-02 11:00:00", "2013-02-02 19:00:00")
		check_if_within_operating_hours("_Test Workstation 1", "Operation 1", "2013-02-02 10:00:00", "2013-02-02 20:00:00")
		self.assertRaises(NotInWorkingHoursError, check_if_within_operating_hours,
			"_Test Workstation 1", "Operation 1", "2013-02-02 05:00:00", "2013-02-02 20:00:00")
		self.assertRaises(NotInWorkingHoursError, check_if_within_operating_hours,
			"_Test Workstation 1", "Operation 1", "2013-02-02 05:00:00", "2013-02-02 20:00:00")
		self.assertRaises(WorkstationHolidayError, check_if_within_operating_hours,
			"_Test Workstation 1", "Operation 1", "2013-02-01 10:00:00", "2013-02-02 20:00:00")

def make_workstation(**args):
	args = frappe._dict(args)

	try:
		doc = frappe.get_doc({
			"doctype": "Workstation",
			"workstation_name": args.workstation_name
		})

		doc.insert()

		return doc
	except frappe.DuplicateEntryError:
		return frappe.get_doc("Workstation", args.workstation_name)