# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes
import unittest

from hr.doctype.leave_application.leave_application import LeaveDayBlockedError, OverlapError

class TestLeaveApplication(unittest.TestCase):
	def tearDown(self):
		webnotes.set_user("Administrator")
		
	def _clear_roles(self):
		webnotes.conn.sql("""delete from `tabUserRole` where parent in 
			("test@example.com", "test1@example.com", "test2@example.com")""")
			
	def _clear_applications(self):
		webnotes.conn.sql("""delete from `tabLeave Application`""")
		
	def _add_employee_leave_approver(self, employee, leave_approver):
		temp_session_user = webnotes.session.user
		webnotes.set_user("Administrator")
		employee = webnotes.bean("Employee", employee)
		employee.doclist.append({
			"doctype": "Employee Leave Approver",
			"parentfield": "employee_leave_approvers",
			"leave_approver": leave_approver
		})
		employee.save()
		webnotes.set_user(temp_session_user)
	
	def get_application(self, doclist):
		application = webnotes.bean(copy=doclist)
		application.doc.from_date = "2013-01-01"
		application.doc.to_date = "2013-01-05"
		return application

	def test_block_list(self):
		self._clear_roles()
		
		from webnotes.profile import add_role
		add_role("test1@example.com", "HR User")
			
		webnotes.conn.set_value("Department", "_Test Department", 
			"leave_block_list", "_Test Leave Block List")
		
		application = self.get_application(test_records[1])
		application.insert()
		application.doc.status = "Approved"
		self.assertRaises(LeaveDayBlockedError, application.submit)
		
		webnotes.set_user("test1@example.com")

		# clear other applications
		webnotes.conn.sql("delete from `tabLeave Application`")
		
		application = self.get_application(test_records[1])
		self.assertTrue(application.insert())
		
	def test_overlap(self):
		self._clear_roles()
		self._clear_applications()
		
		from webnotes.profile import add_role
		add_role("test@example.com", "Employee")
		add_role("test2@example.com", "Leave Approver")
		
		webnotes.set_user("test@example.com")
		application = self.get_application(test_records[1])
		application.doc.leave_approver = "test2@example.com"
		application.insert()
		
		application = self.get_application(test_records[1])
		application.doc.leave_approver = "test2@example.com"
		self.assertRaises(OverlapError, application.insert)
		
	def test_global_block_list(self):
		self._clear_roles()

		from webnotes.profile import add_role
		add_role("test1@example.com", "Employee")
		add_role("test@example.com", "Leave Approver")
				
		application = self.get_application(test_records[3])
		application.doc.leave_approver = "test@example.com"
		
		webnotes.conn.set_value("Leave Block List", "_Test Leave Block List", 
			"applies_to_all_departments", 1)
		webnotes.conn.set_value("Employee", "_T-Employee-0002", "department", 
			"_Test Department")
		
		webnotes.set_user("test1@example.com")
		application.insert()
		
		webnotes.set_user("test@example.com")
		application.doc.status = "Approved"
		self.assertRaises(LeaveDayBlockedError, application.submit)
		
		webnotes.conn.set_value("Leave Block List", "_Test Leave Block List", 
			"applies_to_all_departments", 0)
		
	def test_leave_approval(self):
		self._clear_roles()
		
		from webnotes.profile import add_role
		add_role("test@example.com", "Employee")
		add_role("test1@example.com", "Leave Approver")
		add_role("test2@example.com", "Leave Approver")
		
		self._test_leave_approval_basic_case()
		self._test_leave_approval_invalid_leave_approver_insert()
		self._test_leave_approval_invalid_leave_approver_submit()
		self._test_leave_approval_valid_leave_approver_insert()
		
	def _test_leave_approval_basic_case(self):
		self._clear_applications()
		
		# create leave application as Employee
		webnotes.set_user("test@example.com")
		application = self.get_application(test_records[1])
		application.doc.leave_approver = "test1@example.com"
		application.insert()
		
		# submit leave application by Leave Approver
		webnotes.set_user("test1@example.com")
		application.doc.status = "Approved"
		application.submit()
		self.assertEqual(webnotes.conn.get_value("Leave Application", application.doc.name,
			"docstatus"), 1)
		
	def _test_leave_approval_invalid_leave_approver_insert(self):
		from hr.doctype.leave_application.leave_application import InvalidLeaveApproverError
		
		self._clear_applications()
		
		# add a different leave approver in the employee's list
		# should raise exception if not a valid leave approver
		self._add_employee_leave_approver("_T-Employee-0001", "test2@example.com")
		
		# TODO - add test2@example.com leave approver in employee's leave approvers list
		application = self.get_application(test_records[1])
		webnotes.set_user("test@example.com")
		
		application.doc.leave_approver = "test1@example.com"
		self.assertRaises(InvalidLeaveApproverError, application.insert)
		
		webnotes.conn.sql("""delete from `tabEmployee Leave Approver` where parent=%s""",
			"_T-Employee-0001")
		
	def _test_leave_approval_invalid_leave_approver_submit(self):
		self._clear_applications()
		self._add_employee_leave_approver("_T-Employee-0001", "test2@example.com")
		
		# create leave application as employee
		# but submit as invalid leave approver - should raise exception
		webnotes.set_user("test@example.com")
		application = self.get_application(test_records[1])
		application.doc.leave_approver = "test2@example.com"
		application.insert()
		webnotes.set_user("test1@example.com")
		application.doc.status = "Approved"
		
		from webnotes.model.bean import BeanPermissionError
		self.assertRaises(BeanPermissionError, application.submit)
		
		webnotes.conn.sql("""delete from `tabEmployee Leave Approver` where parent=%s""",
			"_T-Employee-0001")
		
	def _test_leave_approval_valid_leave_approver_insert(self):
		self._clear_applications()
		self._add_employee_leave_approver("_T-Employee-0001", "test2@example.com")
		
		original_department = webnotes.conn.get_value("Employee", "_T-Employee-0001", "department")
		webnotes.conn.set_value("Employee", "_T-Employee-0001", "department", None)
		
		webnotes.set_user("test@example.com")
		application = self.get_application(test_records[1])
		application.doc.leave_approver = "test2@example.com"
		application.insert()

		# change to valid leave approver and try to submit leave application
		webnotes.set_user("test2@example.com")
		application.doc.status = "Approved"
		application.submit()
		self.assertEqual(webnotes.conn.get_value("Leave Application", application.doc.name,
			"docstatus"), 1)
			
		webnotes.conn.sql("""delete from `tabEmployee Leave Approver` where parent=%s""",
			"_T-Employee-0001")
		
		webnotes.conn.set_value("Employee", "_T-Employee-0001", "department", original_department)
		
test_dependencies = ["Leave Block List"]		

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
	}],
	[{
		"doctype": "Leave Application",
		"leave_type": "_Test Leave Type LWP",
		"from_date": "2013-01-15",
		"to_date": "2013-01-15",
		"posting_date": "2013-01-02",
		"fiscal_year": "_Test Fiscal Year 2013",
		"employee": "_T-Employee-0001",
		"company": "_Test Company",
	}]
]
