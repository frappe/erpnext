# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils.data import today

from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
from erpnext.accounts.report.balance_sheet.balance_sheet import execute
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company 6"
COMPANY_SHORT_NAME = "_TC6"


class TestBalanceSheetDimensionWise(ERPNextTestSuite):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_account("Dim Bank", f"Bank Accounts - {COMPANY_SHORT_NAME}", COMPANY)

	def _dim_filters(self, accumulated_values=False, periodicity="Yearly"):
		return frappe._dict(
			company=COMPANY,
			period_start_date=today(),
			period_end_date=today(),
			periodicity=periodicity,
			filter_based_on="Date Range",
			from_fiscal_year=None,
			to_fiscal_year=None,
			accumulated_values=accumulated_values,
			group_by_dimension="Cost Center",
			show_zero_values=0,
			finance_book=None,
			presentation_currency=None,
		)

	def _make_jv(self, bank_amount, income_amount, cost_center):
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = today()
		jv.company = COMPANY
		jv.user_remark = "test"
		jv.append(
			"accounts",
			{
				"account": f"Dim Bank - {COMPANY_SHORT_NAME}",
				"debit_in_account_currency": bank_amount,
				"credit_in_account_currency": 0,
				"cost_center": cost_center,
			},
		)
		jv.append(
			"accounts",
			{
				"account": f"Sales - {COMPANY_SHORT_NAME}",
				"debit_in_account_currency": 0,
				"credit_in_account_currency": income_amount,
				"cost_center": cost_center,
			},
		)
		jv.insert()
		jv.submit()

	def _totals(self, result):
		return {r["account_name"]: r["total"] for r in result[1] if r and "total" in r}

	def _summary(self, result):
		return {s["label"]: s["value"] for s in (result[4] or [])}

	def test_dim_not_accumulated(self):
		"""Two cost centers in separate columns; Total = sum across both dims."""
		cc1 = f"_Test BS Dim CC1 - {COMPANY_SHORT_NAME}"
		cc2 = f"_Test BS Dim CC2 - {COMPANY_SHORT_NAME}"
		create_cost_center(cost_center_name="_Test BS Dim CC1", company=COMPANY)
		create_cost_center(cost_center_name="_Test BS Dim CC2", company=COMPANY)

		self._make_jv(bank_amount=500, income_amount=500, cost_center=cc1)
		self._make_jv(bank_amount=300, income_amount=300, cost_center=cc2)

		result = execute(self._dim_filters(accumulated_values=False))
		totals = self._totals(result)

		self.assertEqual(totals.get("Dim Bank"), 800.0)

		summary = self._summary(result)
		self.assertGreaterEqual(summary.get("Total Asset"), 800.0)

	def test_dim_accumulated_total_column(self):
		"""
		accumulated_values=True, Yearly: one period per dim.
		Total column = last-period per dim summed (not a running cross-dim sum).
		"""
		cc1 = f"_Test BS Dim CC3 - {COMPANY_SHORT_NAME}"
		cc2 = f"_Test BS Dim CC4 - {COMPANY_SHORT_NAME}"
		create_cost_center(cost_center_name="_Test BS Dim CC3", company=COMPANY)
		create_cost_center(cost_center_name="_Test BS Dim CC4", company=COMPANY)

		self._make_jv(bank_amount=700, income_amount=700, cost_center=cc1)
		self._make_jv(bank_amount=200, income_amount=200, cost_center=cc2)

		result = execute(self._dim_filters(accumulated_values=True))
		totals = self._totals(result)

		self.assertEqual(totals.get("Dim Bank"), 900.0)

		summary = self._summary(result)
		self.assertGreaterEqual(summary.get("Total Asset"), 900.0)

	def test_dim_provisional_profit_loss_total(self):
		"""Provisional Profit/Loss Total = last-period-per-dim sum."""
		cc1 = f"_Test BS Dim CC5 - {COMPANY_SHORT_NAME}"
		create_cost_center(cost_center_name="_Test BS Dim CC5", company=COMPANY)

		self._make_jv(bank_amount=400, income_amount=400, cost_center=cc1)

		result = execute(self._dim_filters(accumulated_values=True))
		totals = self._totals(result)

		provisional_total = totals.get("'Provisional Profit / Loss (Credit)'")
		self.assertIsNotNone(provisional_total)
		self.assertGreaterEqual(provisional_total, 400.0)

	def test_dim_columns_per_dim(self):
		"""Period columns = one per dim X time-bucket; Total column is always present."""
		cc1 = f"_Test BS Dim CC6 - {COMPANY_SHORT_NAME}"
		cc2 = f"_Test BS Dim CC7 - {COMPANY_SHORT_NAME}"
		create_cost_center(cost_center_name="_Test BS Dim CC6", company=COMPANY)
		create_cost_center(cost_center_name="_Test BS Dim CC7", company=COMPANY)

		self._make_jv(bank_amount=100, income_amount=100, cost_center=cc1)
		self._make_jv(bank_amount=100, income_amount=100, cost_center=cc2)

		result = execute(self._dim_filters(accumulated_values=False))
		columns = result[0]

		period_cols = [c for c in columns if c.get("fieldtype") == "Currency" and c["fieldname"] != "total"]
		total_col = [c for c in columns if c["fieldname"] == "total"]

		# at least 2 dims X 1 period each
		self.assertGreaterEqual(len(period_cols), 2)
		self.assertEqual(len(total_col), 1)

	def test_dim_quarterly_accumulated(self):
		"""
		Quarterly + accumulated_values=True: Total uses last-quarter balance per dim,
		not a running cross-quarter X cross-dim sum.
		"""
		cc1 = f"_Test BS Dim CC8 - {COMPANY_SHORT_NAME}"
		cc2 = f"_Test BS Dim CC9 - {COMPANY_SHORT_NAME}"
		create_cost_center(cost_center_name="_Test BS Dim CC8", company=COMPANY)
		create_cost_center(cost_center_name="_Test BS Dim CC9", company=COMPANY)

		self._make_jv(bank_amount=600, income_amount=600, cost_center=cc1)
		self._make_jv(bank_amount=150, income_amount=150, cost_center=cc2)

		result = execute(self._dim_filters(accumulated_values=True, periodicity="Quarterly"))
		totals = self._totals(result)

		self.assertEqual(totals.get("Dim Bank"), 750.0)


def create_account(account_name: str, parent_account: str, company: str):
	if frappe.db.exists("Account", {"account_name": account_name, "company": company}):
		return
	acc = frappe.new_doc("Account")
	acc.account_name = account_name
	acc.company = company
	acc.parent_account = parent_account
	acc.insert()
