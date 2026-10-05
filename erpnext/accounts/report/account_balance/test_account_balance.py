import frappe
from frappe.utils import add_days, getdate

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.account_balance.account_balance import execute
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountBalance(ERPNextTestSuite):
	def test_account_balance(self):
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
				"account": "Exchange Gain - _TC2",
				"currency": "EUR",
				"balance": 0.0,
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
				"account": "Interest Income - _TC2",
				"currency": "EUR",
				"balance": 0.0,
			},
			{
				"account": "Interest on Fixed Deposits - _TC2",
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

	def test_income_balance_starts_at_fiscal_year(self):
		filters = {"company": "_Test Company 2", "report_date": getdate(), "root_type": "Income"}

		def sales_balance():
			return next(row["balance"] for row in execute(filters)[1] if row["account"] == "Sales - _TC2")

		before = sales_balance()
		year_start_date = get_fiscal_year(getdate(), company="_Test Company 2")[1]
		make_sales_invoice(posting_date=add_days(year_start_date, -1), rate=100)
		make_sales_invoice(rate=30)

		self.assertEqual(sales_balance() - before, -30)


def make_sales_invoice(**args):
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
		**args,
	)
