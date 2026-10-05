# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.utils import today

from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.accounts.report.cash_flow.cash_flow import execute
from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestCashFlow(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company"

	def run_report(self, **extra):
		fiscal_year, year_start, year_end = get_fiscal_year(today(), company=self.company)
		filters = frappe._dict(
			company=self.company,
			from_fiscal_year=fiscal_year,
			to_fiscal_year=fiscal_year,
			period_start_date=year_start,
			period_end_date=year_end,
			filter_based_on="Fiscal Year",
			periodicity="Yearly",
			accumulated_values=0,
			**extra,
		)
		return execute(filters)[1]

	def get_row(self, label, **extra):
		rows = self.run_report(**extra)
		return next(row for row in rows if label in str(row.get("section_name") or row.get("account_name")))

	def test_presentation_currency_converts_account_type_rows(self):
		make_journal_entry("Office Equipment - _TC", "Cash - _TC", 4000, posting_date=today(), submit=True)

		with patch("erpnext.accounts.report.utils.get_rate_as_at", return_value=80):
			row = self.get_row("Net Change in Fixed Asset", presentation_currency="USD")

		self.assertEqual(row["total"], self.get_row("Net Change in Fixed Asset")["total"] / 80)
		self.assertEqual(row["currency"], "USD")
