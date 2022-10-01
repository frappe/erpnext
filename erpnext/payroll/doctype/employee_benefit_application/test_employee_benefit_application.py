# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, date_diff, get_year_ending, get_year_start, getdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.holiday_list.test_holiday_list import set_holiday_list
from erpnext.hr.tests.test_utils import get_first_sunday
from erpnext.hr.utils import get_holiday_dates_for_employee
from erpnext.payroll.doctype.employee_benefit_application.employee_benefit_application import (
	calculate_lwp,
)
from erpnext.payroll.doctype.employee_tax_exemption_declaration.test_employee_tax_exemption_declaration import (
	create_payroll_period,
)
from erpnext.payroll.doctype.salary_slip.test_salary_slip import (
	make_holiday_list,
	make_leave_application,
)
from erpnext.payroll.doctype.salary_structure.salary_structure import make_salary_slip
from erpnext.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure


class TestEmployeeBenefitApplication(FrappeTestCase):
	def setUp(self):
		date = getdate()
		make_holiday_list(from_date=get_year_start(date), to_date=get_year_ending(date))

	@set_holiday_list("Salary Slip Test Holiday List", "_Test Company")
	def test_employee_benefit_application(self):
		payroll_period = create_payroll_period(name="_Test Payroll Period 1", company="_Test Company")
		employee = make_employee("test_employee_benefits@salary.com", company="_Test Company")
		first_sunday = get_first_sunday("Salary Slip Test Holiday List")

		leave_application = make_leave_application(
			employee,
			add_days(first_sunday, 1),
			add_days(first_sunday, 3),
			"Leave Without Pay",
			half_day=1,
			half_day_date=add_days(first_sunday, 1),
			submit=True,
		)

		frappe.db.set_value("Leave Type", "Leave Without Pay", "include_holiday", 0)
		salary_structure = make_salary_structure(
			"Test Employee Benefits",
			"Monthly",
			other_details={"max_benefits": 100000},
			include_flexi_benefits=True,
			employee=employee,
			payroll_period=payroll_period,
		)
		salary_slip = make_salary_slip(salary_structure.name, employee=employee, posting_date=getdate())
		salary_slip.insert()
		salary_slip.submit()

		application = make_employee_benefit_application(
			employee, payroll_period.name, date=leave_application.to_date
		)
		self.assertEqual(application.employee_benefits[0].max_benefit_amount, 15000)

		holidays = get_holiday_dates_for_employee(employee, payroll_period.start_date, application.date)
		working_days = date_diff(application.date, payroll_period.start_date) + 1
		lwp = calculate_lwp(employee, payroll_period.start_date, holidays, working_days)
		self.assertEqual(lwp, 2.5)


def make_employee_benefit_application(employee, payroll_period, date):
	frappe.db.delete("Employee Benefit Application")

	return frappe.get_doc(
		{
			"doctype": "Employee Benefit Application",
			"employee": employee,
			"date": date,
			"payroll_period": payroll_period,
			"employee_benefits": [{"earning_component": "Medical Allowance", "amount": 1500}],
		}
	).insert()
