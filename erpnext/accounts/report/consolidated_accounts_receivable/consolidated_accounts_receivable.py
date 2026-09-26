# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport

# Outstanding invoices of a party across companies that need not be related to each other.


def execute(filters=None):
	args = {
		"account_type": "Receivable",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return ConsolidatedReceivablePayable(filters).run(args)


class ConsolidatedReceivablePayable(ReceivablePayableReport):
	def run(self, args):
		self.companies = self.filters.get("companies") or []
		self.args = args  # the engine's get_data() takes no arguments

		return super().run(args)

	def get_columns(self):
		super().get_columns()
		add_company_columns(self.columns)

	def get_data(self):
		self.data = []
		for rows in self.get_grouped_rows("party").values():
			self.data.extend(rows)
			if self.filters.get("group_by_party"):
				self.data.append(self.party_subtotal(rows))
				self.data.append({})  # blank separator, like the engine's own grouping

	def get_grouped_rows(self, group_by):
		"""Rows of every company, regrouped so those sharing `group_by` sit together."""
		grouped = OrderedDict()
		for row in rows_per_company(self.companies, self.filters, self.args, ReceivablePayableReport):
			grouped.setdefault(row.get(group_by), []).append(row)

		return grouped

	def party_subtotal(self, rows):
		return self.subtotal(rows, party=rows[0].party)

	def subtotal(self, rows, **label):
		subtotal = frappe._dict(currency=rows[0].get("currency"), bold=1, **label)
		for field in self.get_currency_fields():
			subtotal[field] = sum(flt(row.get(field)) for row in rows)

		return subtotal


def rows_per_company(companies, filters, args, engine):
	"""Run `engine` once per company, tagging every row with the company it came from."""
	for company in companies:
		# subtotals are appended once per group by the caller, not once per company
		company_filters = frappe._dict(filters, company=company, group_by_party=0)
		company_filters.pop("companies", None)

		for row in engine(company_filters).run(args)[1]:
			row.company = company
			yield row


def add_company_columns(columns):
	"""The company a row came from, right after the party columns."""
	columns.insert(
		company_column_index(columns),
		dict(
			label=_("Company"),
			fieldname="company",
			fieldtype="Link",
			options="Company",
			width=180,
			sticky=True,
		),
	)


def company_column_index(columns):
	fieldnames = [column["fieldname"] for column in columns]
	for fieldname in ("party_name", "party"):
		if fieldname in fieldnames:
			return fieldnames.index(fieldname) + 1

	return 0
