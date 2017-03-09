# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
import erpnext
from frappe.utils import nowdate
from erpnext.hr.doctype.salary_structure.test_salary_structure import make_salary_structure, make_employee
from erpnext.hr.doctype.payroll.payroll \
	import create_salary_slips, submit_salary_slips, make_accural_jv_entry, make_payment_entry, get_start_end_dates
from erpnext.hr.doctype.salary_slip.test_salary_slip \
	import make_earning_salary_component, make_deduction_salary_component, get_salary_component_account

class TestPayroll(unittest.TestCase):
	def setUp(self):
		make_earning_salary_component(["Basic Salary", "Special Allowance", "HRA"])
		make_deduction_salary_component(["Professional Tax", "TDS"])
		make_employee("test_employee@salary.com")
		make_employee("test_employee_2@salary.com")
		make_salary_structure("Payroll Salary Structure")
		date_details = get_start_end_dates("Monthly", nowdate())
		self.start_date = date_details.start_date
		self.end_date = date_details.end_date
		self.company = erpnext.get_default_company()
		
		for data in frappe.get_all('Salary Component', fields = ["name"]):
			if not frappe.db.get_value('Salary Component Account', {'parent': data.name, 'company': self.company}, 'name'):
				get_salary_component_account(data.name)

		if not frappe.db.get_value("Company", {"company_name": self.company}, "default_payroll_payable_account"):
			frappe.db.set_value("Company", {"company_name": self.company}, "default_payroll_payable_account", frappe.db.get_value('Account', dict(account_name='Payroll Payable')))

	def test_payroll(self):
		payroll = frappe.get_doc({
					"doctype": "Payroll",
					"company": self.company,
					"start_date": self.start_date,
					"end_date": self.end_date,
					"payment_account": frappe.get_value('Account', {'account_type': 'Cash', 'company': self.company,'is_group':0}, "name"),
					"posting_date": nowdate(),
					"payroll_frequency": "Monthly",
				}).insert()

		created_salary_slips = create_salary_slips(payroll.start_date, payroll.end_date, payroll.company, payroll.payroll_frequency, payroll.posting_date)
		if created_salary_slips:
			for salary_slip in created_salary_slips:
				ss = payroll.append("salary_slips")
				ss.employee = salary_slip.employee
				ss.employee_name = salary_slip.employee_name
				ss.salary_slip = salary_slip.name
				ss.salary_slip_status = salary_slip.status
				ss.net_pay = salary_slip.net_pay
			payroll.save()
			submitted_salary_slips = submit_salary_slips(payroll.name)
			if submitted_salary_slips:
				for salary_slip in submitted_salary_slips:
					frappe.db.set_value("Payroll Salary Slip", salary_slip, "salary_slip_status", "Submitted")
				make_accural_jv_entry(payroll.name, payroll.company, payroll.start_date, payroll.end_date)
				make_payment_entry(payroll.name, payroll.company, payroll.start_date, payroll.end_date, payroll.payment_account)