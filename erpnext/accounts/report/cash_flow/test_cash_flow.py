# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import getdate

from erpnext.accounts.report.cash_flow.cash_flow import execute
from erpnext.accounts.report.financial_statements import build_period_list, is_dimension_grouped
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestCashFlow(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()

	def test_group_by_dimension(self):
		filters = frappe._dict(
			company=self.company,
			period_start_date=getdate(),
			period_end_date=getdate(),
			filter_based_on="Date Range",
			periodicity="Yearly",
			accumulated_values=False,
			group_by_dimension="Cost Center",
			show_opening_and_closing_balance=False,
			presentation_currency=None,
			finance_book=None,
		)

		period_list = build_period_list(filters)
		self.assertTrue(period_list)
		self.assertTrue(is_dimension_grouped(period_list))

		columns, data, *_ = execute(filters)

		dim_cols = [c for c in columns if c.get("dimension_value")]
		self.assertTrue(len(dim_cols) > 0)
