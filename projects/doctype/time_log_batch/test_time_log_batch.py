# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes, unittest

class TimeLogBatchTest(unittest.TestCase):
	def test_time_log_status(self):
		from projects.doctype.time_log.test_time_log import test_records as time_log_records
		time_log = webnotes.bean(copy=time_log_records[0])
		time_log.doc.fields.update({
			"from_time": "2013-01-02 10:00:00",
			"to_time": "2013-01-02 11:00:00",
			"docstatus": 0
		})
		time_log.insert()
		time_log.submit()
		
		self.assertEquals(webnotes.conn.get_value("Time Log", time_log.doc.name, "status"), "Submitted")
		tlb = webnotes.bean(copy=test_records[0])
		tlb.doclist[1].time_log = time_log.doc.name
		tlb.insert()
		tlb.submit()

		self.assertEquals(webnotes.conn.get_value("Time Log", time_log.doc.name, "status"), "Batched for Billing")
		tlb.cancel()
		self.assertEquals(webnotes.conn.get_value("Time Log", time_log.doc.name, "status"), "Submitted")

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