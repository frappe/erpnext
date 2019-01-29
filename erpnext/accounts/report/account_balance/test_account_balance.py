from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import getdate
from erpnext.accounts.report.account_balance.account_balance import execute
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice

class TestAccountBalance(unittest.TestCase):
	def test_account_balance(self):
		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company 2'")
		frappe.db.sql("delete from `tabGL Entry` where company='_Test Company 2'")

		filters = {
			'company': '_Test Company 2',
			'report_date': getdate(),
			'root_type': 'Income',
		}

		make_sales_invoice()

		report = execute(filters)

		expected_data = [
			{
				"account": 'Sales - _TC2',
				"currency": 'EUR',
				"balance": -100.0,
			},
			{
				"account": 'Income - _TC2',
				"currency": 'EUR',
				"balance": -100.0,
			},
			{
				"account": 'Service - _TC2',
				"currency": 'EUR',
				"balance": 0.0,
			},
			{
				"account": 'Direct Income - _TC2',
				"currency": 'EUR',
				"balance": -100.0,
			},
			{
				"account": 'Indirect Income - _TC2',
				"currency": 'EUR',
				"balance": 0.0,
			},
		]

		self.assertEqual(expected_data, report[1])

def make_sales_invoice():
	frappe.set_user("Administrator")

	create_sales_invoice(company="_Test Company 2",
		customer = '_Test Customer 2',
		currency = 'EUR',
		warehouse = 'Finished Goods - _TC2',
		debit_to = 'Debtors - _TC2',
		income_account = 'Sales - _TC2',
		expense_account = 'Cost of Goods Sold - _TC2',
		cost_center = '_Test Company 2 - _TC2')





