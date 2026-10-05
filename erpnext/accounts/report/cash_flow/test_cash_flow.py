# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from erpnext.accounts.report.cash_flow.cash_flow import execute
from erpnext.accounts.utils import get_fiscal_year


class TestCashFlow(FrappeTestCase):
	def setUp(self):
		self.company = "_Test Company"

	def tearDown(self):
		frappe.db.rollback()

	def net_change_in_cash(self):
		"""Run the report for the current fiscal year and return the Net Change in Cash total."""
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
		)
		rows = execute(filters)[1]
		row = next(row for row in rows if row.get("section") == "'Net Change in Cash'")
		return row["total"]

	def test_opening_entries_are_not_cash_flows(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		before = self.net_change_in_cash()
		opening_entry = make_journal_entry(
			"Office Equipments - _TC", "Temporary Opening - _TC", 800, posting_date=today(), save=False
		)
		opening_entry.is_opening = "Yes"
		opening_entry.submit()

		self.assertEqual(self.net_change_in_cash() - before, 0)
