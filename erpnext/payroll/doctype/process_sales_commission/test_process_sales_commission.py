# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_to_date, getdate

from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.payroll.doctype.salary_structure.test_salary_structure import (
	create_salary_structure_assignment,
)
from erpnext.payroll.doctype.sales_commission.test_sales_commission import (
	company,
	emp_name,
	make_salary_structure,
	make_sales_person,
	make_so,
	salary_structure,
	sales_commission_component,
	setup_test,
)

salary_structure = "Salary Structure for Sales Commission2"
emp_name2= "test_sales_commission2@payout.com"
class TestProcessSalesCommission(unittest.TestCase):
	def setUp(self):
		setup_test()
		emp_id = make_employee(emp_name2, company=company)
		make_sales_person(emp_id, emp_name2)
		make_salary_structure(salary_structure)
		create_salary_structure_assignment(
			emp_id,
			salary_structure,
			company=company,
			currency="INR"
		)

		frappe.db.set_value("Payroll Settings", "Payroll Settings", "salary_component_for_sales_commission", sales_commission_component[0]["salary_component"])
		frappe.db.set_value("Selling Settings", "Selling Settings", "approval_required_for_sales_commission_payout", 0)
		frappe.db.sql("delete from `tabAdditional Salary`")
		frappe.db.set_value("Payroll Settings", None, "email_salary_slip_to_employee", 0)

	def tearDown(self):
		for dt in ["Additional Salary", "Salary Structure Assignment", "Salary Structure"]:
			frappe.db.sql("delete from `tab%s`" % dt)

	def test_process_sales_commission(self):
		make_so(emp_name)
		make_so(emp_name2)

		psc = frappe.new_doc("Process Sales Commission")
		psc.company = company
		psc.commission_based_on = "Sales Order"
		psc.from_date = add_to_date(getdate(), days=-2)
		psc.to_date = getdate()
		psc.insert()
		psc.submit()

		sales_commissions = frappe.get_all("Sales Commission", filters={"process_sales_commission_reference": psc.name})
		self.assertEqual(len(sales_commissions), 2)
