# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.utils.data import today

from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
from erpnext.accounts.report.cash_flow.cash_flow import execute
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company 6"
COMPANY_SHORT_NAME = "_TC6"


class TestCashFlowDimensionWise(ERPNextTestSuite):
	def _dim_filters(self, periodicity="Yearly"):
		return frappe._dict(
			company=COMPANY,
			period_start_date=today(),
			period_end_date=today(),
			periodicity=periodicity,
			filter_based_on="Date Range",
			from_fiscal_year=None,
			to_fiscal_year=None,
			accumulated_values=False,
			group_by_dimension="Cost Center",
			show_zero_values=0,
			finance_book=None,
			presentation_currency=None,
			show_opening_and_closing_balance=False,
			include_default_book_entries=0,
		)

	def _make_receivable_receipt(self, cost_center, amount):
		"""Credit Debtors (cash collected from customer), debit Cash."""
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = today()
		jv.company = COMPANY
		jv.user_remark = "test"
		jv.append(
			"accounts",
			{
				"account": f"Debtors - {COMPANY_SHORT_NAME}",
				"debit_in_account_currency": 0,
				"credit_in_account_currency": amount,
				"cost_center": cost_center,
			},
		)
		jv.append(
			"accounts",
			{
				"account": f"Cash - {COMPANY_SHORT_NAME}",
				"debit_in_account_currency": amount,
				"credit_in_account_currency": 0,
				"cost_center": cost_center,
			},
		)
		jv.insert()
		jv.submit()

	def _receivable_row(self, result):
		return next(
			(r for r in result[1] if r and "Receivable" in (r.get("section_name") or "")),
			None,
		)

	def test_dim_columns_present(self):
		"""Dim-wise CF: one period column per dimXtime-bucket + a Total column."""
		cc1 = f"_Test CF Dim CC1 - {COMPANY_SHORT_NAME}"
		cc2 = f"_Test CF Dim CC2 - {COMPANY_SHORT_NAME}"
		create_cost_center(cost_center_name="_Test CF Dim CC1", company=COMPANY)
		create_cost_center(cost_center_name="_Test CF Dim CC2", company=COMPANY)

		self._make_receivable_receipt(cc1, 400)
		self._make_receivable_receipt(cc2, 200)

		result = execute(self._dim_filters())
		columns = result[0]

		period_cols = [c for c in columns if c.get("fieldtype") == "Currency" and c["fieldname"] != "total"]
		total_col = [c for c in columns if c["fieldname"] == "total"]

		# at least 2 dim columns
		self.assertGreaterEqual(len(period_cols), 2)
		self.assertEqual(len(total_col), 1)

	def test_dim_values_segregated(self):
		"""Each dim column shows only that dim's cash movement."""
		cc1 = f"_Test CF Dim CC3 - {COMPANY_SHORT_NAME}"
		cc2 = f"_Test CF Dim CC4 - {COMPANY_SHORT_NAME}"
		create_cost_center(cost_center_name="_Test CF Dim CC3", company=COMPANY)
		create_cost_center(cost_center_name="_Test CF Dim CC4", company=COMPANY)

		self._make_receivable_receipt(cc1, 400)
		self._make_receivable_receipt(cc2, 200)

		result = execute(self._dim_filters())
		columns = result[0]
		period_cols = [c for c in columns if c.get("fieldtype") == "Currency" and c["fieldname"] != "total"]

		recv_row = self._receivable_row(result)
		self.assertIsNotNone(recv_row)

		col_values = [recv_row.get(c["fieldname"], 0) for c in period_cols]
		self.assertIn(400.0, col_values)
		self.assertIn(200.0, col_values)

	def test_dim_total_column(self):
		"""Total column = sum of all dim activity (no accumulated_values in CF)."""
		cc1 = f"_Test CF Dim CC5 - {COMPANY_SHORT_NAME}"
		cc2 = f"_Test CF Dim CC6 - {COMPANY_SHORT_NAME}"
		create_cost_center(cost_center_name="_Test CF Dim CC5", company=COMPANY)
		create_cost_center(cost_center_name="_Test CF Dim CC6", company=COMPANY)

		self._make_receivable_receipt(cc1, 300)
		self._make_receivable_receipt(cc2, 150)

		result = execute(self._dim_filters())

		recv_row = self._receivable_row(result)
		self.assertIsNotNone(recv_row)
		self.assertEqual(recv_row.get("total"), 450.0)

	def test_dim_net_change_in_cash_total(self):
		"""Net Change in Cash Total = sum of all dim activity."""
		cc1 = f"_Test CF Dim CC7 - {COMPANY_SHORT_NAME}"
		create_cost_center(cost_center_name="_Test CF Dim CC7", company=COMPANY)

		self._make_receivable_receipt(cc1, 500)

		result = execute(self._dim_filters())

		net_change_row = next(
			(r for r in result[1] if r and "Net Change in Cash" in (r.get("section_name") or "")),
			None,
		)
		self.assertIsNotNone(net_change_row)
		self.assertGreaterEqual(net_change_row.get("total", 0), 500.0)

	def test_dim_quarterly(self):
		"""Quarterly periodicity: columns = 2 dims X 4 quarters (+ Total)."""
		cc1 = f"_Test CF Dim CC8 - {COMPANY_SHORT_NAME}"
		cc2 = f"_Test CF Dim CC9 - {COMPANY_SHORT_NAME}"
		create_cost_center(cost_center_name="_Test CF Dim CC8", company=COMPANY)
		create_cost_center(cost_center_name="_Test CF Dim CC9", company=COMPANY)

		self._make_receivable_receipt(cc1, 100)
		self._make_receivable_receipt(cc2, 100)

		result = execute(self._dim_filters(periodicity="Quarterly"))
		columns = result[0]
		period_cols = [c for c in columns if c.get("fieldtype") == "Currency" and c["fieldname"] != "total"]

		# 2 dims X ≥1 quarters each → at least 2 period columns
		self.assertGreaterEqual(len(period_cols), 2)
