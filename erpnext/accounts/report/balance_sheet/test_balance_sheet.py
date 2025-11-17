# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.accounts.report.balance_sheet.balance_sheet import execute
from erpnext.accounts.report.balance_sheet import balance_sheet


class TestBalanceSheet(FrappeTestCase):
	def test_balance_sheet(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_sales_invoice,
		)

		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company 6'")
		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company 6'")
		frappe.db.sql("delete from `tabGL Entry` where company='_Test Company 6'")

		make_purchase_invoice(
			company="_Test Company 6",
			warehouse="Finished Goods - _TC6",
			expense_account="Cost of Goods Sold - _TC6",
			cost_center="Main - _TC6",
			qty=10,
			rate=100,
		)
		create_sales_invoice(
			company="_Test Company 6",
			debit_to="Debtors - _TC6",
			income_account="Sales - _TC6",
			cost_center="Main - _TC6",
			qty=5,
			rate=110,
		)
		filters = frappe._dict(
			company="_Test Company 6",
			period_start_date=today(),
			period_end_date=today(),
			periodicity="Yearly",
		)
		result = execute(filters)[1]
		for account_dict in result:
			if account_dict.get("account") == "Current Liabilities - _TC6":
				self.assertEqual(account_dict.total, 1000)
			if account_dict.get("account") == "Current Assets - _TC6":
				self.assertEqual(account_dict.total, 550)
	
	def setUp(self):
		self.filters = frappe._dict(
			company="_Test Company",
			from_fiscal_year="2023",
			to_fiscal_year="2023",
			period_start_date=today(),
			period_end_date=today(),
			filter_based_on="Fiscal Year",
			periodicity="Yearly",
			accumulated_values=0,
			presentation_currency="INR",
		)

	def test_balance_sheet_TC_ACC_370(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_sales_invoice,
		)

		frappe.db.sql("delete from `tabPurchase Invoice` where company='_Test Company 6'")
		frappe.db.sql("delete from `tabSales Invoice` where company='_Test Company 6'")
		frappe.db.sql("delete from `tabGL Entry` where company='_Test Company 6'")

		make_purchase_invoice(
			company="_Test Company",
			warehouse="Finished Goods - _TC",
			expense_account="Cost of Goods Sold - _TC",
			cost_center="Main - _TC",
			qty=10,
			rate=100,
		)
		create_sales_invoice(
			company="_Test Company",
			debit_to="Debtors - _TC",
			income_account="Sales - _TC",
			cost_center="Main - _TC",
			qty=5,
			rate=110,
		)
		filters = frappe._dict(
			company="_Test Company",
			period_start_date=today(),
			period_end_date=today(),
			periodicity="Yearly",
		)
		result = execute(filters)[1]
		for account_dict in result:
			if account_dict.get("account") == "Current Liabilities - _TC":
				self.assertGreater(account_dict.total, 0)
			if account_dict.get("account") == "Current Assets - _TC":
				self.assertGreater(account_dict.total, 0)

	def test_balance_sheet_with_opening_balance_TC_ACC_386(self):
		filters = frappe._dict(
			company="_Test Company",
			period_start_date=today(),
			period_end_date=today(),
			filter_based_on="Date Range",
			periodicity="Yearly",
			accumulated_values=0,
		)

		fake_period_list = [frappe._dict(key="2023", year_start_date=today(), year_end_date=today())]
		balance_sheet.get_period_list = lambda *a, **kw: fake_period_list

		asset = [
			{"account_name": "Asset Account", "account": "Asset", "2023": 200},
			{"account_name": "Asset Total", "account": "Asset Total", "2023": 100, "opening_balance": 500},
		]
		liability = [
			{"account_name": "Liability Account", "account": "Liability", "2023": 50},
			{"account_name": "Liability Total", "account": "Liability Total", "2023": 0, "opening_balance": 100},
		]
		equity = [
			{"account_name": "Equity Account", "account": "Equity", "2023": 30},
			{"account_name": "Equity Total", "account": "Equity Total", "2023": 0, "opening_balance": 100},
		]


		balance_sheet.get_data = lambda *a, **kw: (
			asset if a[1] == "Asset"
			else liability if a[1] == "Liability"
			else equity
		)

		columns, data, msg, chart, summary, primitive = balance_sheet.execute(filters)
		self.assertTrue(any("Unclosed Fiscal Years Profit / Loss" in d.get("account_name", "") for d in data))
		self.assertIn("Previous Financial Year is not closed", msg)
		self.assertIsInstance(summary, list)
		self.assertIsInstance(primitive, (int, float))


	def test_balance_sheet_growth_view_TC_ACC_387(self):
		filters = frappe._dict(
			company="_Test Company",
			period_start_date=today(),
			period_end_date=today(),
			filter_based_on="Date Range",
			periodicity="Yearly",
			accumulated_values=0,
			selected_view="Growth",
		)

		fake_period_list = [frappe._dict(key="2023", year_start_date=today(), year_end_date=today())]
		balance_sheet.get_period_list = lambda *a, **kw: fake_period_list

		# Fake data for Asset, Liability, Equity
		asset = [
			{"account_name": "Asset Account", "account": "Asset", "2023": 100},
			{"account_name": "Asset Total", "account": "Asset Total", "2023": 200},
		]
		liability = [
			{"account_name": "Liability Account", "account": "Liability", "2023": 50},
			{},
		]
		equity = [
			{"account_name": "Equity Account", "account": "Equity", "2023": 30},
			{},
		]

		balance_sheet.get_data = lambda *a, **kw: (
			asset if a[1] == "Asset"
			else liability if a[1] == "Liability"
			else equity
		)

		columns, data, msg, chart, summary, primitive = balance_sheet.execute(filters)
		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)
		self.assertIsInstance(summary, list)
		self.assertIsInstance(primitive, (int, float))
		self.assertTrue(any("account_name" in d for d in data))
