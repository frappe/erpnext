# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, unittest

class TimeLogBatchTest(unittest.TestCase):
	def test_time_log_status(self):
		delete_time_log_and_batch()
		time_log = create_time_log()

		self.assertEquals(frappe.db.get_value("Time Log", time_log, "status"), "Submitted")

		tlb = create_time_log_batch(time_log)

		self.assertEquals(frappe.db.get_value("Time Log", time_log, "status"), "Batched for Billing")
		tlb.cancel()
		self.assertEquals(frappe.db.get_value("Time Log", time_log, "status"), "Submitted")

		delete_time_log_and_batch()

def delete_time_log_and_batch():
	for name in frappe.db.sql_list("select name from `tabTime Log Batch` where docstatus=1"):
		frappe.get_doc("Time Log Batch", name).cancel()
		frappe.delete_doc("Time Log Batch", name)

	for name in frappe.db.sql_list("select name from `tabTime Log` where docstatus=1"):
		frappe.get_doc("Time Log", name).cancel()
		frappe.delete_doc("Time Log", name)

def create_time_log():
	from erpnext.projects.doctype.time_log.test_time_log import test_records as time_log_records
	time_log = frappe.copy_doc(time_log_records[0])
	time_log.update({
		"from_time": "2013-01-02 10:00:00.000000",
		"to_time": "2013-01-02 11:00:00.000000",
		"docstatus": 0
	})
	time_log.insert()
	time_log.submit()
	return time_log.name

def create_time_log_batch(time_log):
	tlb = frappe.get_doc({
		"doctype": "Time Log Batch",
		"rate": "500",
		"time_log_batch_details": [
			{
			"doctype": "Time Log Batch Detail",
			"parentfield": "time_log_batch_details",
			"parenttype": "Time Log Batch",
			"time_log": time_log
			}
		]
	})

	tlb.insert()
	tlb.submit()
	return tlb

test_ignore = ["Sales Invoice"]
