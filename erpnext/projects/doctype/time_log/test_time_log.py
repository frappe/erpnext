# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

from __future__ import unicode_literals
import frappe
import unittest

from erpnext.projects.doctype.time_log.time_log import OverlapError
from erpnext.projects.doctype.time_log.time_log import NotSubmittedError

from erpnext.manufacturing.doctype.workstation.workstation import WorkstationHolidayError
from erpnext.manufacturing.doctype.workstation.workstation import NotInWorkingHoursError

from erpnext.projects.doctype.time_log_batch.test_time_log_batch import *

class TestTimeLog(unittest.TestCase):
	def test_duplication(self):
		frappe.db.sql("delete from `tabTime Log`")

		tl1 = frappe.get_doc(frappe.copy_doc(test_records[0]))
		tl1.user = "test@example.com"
		tl1.insert()

		tl2 = frappe.get_doc(frappe.copy_doc(test_records[0]))
		tl2.user = "test@example.com"

		self.assertRaises(OverlapError, tl2.insert)

		frappe.db.sql("delete from `tabTime Log`")

	def test_production_order_status(self):
		prod_order = make_prod_order(self)

		prod_order.save()

		time_log = frappe.get_doc({
			"doctype": "Time Log",
			"time_log_for": "Manufacturing",
			"production_order": prod_order.name,
			"qty": 1,
			"from_time": "2014-12-26 00:00:00",
			"to_time": "2014-12-26 00:00:00"
		})

		self.assertRaises(NotSubmittedError, time_log.save)

	def test_time_log_on_holiday(self):
		prod_order = make_prod_order(self)
		prod_order.set_production_order_operations()
		prod_order.save()
		prod_order.submit()

		time_log = frappe.get_doc({
			"doctype": "Time Log",
			"time_log_for": "Manufacturing",
			"production_order": prod_order.name,
			"operation": prod_order.operations[0].operation,
			"operation_id": prod_order.operations[0].name,
			"qty": 1,
			"activity_type": "_Test Activity Type",
			"from_time": "2013-02-01 10:00:00",
			"to_time": "2013-02-01 20:00:00",
			"workstation": "_Test Workstation 1"
		})
		self.assertRaises(WorkstationHolidayError , time_log.save)

		time_log.update({
			"from_time": "2013-02-02 09:00:00",
			"to_time": "2013-02-02 20:00:00"
		})
		self.assertRaises(NotInWorkingHoursError , time_log.save)

		time_log.from_time= "2013-02-02 10:30:00"
		time_log.save()
		time_log.submit()
		time_log.cancel()

	def test_negative_hours(self):
		frappe.db.sql("delete from `tabTime Log`")
		test_time_log = frappe.new_doc("Time Log")
		test_time_log.activity_type = "Communication"
		test_time_log.from_time = "2013-01-01 11:00:00.000000"
		test_time_log.to_time = "2013-01-01 10:00:00.000000"
		self.assertRaises(frappe.ValidationError, test_time_log.save)
		frappe.db.sql("delete from `tabTime Log`")

def make_prod_order(self):
	return frappe.get_doc({
			"doctype":"Production Order",
			"production_item": "_Test FG Item 2",
			"bom_no": "BOM/_Test FG Item 2/001",
			"qty": 1,
			"wip_warehouse": "_Test Warehouse - _TC",
			"fg_warehouse": "_Test Warehouse 1 - _TC",
			"company": "_Test Company"
		})

test_records = frappe.get_test_records('Time Log')
test_ignore = ["Time Log Batch", "Sales Invoice"]
