# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe
import unittest

from erpnext.hr.doctype.leave_application.leave_application import LeaveDayBlockedError, OverlapError, NotAnOptionalHoliday, get_leave_balance_on
from frappe.permissions import clear_user_permissions_for_doctype
from frappe.utils import add_days, nowdate, now_datetime

test_dependencies = ["Leave Allocation", "Leave Block List"]

_test_records = [
 {
  "company": "_Test Company",
  "doctype": "Leave Application",
  "employee": "_T-Employee-00001",
  "from_date": "2013-05-01",
  "leave_type": "_Test Leave Type",
  "posting_date": "2013-01-02",
  "to_date": "2013-05-05"
 },
 {
  "company": "_Test Company",
  "doctype": "Leave Application",
  "employee": "_T-Employee-00002",
  "from_date": "2013-05-01",
  "leave_type": "_Test Leave Type",
  "posting_date": "2013-01-02",
  "to_date": "2013-05-05"
 },
 {
  "company": "_Test Company",
  "doctype": "Leave Application",
  "employee": "_T-Employee-00001",
  "from_date": "2013-01-15",
  "leave_type": "_Test Leave Type LWP",
  "posting_date": "2013-01-02",
  "to_date": "2013-01-15"
 }
]


class TestLeaveApplication(unittest.TestCase):
	def setUp(self):
		for dt in ["Leave Application", "Leave Allocation", "Salary Slip"]:
			frappe.db.sql("delete from `tab%s`" % dt)

	@classmethod
	def setUpClass(cls):
		set_leave_approver()

	def tearDown(self):
		frappe.set_user("Administrator")

	def _clear_roles(self):
		frappe.db.sql("""delete from `tabHas Role` where parent in
			("test@example.com", "test1@example.com", "test2@example.com")""")

	def _clear_applications(self):
		frappe.db.sql("""delete from `tabLeave Application`""")

	def get_application(self, doc):
		application = frappe.copy_doc(doc)
		application.from_date = "2013-01-01"
		application.to_date = "2013-01-05"
		return application

	def test_block_list(self):
		self._clear_roles()

		from frappe.utils.user import add_role
		add_role("test@example.com", "HR User")
		clear_user_permissions_for_doctype("Employee")

		frappe.db.set_value("Department", "_Test Department - _TC",
			"leave_block_list", "_Test Leave Block List")

		make_allocation_record()

		application = self.get_application(_test_records[0])
		application.insert()
		application.status = "Approved"
		self.assertRaises(LeaveDayBlockedError, application.submit)

		frappe.set_user("test@example.com")

		# clear other applications
		frappe.db.sql("delete from `tabLeave Application`")

		application = self.get_application(_test_records[0])
		self.assertTrue(application.insert())

	def test_overlap(self):
		self._clear_roles()
		self._clear_applications()

		from frappe.utils.user import add_role
		add_role("test@example.com", "Employee")
		frappe.set_user("test@example.com")

		make_allocation_record()

		application = self.get_application(_test_records[0])
		application.insert()

		application = self.get_application(_test_records[0])
		self.assertRaises(OverlapError, application.insert)

	def test_overlap_with_half_day_1(self):
		self._clear_roles()
		self._clear_applications()

		from frappe.utils.user import add_role
		add_role("test@example.com", "Employee")
		frappe.set_user("test@example.com")

		make_allocation_record()

		# leave from 1-5, half day on 3rd
		application = self.get_application(_test_records[0])
		application.half_day = 1
		application.half_day_date = "2013-01-03"
		application.insert()

		# Apply again for a half day leave on 3rd
		application = self.get_application(_test_records[0])
		application.from_date = "2013-01-03"
		application.to_date = "2013-01-03"
		application.half_day = 1
		application.half_day_date = "2013-01-03"
		application.insert()

		# Apply again for a half day leave on 3rd
		application = self.get_application(_test_records[0])
		application.from_date = "2013-01-03"
		application.to_date = "2013-01-03"
		application.half_day = 1
		application.half_day_date = "2013-01-03"

		self.assertRaises(OverlapError, application.insert)

	def test_overlap_with_half_day_2(self):
		self._clear_roles()
		self._clear_applications()

		from frappe.utils.user import add_role
		add_role("test@example.com", "Employee")

		frappe.set_user("test@example.com")

		make_allocation_record()

		# leave from 1-5, no half day
		application = self.get_application(_test_records[0])
		application.insert()

		# Apply again for a half day leave on 1st
		application = self.get_application(_test_records[0])
		application.half_day = 1
		application.half_day_date = application.from_date

		self.assertRaises(OverlapError, application.insert)

	def test_overlap_with_half_day_3(self):
		self._clear_roles()
		self._clear_applications()

		from frappe.utils.user import add_role
		add_role("test@example.com", "Employee")

		frappe.set_user("test@example.com")

		make_allocation_record()

		# leave from 1-5, half day on 5th
		application = self.get_application(_test_records[0])
		application.half_day = 1
		application.half_day_date = "2013-01-05"
		application.insert()

		# Apply leave from 4-7, half day on 5th
		application = self.get_application(_test_records[0])
		application.from_date = "2013-01-04"
		application.to_date = "2013-01-07"
		application.half_day = 1
		application.half_day_date = "2013-01-05"

		self.assertRaises(OverlapError, application.insert)

		# Apply leave from 5-7, half day on 5th
		application = self.get_application(_test_records[0])
		application.from_date = "2013-01-05"
		application.to_date = "2013-01-07"
		application.half_day = 1
		application.half_day_date = "2013-01-05"
		application.insert()

	def test_optional_leave(self):
		leave_period = get_leave_period()
		today = nowdate()
		from datetime import date
		holiday_list = 'Test Holiday List for Optional Holiday'
		if not frappe.db.exists('Holiday List', holiday_list):
			frappe.get_doc(dict(
				doctype = 'Holiday List',
				holiday_list_name = holiday_list,
				from_date = date(date.today().year, 1, 1),
				to_date = date(date.today().year, 12, 31),
				holidays = [
					dict(holiday_date = today, description = 'Test')
				]
			)).insert()
		employee = get_employee()

		frappe.db.set_value('Leave Period', leave_period.name, 'optional_holiday_list', holiday_list)
		leave_type = 'Test Optional Type'
		if not frappe.db.exists('Leave Type', leave_type):
			frappe.get_doc(dict(
				leave_type_name = leave_type,
				doctype = 'Leave Type',
				is_optional_leave = 1
			)).insert()

		allocate_leaves(employee, leave_period, leave_type, 10)

		date = add_days(today, - 1)

		leave_application = frappe.get_doc(dict(
			doctype = 'Leave Application',
			employee = employee.name,
			company = '_Test Company',
			leave_type = leave_type,
			from_date = date,
			to_date = date,
		))

		# can only apply on optional holidays
		self.assertTrue(NotAnOptionalHoliday, leave_application.insert)

		leave_application.from_date = today
		leave_application.to_date = today
		leave_application.status = "Approved"
		leave_application.insert()
		leave_application.submit()

		# check leave balance is reduced
		self.assertEqual(get_leave_balance_on(employee.name, leave_type, today), 9)


	def test_leaves_allowed(self):
		employee = get_employee()
		leave_period = get_leave_period()
		frappe.delete_doc_if_exists("Leave Type", "Test Leave Type", force=1)
		leave_type = frappe.get_doc(dict(
			leave_type_name = 'Test Leave Type',
			doctype = 'Leave Type',
			max_leaves_allowed = 5
		)).insert()

		date = add_days(nowdate(), -7)

		allocate_leaves(employee, leave_period, leave_type.name, 5)

		leave_application = frappe.get_doc(dict(
		doctype = 'Leave Application',
			employee = employee.name,
			leave_type = leave_type.name,
			from_date = date,
			to_date = add_days(date, 2),
			company = "_Test Company",
			docstatus = 1,
            status = "Approved"
		))

		self.assertTrue(leave_application.insert())

		leave_application = frappe.get_doc(dict(
			doctype = 'Leave Application',
			employee = employee.name,
			leave_type = leave_type.name,
			from_date = add_days(date, 4),
			to_date = add_days(date, 7),
			company = "_Test Company",
			docstatus = 1,
            status = "Approved"
		))
		self.assertRaises(frappe.ValidationError, leave_application.insert)

	def test_applicable_after(self):
		employee = get_employee()
		leave_period = get_leave_period()
		frappe.delete_doc_if_exists("Leave Type", "Test Leave Type", force=1)
		leave_type = frappe.get_doc(dict(
			leave_type_name = 'Test Leave Type',
			doctype = 'Leave Type',
			applicable_after = 15
		)).insert()
		date = add_days(nowdate(), -7)
		frappe.db.set_value('Employee', employee.name, "date_of_joining", date)
		allocate_leaves(employee, leave_period, leave_type.name, 10)

		leave_application = frappe.get_doc(dict(
			doctype = 'Leave Application',
			employee = employee.name,
			leave_type = leave_type.name,
			from_date = date,
			to_date = add_days(date, 4),
			company = "_Test Company",
			docstatus = 1,
            status = "Approved"
		))

		self.assertRaises(frappe.ValidationError, leave_application.insert)

		frappe.delete_doc_if_exists("Leave Type", "Test Leave Type 1", force=1)
		leave_type_1 = frappe.get_doc(dict(
			leave_type_name = 'Test Leave Type 1',
			doctype = 'Leave Type'
		)).insert()

		allocate_leaves(employee, leave_period, leave_type_1.name, 10)

		leave_application = frappe.get_doc(dict(
		doctype = 'Leave Application',
			employee = employee.name,
			leave_type = leave_type_1.name,
			from_date = date,
			to_date = add_days(date, 4),
			company = "_Test Company",
			docstatus = 1,
            status = "Approved"
		))

		self.assertTrue(leave_application.insert())
		frappe.db.set_value('Employee', employee.name, "date_of_joining", "2010-01-01")

	def test_max_continuous_leaves(self):
		employee = get_employee()
		leave_period = get_leave_period()
		frappe.delete_doc_if_exists("Leave Type", "Test Leave Type", force=1)
		leave_type = frappe.get_doc(dict(
			leave_type_name = 'Test Leave Type',
			doctype = 'Leave Type',
			max_leaves_allowed = 15,
			max_continuous_days_allowed = 3
		)).insert()

		date = add_days(nowdate(), -7)

		allocate_leaves(employee, leave_period, leave_type.name, 10)

		leave_application = frappe.get_doc(dict(
			doctype = 'Leave Application',
			employee = employee.name,
			leave_type = leave_type.name,
			from_date = date,
			to_date = add_days(date, 4),
			company = "_Test Company",
			docstatus = 1,
            status = "Approved"
		))

		self.assertRaises(frappe.ValidationError, leave_application.insert)

	def test_earned_leave(self):
		leave_period = get_leave_period()
		employee = get_employee()
		leave_type = 'Test Earned Leave Type'
		if not frappe.db.exists('Leave Type', leave_type):
			frappe.get_doc(dict(
				leave_type_name = leave_type,
				doctype = 'Leave Type',
				is_earned_leave = 1,
				earned_leave_frequency = 'Monthly',
				rounding = 0.5,
				max_leaves_allowed = 6
			)).insert()
		leave_policy = frappe.get_doc({
			"doctype": "Leave Policy",
			"leave_policy_details": [{"leave_type": leave_type, "annual_allocation": 6}]
		}).insert()
		frappe.db.set_value("Employee", employee.name, "leave_policy", leave_policy.name)

		allocate_leaves(employee, leave_period, leave_type, 0, eligible_leaves = 12)

		from erpnext.hr.utils import allocate_earned_leaves
		i = 0
		while(i<14):
			allocate_earned_leaves()
			i += 1
		self.assertEqual(get_leave_balance_on(employee.name, leave_type, nowdate()), 6)

def make_allocation_record(employee=None, leave_type=None):
	frappe.db.sql("delete from `tabLeave Allocation`")

	allocation = frappe.get_doc({
		"doctype": "Leave Allocation",
		"employee": employee or "_T-Employee-00001",
		"leave_type": leave_type or "_Test Leave Type",
		"from_date": "2013-01-01",
		"to_date": "2015-12-31",
		"new_leaves_allocated": 30
	})

	allocation.insert(ignore_permissions=True)
	allocation.submit()

def get_employee():
	return frappe.get_doc("Employee", "_T-Employee-00001")

def set_leave_approver():
	employee = get_employee()
	dept_doc = frappe.get_doc("Department", employee.department)
	dept_doc.append('leave_approvers', {
		'approver': 'test@example.com'
	})
	dept_doc.save(ignore_permissions=True)

def get_leave_period():
	leave_period_name = frappe.db.exists({
		"doctype": "Leave Period",
		"company": "_Test Company"
	})
	if leave_period_name:
		return frappe.get_doc("Leave Period", leave_period_name[0][0])
	else:
		return frappe.get_doc(dict(
				name = 'Test Leave Period',
				doctype = 'Leave Period',
				from_date = "{0}-01-01".format(now_datetime().year),
				to_date = "{0}-12-31".format(now_datetime().year),
				company = "_Test Company",
				is_active = 1
			)).insert()

def allocate_leaves(employee, leave_period, leave_type, new_leaves_allocated, eligible_leaves=0):
	allocate_leave = frappe.get_doc({
		"doctype": "Leave Allocation",
		"__islocal": 1,
		"employee": employee.name,
		"employee_name": employee.employee_name,
		"leave_type": leave_type,
		"from_date": leave_period.from_date,
		"to_date": leave_period.to_date,
		"new_leaves_allocated": new_leaves_allocated,
		"docstatus": 1
	}).insert()

	allocate_leave.submit()

def make_leave_application(**args):
	args = frappe._dict(args)
	if args.leave_type and not frappe.db.exists("Leave Type", args.leave_type):
		frappe.get_doc({
			"doctype": "Leave Type",
			"leave_type_name": args.leave_type,
			"allow_negative": args.allow_negative
		}).insert()
	
	la = frappe.get_doc(dict(
		doctype = 'Leave Application',
		employee = args.employee,
		leave_type = args.leave_type,
		from_date = args.from_date or nowdate(),
		to_date = args.to_date or nowdate(),
		company = "_Test Company",
		status = "Approved"
	))
	la.submit()