# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
	AccountsReceivableSummary,
)
from erpnext.accounts.report.consolidated_accounts_receivable.consolidated_accounts_receivable import (
	add_company_columns,
	get_consolidated_companies,
	rows_per_company,
)

# What a party owes (or is owed) across companies that need not be related to each other.


def execute(filters=None):
	args = {
		"account_type": "Receivable",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return ConsolidatedReceivablePayableSummary(filters).run(args)


class ConsolidatedReceivablePayableSummary(AccountsReceivableSummary):
	def run(self, args):
		self.companies = get_consolidated_companies(self.filters)

		return super().run(args)

	def get_columns(self):
		super().get_columns()
		add_company_columns(self.columns)

	def get_data(self, args):
		self.data = []
		for rows in self.get_rows_by_party(args).values():
			self.data.extend(rows)
			self.data.append(self.total_row(rows))

	def get_rows_by_party(self, args):
		"""Rows of every company, regrouped so a party's companies sit together."""
		by_party = OrderedDict()
		for row in rows_per_company(self.companies, self.filters, args, AccountsReceivableSummary):
			by_party.setdefault(row.party, []).append(row)

		return by_party

	def total_row(self, rows):
		# `bold` is picked up by the formatter in the report's js
		total = frappe._dict(
			party_type=_("Total"),
			party="",
			company="",
			currency=rows[0].get("currency"),
			bold=1,
		)
		for row in rows:
			for field, value in row.items():
				# `advance` arrives as an int when there is none, so don't filter on float alone
				if isinstance(value, int | float) and not isinstance(value, bool):
					total[field] = flt(total.get(field)) + value

		return total
