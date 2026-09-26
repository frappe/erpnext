# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import OrderedDict

import frappe
from frappe import _
from frappe.model import numeric_fieldtypes
from frappe.utils import flt

from erpnext.accounts.report.accounts_receivable.accounts_receivable import ReceivablePayableReport
from erpnext.accounts.report.consolidated_financial_statement.consolidated_financial_statement import (
	get_subsidiary_companies,
)

# Outstanding invoices of a party across companies that need not be related to each other.


def execute(filters=None):
	args = {
		"account_type": "Receivable",
		"naming_by": ["Selling Settings", "cust_master_name"],
	}
	return ConsolidatedReceivablePayable(filters).run(args)


class ConsolidatedReceivablePayable(ReceivablePayableReport):
	def run(self, args):
		self.companies = get_consolidated_companies(self.filters)
		self.args = args  # the engine's get_data() takes no arguments
		columns, data, _message, chart, _report_summary, skip_total_row = super().run(args)

		if self.filters.get("group_by_company"):
			# a grand total would double count the company subtotals
			skip_total_row = 1

		return columns, data, None, chart, None, skip_total_row

	def get_columns(self):
		super().get_columns()
		add_company_columns(self.columns)

	def get_data(self):
		# party wins when both are checked
		if self.filters.get("group_by_party"):
			group_by, subtotal_of = "party", self.party_subtotal
		elif self.filters.get("group_by_company"):
			group_by, subtotal_of = "company", self.company_subtotal
		else:
			group_by, subtotal_of = "party", None

		self.data = []
		for rows in self.get_grouped_rows(group_by).values():
			self.data.extend(rows)
			if subtotal_of:
				self.data.append(subtotal_of(rows))
				self.data.append({})  # blank separator, like the engine's own grouping

	def get_grouped_rows(self, group_by):
		"""Rows of every company, regrouped so those sharing `group_by` sit together."""
		grouped = OrderedDict()
		for row in rows_per_company(self.companies, self.filters, self.args, ReceivablePayableReport):
			grouped.setdefault(row.get(group_by), []).append(row)

		return grouped

	def party_subtotal(self, rows):
		return self.subtotal(rows, party=rows[0].party)

	def company_subtotal(self, rows):
		return self.subtotal(rows, company=rows[0].company)

	def subtotal(self, rows, **label):
		subtotal = frappe._dict(currency=rows[0].get("currency"), bold=1, **label)
		for field in self.get_currency_fields():
			subtotal[field] = sum(flt(row.get(field)) for row in rows)

		return subtotal


def rows_per_company(companies, filters, args, engine):
	"""Run `engine` once per company, tagging every row with the company it came from."""
	# every parent in one query, not a lookup per company
	parents = dict(
		frappe.get_all(
			"Company",
			filters={"name": ["in", companies]},
			fields=["name", "parent_company"],
			as_list=True,
		)
	)

	for company in companies:
		# subtotals are appended once per group by the caller, not once per company
		company_filters = frappe._dict(filters, company=company, group_by_party=0)
		company_filters.pop("companies", None)

		for row in engine(company_filters).run(args)[1]:
			row.company, row.parent_company = company, parents.get(company)
			yield row


def get_consolidated_companies(filters):
	"""Selected companies, a group company standing for the companies under it."""
	companies = []
	for selected in filters.get("companies") or []:
		for company in get_subsidiary_companies(selected):
			if company not in companies:
				companies.append(company)

	return companies


def add_company_columns(columns):
	"""Company and its parent, right after the party columns, plus header alignment."""
	at = company_column_index(columns)
	columns.insert(
		at,
		dict(
			label=_("Company"),
			fieldname="company",
			fieldtype="Link",
			options="Company",
			width=180,
			sticky=True,
		),
	)
	columns.insert(
		at + 1,
		dict(
			label=_("Parent Company"),
			fieldname="parent_company",
			fieldtype="Link",
			options="Company",
			width=160,
		),
	)

	# datatable guesses alignment from the first row, which misreads an empty column
	for column in columns:
		column["align"] = "right" if column["fieldtype"] in numeric_fieldtypes else "left"


def company_column_index(columns):
	fieldnames = [column["fieldname"] for column in columns]
	for fieldname in ("party_name", "party"):
		if fieldname in fieldnames:
			return fieldnames.index(fieldname) + 1

	return 0
