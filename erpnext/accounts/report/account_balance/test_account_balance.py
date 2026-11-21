import unittest

import frappe
from frappe.utils import add_days, getdate

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.account_balance.account_balance import execute
from erpnext.accounts.utils import get_fiscal_year


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

	def test_income_balance_starts_at_fiscal_year(self):
		filters = {"company": "_Test Company 2", "report_date": getdate(), "root_type": "Income"}

		def sales_balance():
			return next(row["balance"] for row in execute(filters)[1] if row["account"] == "Sales - _TC2")

		before = sales_balance()
		year_start_date = get_fiscal_year(getdate(), company="_Test Company 2")[1]
		make_sales_invoice(posting_date=add_days(year_start_date, -1), rate=100)
		make_sales_invoice(rate=30)

		self.assertEqual(sales_balance() - before, -30)

	def test_year_start_resolved_per_company_without_company_filter(self):
		frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": "_Test AB Fiscal Year 2026-27",
				"year_start_date": "2026-04-01",
				"year_end_date": "2027-03-31",
				"companies": [{"company": "_Test Company 2"}],
			}
		).insert()
		self.addCleanup(frappe.cache().delete_key, "fiscal_years")
		self.addCleanup(frappe.db.rollback)
		create_sales_invoice(posting_date="2026-02-01", rate=70)

		def sales_balance(company=None):
			filters = {"company": company, "report_date": "2026-10-15", "root_type": "Income"}
			return next(row["balance"] for row in execute(filters)[1] if row["account"] == "Sales - _TC")

		self.assertEqual(sales_balance(), sales_balance("_Test Company"))


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
