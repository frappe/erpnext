# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, unittest

class TimeLogBatchTest(unittest.TestCase):
	def setUp(self):
		for name in frappe.db.sql_list("select name from `tabTime Log` where docstatus=1"):
			frappe.get_doc("Time Log", name).cancel()
			frappe.delete_doc("Time Log", name)

	def test_time_log_status(self):
		from erpnext.projects.doctype.time_log.test_time_log import test_records as time_log_records
		time_log = frappe.copy_doc(time_log_records[0])
		time_log.update({
			"from_time": "2013-01-02 10:00:00.000000",
			"to_time": "2013-01-02 11:00:00.000000",
			"docstatus": 0
		})
		time_log.insert()
		time_log.submit()

		self.assertEquals(frappe.db.get_value("Time Log", time_log.name, "status"), "Submitted")
		tlb = frappe.copy_doc(test_records[0])
		tlb.get("time_log_batch_details")[0].time_log = time_log.name
		tlb.insert()
		tlb.submit()

		self.assertEquals(frappe.db.get_value("Time Log", time_log.name, "status"), "Batched for Billing")
		tlb.cancel()
		self.assertEquals(frappe.db.get_value("Time Log", time_log.name, "status"), "Submitted")

test_records = frappe.get_test_records('Time Log Batch')
test_dependencies = ["Time Log"]
test_ignore = ["Sales Invoice"]
