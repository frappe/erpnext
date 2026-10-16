# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.report.financial_ratios.financial_ratios import update_balances


class TestFinancialRatios(FrappeTestCase):
	def test_fixed_asset_balances_combine_groups_of_same_type(self):
		rows = [
			("Assets", None, "", 1, 54000),
			("Fixed Assets", "Assets", "Fixed Asset", 1, 13000),
			("Buildings", "Fixed Assets", "", 0, 10000),
			("Plant Group", "Fixed Assets", "Fixed Asset", 1, 3000),
			("Plant", "Plant Group", "", 0, 3000),
			("Solar Power System", "Assets", "Fixed Asset", 1, 5000),
			("Solar Panels", "Solar Power System", "", 0, 5000),
			("Cash", "Assets", "Cash", 0, 36000),
		]
		balances, totals, quick_assets = {}, {}, {}
		update_balances(
			balances, totals, "Fixed Asset", "year", self.make_report_rows(rows), "Asset", quick_assets
		)

		self.assertEqual(balances["year"], 18000)
		self.assertEqual(totals["year"], 54000)
		self.assertEqual(quick_assets["year"], 36000)

	def test_direct_expense_combines_groups_of_same_type(self):
		rows = [
			("Expenses", None, "", 1, 500),
			("Direct Expenses", "Expenses", "Direct Expense", 1, 200),
			("Cost of Goods Sold", "Direct Expenses", "Cost of Goods Sold", 0, 200),
			("Freight Group", "Expenses", "Direct Expense", 1, 300),
			("Freight", "Freight Group", "", 0, 300),
		]
		balances = {}
		update_balances(balances, {}, "Direct Expense", "year", self.make_report_rows(rows), "Expense")

		self.assertEqual(balances["year"], 500)

	def make_report_rows(self, rows):
		return [
			frappe._dict(
				account=account,
				parent_account=parent,
				account_type=account_type,
				is_group=is_group,
				year=balance,
			)
			for account, parent, account_type, is_group, balance in rows
		]
