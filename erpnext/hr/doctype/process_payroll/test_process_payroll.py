# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import unittest

import erpnext
import frappe
from frappe.utils import nowdate
from erpnext.hr.doctype.process_payroll.process_payroll import get_end_date


class TestProcessPayroll(unittest.TestCase):
	def test_process_payroll(self):
		month = "11"
		fiscal_year = "_Test Fiscal Year 2016"

		for data in frappe.get_all('Salary Component', fields = ["name"]):
			if not frappe.db.get_value('Salary Component Account',
				{'parent': data.name, 'company': erpnext.get_default_company()}, 'name'):
				get_salary_component_account(data.name)
				
		payment_account = frappe.get_value('Account',
			{'account_type': 'Cash', 'company': erpnext.get_default_company(),'is_group':0}, "name")

		if not frappe.db.get_value("Salary Slip", {"start_date": "2016-11-01", "end_date": "2016-11-30"}):
			process_payroll = frappe.get_doc("Process Payroll", "Process Payroll")
			process_payroll.company = erpnext.get_default_company()
			process_payroll.start_date = "2016-11-01"
			process_payroll.end_date = "2016-11-30"
			process_payroll.payment_account = payment_account
			process_payroll.posting_date = nowdate()
			process_payroll.payroll_frequency = "Monthly"
			process_payroll.create_salary_slips()
			process_payroll.submit_salary_slips()
			if process_payroll.get_sal_slip_list(ss_status = 1):
				r = process_payroll.make_payment_entry()

	def test_get_end_date(self):
		self.assertEqual(get_end_date('2017-01-01', 'monthly'), {'end_date': '2017-01-31'})
		self.assertEqual(get_end_date('2017-02-01', 'monthly'), {'end_date': '2017-02-28'})
		self.assertEqual(get_end_date('2017-02-01', 'fortnightly'), {'end_date': '2017-02-14'})
		self.assertEqual(get_end_date('2017-02-01', 'bimonthly'), {'end_date': ''})
		self.assertEqual(get_end_date('2017-01-01', 'bimonthly'), {'end_date': ''})
		self.assertEqual(get_end_date('2020-02-15', 'bimonthly'), {'end_date': ''})
		self.assertEqual(get_end_date('2017-02-15', 'monthly'), {'end_date': '2017-03-14'})
		self.assertEqual(get_end_date('2017-02-15', 'daily'), {'end_date': '2017-02-15'})
	

def get_salary_component_account(sal_comp):
	company = erpnext.get_default_company()
	sal_comp = frappe.get_doc("Salary Component", sal_comp)
	sc = sal_comp.append("accounts")
	sc.company = company
	sc.default_account = create_account(company)
	
def create_account(company):
	salary_account = frappe.db.get_value("Account", "Salary - " + frappe.db.get_value('Company', company, 'abbr'))
	if not salary_account:
		frappe.get_doc({
		"doctype": "Account",
		"account_name": "Salary",
		"parent_account": "Indirect Expenses - " + frappe.db.get_value('Company', company, 'abbr'),
		"company": company
		}).insert()
	return salary_account