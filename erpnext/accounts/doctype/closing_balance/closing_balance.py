# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import List

import frappe
from frappe.model.document import Document

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)


class ClosingBalance(Document):
	def aggregate_with_last_closing_balance(self, accounting_dimensions: List[str]):
		closing_balance = frappe.qb.DocType("Closing Balance")

		query = (
			frappe.qb.from_(closing_balance)
			.select(closing_balance.debit, closing_balance.credit)
			.where(
				closing_balance.closing_date < self.closing_date,
			)
		)

		for dimension in accounting_dimensions:
			query = query.where(closing_balance[dimension] == self.get(dimension))

		query = query.orderby(closing_balance.closing_date, order=frappe.qb.desc).limit(1)

		last_closing_balance = query.run(as_dict=1)

		if last_closing_balance:
			self.debit += last_closing_balance[0].debit
			self.credit += last_closing_balance[0].credit


def make_closing_entries(closing_entries):
	accounting_dimensions = get_accounting_dimensions()
	for entry in closing_entries:
		cle = frappe.new_doc("Closing Balance")
		cle.update(entry)
		cle.aggregate_with_last_closing_balance(accounting_dimensions)
		cle.submit()
