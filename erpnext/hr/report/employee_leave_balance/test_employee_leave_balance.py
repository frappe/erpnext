# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.utils import add_days, add_months, flt, get_year_ending, get_year_start, getdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.holiday_list.test_holiday_list import set_holiday_list
from erpnext.hr.doctype.leave_application.test_leave_application import (
	get_first_sunday,
	make_allocation_record,
)
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import process_expired_allocation
from erpnext.hr.doctype.leave_type.test_leave_type import create_leave_type
from erpnext.hr.report.employee_leave_balance.employee_leave_balance import execute
from erpnext.payroll.doctype.salary_slip.test_salary_slip import (
	make_holiday_list,
	make_leave_application,
)

test_records = frappe.get_test_records("Leave Type")


class TestEmployeeLeaveBalance(unittest.TestCase):
	def setUp(self):
		for dt in [
			"Leave Application",
			"Leave Allocation",
			"Salary Slip",
			"Leave Ledger Entry",
			"Leave Type",
		]:
			frappe.db.delete(dt)

		frappe.set_user("Administrator")

		self.employee_id = make_employee("test_emp_leave_balance@example.com", company="_Test Company")

		self.date = getdate()
		self.year_start = getdate(get_year_start(self.date))
		self.mid_year = add_months(self.year_start, 6)
		self.year_end = getdate(get_year_ending(self.date))

		self.holiday_list = make_holiday_list(
			"_Test Emp Balance Holiday List", self.year_start, self.year_end
		)

	def tearDown(self):
		frappe.db.rollback()

	@set_holiday_list("_Test Emp Balance Holiday List", "_Test Company")
	def test_employee_leave_balance(self):
		frappe.get_doc(test_records[0]).insert()

		# 5 leaves
		allocation1 = make_allocation_record(
			employee=self.employee_id,
			from_date=add_days(self.year_start, -11),
			to_date=add_days(self.year_start, -1),
			leaves=5,
		)
		# 30 leaves
		allocation2 = make_allocation_record(
			employee=self.employee_id, from_date=self.year_start, to_date=self.year_end
		)
		# expires 5 leaves
		process_expired_allocation()

		# 4 days leave
		first_sunday = get_first_sunday(self.holiday_list, for_date=self.year_start)
		leave_application = make_leave_application(
			self.employee_id, add_days(first_sunday, 1), add_days(first_sunday, 4), "_Test Leave Type"
		)
		leave_application.reload()

		filters = frappe._dict(
			{
				"from_date": allocation1.from_date,
				"to_date": allocation2.to_date,
				"employee": self.employee_id,
			}
		)

		report = execute(filters)

		expected_data = [
			{
				"leave_type": "_Test Leave Type",
				"employee": self.employee_id,
				"employee_name": "test_emp_leave_balance@example.com",
				"leaves_allocated": flt(allocation1.new_leaves_allocated + allocation2.new_leaves_allocated),
				"leaves_expired": flt(allocation1.new_leaves_allocated),
				"opening_balance": flt(0),
				"leaves_taken": flt(leave_application.total_leave_days),
				"closing_balance": flt(allocation2.new_leaves_allocated - leave_application.total_leave_days),
				"indent": 1,
			}
		]

		self.assertEqual(report[1], expected_data)

	@set_holiday_list("_Test Emp Balance Holiday List", "_Test Company")
	def test_opening_balance_on_alloc_boundary_dates(self):
		frappe.get_doc(test_records[0]).insert()

		# 30 leaves allocated
		allocation1 = make_allocation_record(
			employee=self.employee_id, from_date=self.year_start, to_date=self.year_end
		)
		# 4 days leave application in the first allocation
		first_sunday = get_first_sunday(self.holiday_list, for_date=self.year_start)
		leave_application = make_leave_application(
			self.employee_id, add_days(first_sunday, 1), add_days(first_sunday, 4), "_Test Leave Type"
		)
		leave_application.reload()

		# Case 1: opening balance for first alloc boundary
		filters = frappe._dict(
			{"from_date": self.year_start, "to_date": self.year_end, "employee": self.employee_id}
		)
		report = execute(filters)
		self.assertEqual(report[1][0].opening_balance, 0)

		# Case 2: opening balance after leave application date
		filters = frappe._dict(
			{
				"from_date": add_days(leave_application.to_date, 1),
				"to_date": self.year_end,
				"employee": self.employee_id,
			}
		)
		report = execute(filters)
		self.assertEqual(
			report[1][0].opening_balance,
			(allocation1.new_leaves_allocated - leave_application.total_leave_days),
		)

		# Case 3: leave balance shows actual balance and not consumption balance as per remaining days near alloc end date
		# eg: 3 days left for alloc to end, leave balance should still be 26 and not 3
		filters = frappe._dict(
			{
				"from_date": add_days(self.year_end, -3),
				"to_date": self.year_end,
				"employee": self.employee_id,
			}
		)
		report = execute(filters)
		self.assertEqual(
			report[1][0].opening_balance,
			(allocation1.new_leaves_allocated - leave_application.total_leave_days),
		)

	@set_holiday_list("_Test Emp Balance Holiday List", "_Test Company")
	def test_opening_balance_considers_carry_forwarded_leaves(self):
		leave_type = create_leave_type(leave_type_name="_Test_CF_leave_expiry", is_carry_forward=1)
		leave_type.insert()

		# 30 leaves allocated for first half of the year
		allocation1 = make_allocation_record(
			employee=self.employee_id,
			from_date=self.year_start,
			to_date=self.mid_year,
			leave_type=leave_type.name,
		)
		# 4 days leave application in the first allocation
		first_sunday = get_first_sunday(self.holiday_list, for_date=self.year_start)
		leave_application = make_leave_application(
			self.employee_id, first_sunday, add_days(first_sunday, 3), leave_type.name
		)
		leave_application.reload()
		# 30 leaves allocated for second half of the year + carry forward leaves (26) from the previous allocation
		allocation2 = make_allocation_record(
			employee=self.employee_id,
			from_date=add_days(self.mid_year, 1),
			to_date=self.year_end,
			carry_forward=True,
			leave_type=leave_type.name,
		)

		# Case 1: carry forwarded leaves considered in opening balance for second alloc
		filters = frappe._dict(
			{
				"from_date": add_days(self.mid_year, 1),
				"to_date": self.year_end,
				"employee": self.employee_id,
			}
		)
		report = execute(filters)
		# available leaves from old alloc
		opening_balance = allocation1.new_leaves_allocated - leave_application.total_leave_days
		self.assertEqual(report[1][0].opening_balance, opening_balance)

		# Case 2: opening balance one day after alloc boundary = carry forwarded leaves + new leaves alloc
		filters = frappe._dict(
			{
				"from_date": add_days(self.mid_year, 2),
				"to_date": self.year_end,
				"employee": self.employee_id,
			}
		)
		report = execute(filters)
		# available leaves from old alloc
		opening_balance = allocation2.new_leaves_allocated + (
			allocation1.new_leaves_allocated - leave_application.total_leave_days
		)
		self.assertEqual(report[1][0].opening_balance, opening_balance)
