# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe, unittest
from erpnext.projects.doctype.time_log.test_time_log import make_time_log_test_record

class TimeLogBatchTest(unittest.TestCase):
	def test_time_log_status(self):
		time_log = make_time_log_test_record(simulate=True)

		self.assertEquals(frappe.db.get_value("Time Log", time_log.name, "status"), "Submitted")

		tlb = create_time_log_batch(time_log.name)

		self.assertEquals(frappe.db.get_value("Time Log", time_log.name, "status"), "Batched for Billing")
		tlb.cancel()
		self.assertEquals(frappe.db.get_value("Time Log", time_log.name, "status"), "Submitted")

def create_time_log_batch(time_log):
	tlb = frappe.get_doc({
		"doctype": "Time Log Batch",
		"time_logs": [
			{
			"doctype": "Time Log Batch Detail",
			"parentfield": "time_logs",
			"parenttype": "Time Log Batch",
			"time_log": time_log
			}
		]
	})

	tlb.insert()
	tlb.submit()
	return tlb

test_ignore = ["Sales Invoice"]
