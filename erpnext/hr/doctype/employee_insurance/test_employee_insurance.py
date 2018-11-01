# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import nowdate, add_months

class TestEmployeeInsurance(unittest.TestCase):
	def test_additional_salary_created(self):
		insurance_record = create_employee_insurance()

		addl_sal_record = frappe.get_doc("Additional Salary", {"salary_component": "_Test Employee Insurance"})
		self.assertEqual(insurance_record.name, addl_sal_record.reference_name)
		self.assertEqual(insurance_record.deduct_from_salary, addl_sal_record.overwrite_salary_structure_amount)
		insurance_record.premium_end_date = add_months(nowdate(), 4)
		insurance_record.update()
		self.assertEqual(insurance_record.premium_end_date, addl_sal_record.to_date)
		insurance_record.cancel()
		self.assertTrue(addl_sal_record.docstatus, 2)

	def tearDown(self):
		frappe.db.sql("""delete from `tabEmployee Insurance`""")
		frappe.db.sql("""delete from `tabAdditional Salary`""")

def create_employee_insurance(**args):
	args = frappe._dict(args)
	if not frappe.db.exists("Insurance Type", "Health Insurance"):
		frappe.get_doc({
			"doctype": "Insurance Type",
			"name": "Health Insurance"
		}).insert()
	if not frappe.db.exists("Insurance Company", "_Test Insurance Company"):
		frappe.get_doc({
			"doctype": "Insurance Company",
			"name": "_Test Insurance Company"
		}).insert()
	
	if not frappe.db.exists("Salary Component", "_Test Employee Insurance"):
		frappe.get_doc({
			"doctype": "Salary Component",
			"salary_component": "_Test Employee Insurance",
			"type": "Deduction",
			"component_type": "Life Insurance",
			"is_additional_component": True,
			"is_payable": 1,
			"is_tax_applicable": 1

		}).insert()	


	doc = frappe.get_doc({
        "doctype": "Employee Insurance",
		"employee": frappe.db.get_value("Employee", {"first_name":"_Test Employee"}, "Name") ,
        "insurance_type": "Health Insurance",
	    "insurance_company": "_Test Insurance Company",
        "maturity_amount": args.maturity_amount or 500,
		"deduct_from_salary": args.deduct_from_salary or True,
		"salary_component":"_Test Employee Insurance",
		"premium_start_date": nowdate(),
		"premium_end_date": add_months(nowdate(), 1),
		"policy_no": "342123443",
		"monthly_premium": args.maturity_premium or 500
    })
	doc.insert()
	doc.submit()
	return doc