import webnotes
import unittest

from hr.doctype.leave_application.leave_application import LeaveDayBlockedError

class TestLeaveApplication(unittest.TestCase):
	def get_application(self, doclist):
		application = webnotes.model_wrapper(doclist)
		application.doc.from_date = "2013-01-01"
		application.doc.to_date = "2013-01-05"
		return application

	def test_block_list(self):
		import webnotes
		webnotes.conn.set_value("Employee", "_T-Employee-0001", "department", 
			"_Test Department with Block List")
		
		application = self.get_application(test_records[1])
		application.insert()
		self.assertRaises(LeaveDayBlockedError, application.submit)
		
		webnotes.session.user = "test1@example.com"
		
		from webnotes.profile import add_role
		add_role("test1@example.com", "HR User")
		
		application = self.get_application(test_records[1])
		self.assertTrue(application.insert())
		
	def test_global_block_list(self):
		application = self.get_application(test_records[3])
		application.doc.leave_approver = "test@example.com"
		webnotes.conn.set_value("Leave Block List", "_Test Leave Block List", 
			"applies_to_all_departments", 1)
		webnotes.conn.set_value("Employee", "_T-Employee-0002", "department", 
			"_Test Department")
		
		webnotes.session.user = "test2@example.com"
		from webnotes.profile import add_role
		add_role("test2@example.com", "Employee")

		application.insert()
		
		webnotes.session.user = "test@example.com"
		from webnotes.profile import add_role
		add_role("test@example.com", "Leave Approver")
		
		self.assertRaises(LeaveDayBlockedError, application.submit)
		

test_records = [
	[{
		"doctype": "Leave Allocation",
		"leave_type": "_Test Leave Type",
		"fiscal_year": "_Test Fiscal Year 2013",
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
		"fiscal_year": "_Test Fiscal Year 2013",
		"employee": "_T-Employee-0001",
		"company": "_Test Company"
	}],
	[{
		"doctype": "Leave Allocation",
		"leave_type": "_Test Leave Type",
		"fiscal_year": "_Test Fiscal Year 2013",
		"employee":"_T-Employee-0002",
		"new_leaves_allocated": 15,
		"docstatus": 1
	}],
	[{
		"doctype": "Leave Application",
		"leave_type": "_Test Leave Type",
		"from_date": "2013-05-01",
		"to_date": "2013-05-05",
		"posting_date": "2013-01-02",
		"fiscal_year": "_Test Fiscal Year 2013",
		"employee": "_T-Employee-0002",
		"company": "_Test Company"
	}]
]
