# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import unittest
import frappe, erpnext
from frappe.utils import nowdate, get_first_day, get_last_day
from erpnext.hr.doctype.salary_structure.test_salary_structure import make_salary_structure
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.salary_structure.salary_structure import make_salary_slip


class TestAdditionalSalary(unittest.TestCase):
	def setUp(self):
		from erpnext.hr.doctype.salary_slip.test_salary_slip import make_holiday_list
		frappe.db.sql("delete from `tabAdditional Salary`")

		make_holiday_list()
		frappe.db.set_value("Company", erpnext.get_default_company(), "default_holiday_list", "Salary Slip Test Holiday List")

	def test_additional_salary_included(self):
		employee = make_employee("test_email@erpnext.org")
		salary_structure = make_salary_structure("Salary Structure Sample", "Monthly", employee)
		create_additional_salary(salary_component="Additional Allowance", employee=employee)

		salary_slip = make_salary_slip(salary_structure.name, employee=employee,
			from_date=get_first_day(nowdate()), to_date=get_last_day(nowdate()))

		addl_comp = [d for d in salary_slip.earnings if d.salary_component=="Additional Allowance"]
		self.assertTrue(addl_comp)
		self.assertEqual(addl_comp[0].amount, 100)

def create_additional_salary(**args):
	args = frappe._dict(args)
	create_salary_component_if_missing(salary_component = args.salary_component)

	addl_sal = frappe.new_doc("Additional Salary")
	addl_sal.employee = args.employee
	addl_sal.salary_component = args.salary_component
	addl_sal.amount = args.amount or 100
	addl_sal.company = args.company or "_Test Company"
	addl_sal.overwrite_salary_structure_amount = 1
	addl_sal.payroll_date = args.from_date or get_first_day(nowdate())
	addl_sal.to_date = args.to_date or get_last_day(nowdate())
	addl_sal.submit()


def create_salary_component_if_missing(**args):
	args = frappe._dict(args)
	if args.salary_component and not frappe.db.exists("Salary Component", args.salary_component):
		sc = frappe.new_doc("Salary Component")
		sc.salary_component = args.salary_component
		sc.type = args.type or "Earning"
		sc.is_payable = 1
		sc.depends_on_lwp = args.depends_on_lwp
		sc.prorated_based_on_attendance = args.prorated_based_on_attendance
		sc.save()