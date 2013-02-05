import sys
import unittest

from hr.doctype.leave_application.leave_application import test_records, LeaveDayBlockedError

class TestLeaveApplication(unittest.TestCase):
	def setUp(self):
		from webnotes.test_runner import make_test_records
		make_test_records("Leave Application")
	
	def test_block_list(self):
		import webnotes
		webnotes.conn.set_value("Employee", "_T-Employee-0001", "department", 
			"_Test Department with Block List")
			
		application = webnotes.model_wrapper(test_records[1])
		application.doc.from_date = "2013-01-01"
		application.doc.to_date = "2013-01-05"
		self.assertRaises(LeaveDayBlockedError, application.insert)
		
if __name__=="__main__":
	sys.path.extend(["app", "lib"])
	import webnotes
	webnotes.connect()
	unittest.main()
	