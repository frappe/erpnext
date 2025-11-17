import unittest

import frappe
from frappe.utils import getdate

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.account_balance.account_balance import execute


class TestAccountBalance(unittest.TestCase):
	def test_account_balance(self):
		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company 2'")
		frappe.db.sql("delete from `tabGL Entry` where company='_Test Company 2'")

		filters = {
			"company": "_Test Company 2",
			"report_date": getdate(),
			"root_type": "Income",
		}

		make_sales_invoice()

		report = execute(filters)

		expected_data = [
			{
				"account": "Direct Income - _TC2",
				"currency": "EUR",
				"balance": -100.0,
			},
			{
				"account": "Income - _TC2",
				"currency": "EUR",
				"balance": -100.0,
			},
			{
				"account": "Indirect Income - _TC2",
				"currency": "EUR",
				"balance": 0.0,
			},
			{
				"account": "Sales - _TC2",
				"currency": "EUR",
				"balance": -100.0,
			},
			{
				"account": "Service - _TC2",
				"currency": "EUR",
				"balance": 0.0,
			},
		]

		self.assertEqual(expected_data, report[1])

	def test_account_balance_TC_ACC_365(self):
		filters = {
			"company": "_Test Company",
			"report_date": getdate(),
			"root_type": "Income",
		}

		make_sales_invoice_1()

		_, data = execute(filters)

		# Build a dict by account for easy lookup
		by_account = {d["account"]: d for d in data}

		expected_accounts = [
        "Direct Income - _TC",
        "Income - _TC",
        "Indirect Income - _TC",
        "Sales - _TC",
        "Service - _TC",
        "_Test Account Sales - _TC",
   		 ]

		for acc in expected_accounts:
			self.assertIn(acc, by_account, f"Missing account in report: {acc}")
			self.assertEqual(
				"INR", by_account[acc]["currency"], f"Currency mismatch for {acc}"
			)
			
			self.assertIsInstance(
				by_account[acc]["balance"], (int, float),
				f"Balance for {acc} is not numeric"
			)

def make_sales_invoice_1():
	frappe.set_user("Administrator")
	create_sales_invoice(
		company="_Test Company",
		customer="_Test Customer",
		warehouse="Finished Goods - _TC",
		debit_to="Debtors - _TC",
		income_account="Sales - _TC",
		expense_account="Cost of Goods Sold - _TC",
		cost_center="Main - _TC",
		items=[{"item_code": "_Test Item", "qty": 1, "rate": 100, "warehouse": "Finished Goods - _TC"}],
	)

def make_sales_invoice():
	frappe.set_user("Administrator")

	create_sales_invoice(
		company="_Test Company 2",
		customer="_Test Customer 2",
		currency="EUR",
		warehouse="Finished Goods - _TC2",
		debit_to="Debtors - _TC2",
		income_account="Sales - _TC2",
		expense_account="Cost of Goods Sold - _TC2",
		cost_center="Main - _TC2",
	)
