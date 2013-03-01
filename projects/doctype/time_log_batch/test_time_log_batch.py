import webnotes, unittest

class TimeLogBatchTest(unittest.TestCase):
	def test_time_log_status(self):
		self.assertEquals(webnotes.conn.get_value("Time Log", "_T-Time Log-00001", "status"), "Submitted")
		tlb = webnotes.bean("Time Log Batch", "_T-Time Log Batch-00001")
		tlb.submit()
		self.assertEquals(webnotes.conn.get_value("Time Log", "_T-Time Log-00001", "status"), "Batched for Billing")
		tlb.cancel()
		self.assertEquals(webnotes.conn.get_value("Time Log", "_T-Time Log-00001", "status"), "Submitted")

test_records = [[
	{"rate": "500"},
	{
		"doctype": "Time Log Batch Detail",
		"parenttype": "Time Log Batch",
		"parentfield": "time_log_batch_details",
		"time_log": "_T-Time Log-00001",
	}
]]