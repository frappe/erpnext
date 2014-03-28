# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, unittest

class TimeLogBatchTest(unittest.TestCase):
	def test_time_log_status(self):
		from erpnext.projects.doctype.time_log.test_time_log import test_records as time_log_records
		time_log = frappe.get_doc(copy=time_log_records[0])
		time_log.update({
			"from_time": "2013-01-02 10:00:00.000000",
			"to_time": "2013-01-02 11:00:00.000000",
			"docstatus": 0
		})
		time_log.insert()
		time_log.submit()
		
		self.assertEquals(frappe.db.get_value("Time Log", time_log.name, "status"), "Submitted")
		tlb = frappe.get_doc(copy=test_records[0])
		tlb.doclist[1].time_log = time_log.name
		tlb.insert()
		tlb.submit()

		self.assertEquals(frappe.db.get_value("Time Log", time_log.name, "status"), "Batched for Billing")
		tlb.cancel()
		self.assertEquals(frappe.db.get_value("Time Log", time_log.name, "status"), "Submitted")

test_records = [[
	{
		"doctype": "Time Log Batch",
		"rate": "500"
	},
	{
		"doctype": "Time Log Batch Detail",
		"parenttype": "Time Log Batch",
		"parentfield": "time_log_batch_details",
		"time_log": "_T-Time Log-00001",
	}
]]