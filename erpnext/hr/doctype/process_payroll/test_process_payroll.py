# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import unittest
import frappe
import erpnext
from frappe.utils import flt, add_months, cint, nowdate, getdate, add_days, random_string
from frappe.utils.make_random import get_random

class TestProcessPayroll(unittest.TestCase):
	def test_process_payroll(self):
		month = "11"
		fiscal_year = "_Test Fiscal Year 2016"
		payment_account = frappe.get_all("Account")[0].name
		if not frappe.db.get_value("Salary Slip", {"fiscal_year": fiscal_year, "month": month}):
			process_payroll = frappe.get_doc("Process Payroll", "Process Payroll")
			process_payroll.company = erpnext.get_default_company()
			process_payroll.month = month
			process_payroll.fiscal_year = fiscal_year
			process_payroll.from_date = "2016-11-01"
			process_payroll.to_date = "2016-11-30"
			process_payroll.payment_account = payment_account
			process_payroll.create_sal_slip()
			process_payroll.submit_salary_slip()
			if process_payroll.get_sal_slip_list(ss_status = 1):
				r = process_payroll.make_journal_entry(reference_number=random_string(10),reference_date=nowdate())