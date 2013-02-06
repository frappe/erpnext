import sys
import unittest

from hr.doctype.leave_application.leave_application import LeaveDayBlockedError

class TestLeaveApplication(unittest.TestCase):
	def test_block_list(self):
		import webnotes
		webnotes.conn.set_value("Employee", "_T-Employee-0001", "department", 
			"_Test Department with Block List")
		
		application = webnotes.model_wrapper(test_records[1])
		application.doc.from_date = "2013-01-01"
		application.doc.to_date = "2013-01-05"
		self.assertRaises(LeaveDayBlockedError, application.insert)
		
		webnotes.session.user = "test1@erpnext.com"
		webnotes.get_obj("Profile", "test1@erpnext.com").add_role("HR User")
		self.assertTrue(application.insert())
		

test_records = [
	[{
		"doctype": "Leave Allocation",
		"leave_type": "_Test Leave Type",
		"fiscal_year": "_Test Fiscal Year",
		"employee":"_T-Employee-0001",
		"new_leaves_allocated": 15,
		"docstatus": 1
	}],
	[{
		"doctype": "Leave Application",
		"leave_type": "_Test Leave Type",
		"from_date": "2013-05-01",
		"to_date": "2013-05-05",
		"posting_date": "2013-01-02",
		"fiscal_year": "_Test Fiscal Year",
		"employee": "_T-Employee-0001"
	}]]

if __name__=="__main__":
	sys.path.extend(["app", "lib"])
	import webnotes
	webnotes.connect()

	from webnotes.test_runner import make_test_records
	make_test_records("Leave Application")

	unittest.main()

