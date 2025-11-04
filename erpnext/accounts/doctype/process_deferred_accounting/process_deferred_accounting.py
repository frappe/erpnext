# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.accounts.deferred_revenue import (
	build_conditions,
	convert_deferred_expense_to_expense,
	convert_deferred_revenue_to_income,
)
from erpnext.accounts.general_ledger import make_gl_entries


class ProcessDeferredAccounting(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		amended_from: DF.Link | None
		company: DF.Link
		end_date: DF.Date
		posting_date: DF.Date
		start_date: DF.Date
		type: DF.Literal["", "Income", "Expense"]
	# end: auto-generated types

	def validate(self):
		if self.end_date < self.start_date:
			frappe.throw(_("End date cannot be before start date"))

	def on_submit(self):
		conditions = build_conditions(self.type, self.account, self.company)
		if self.type == "Income":
			convert_deferred_revenue_to_income(self.name, self.start_date, self.end_date, conditions)
		else:
			convert_deferred_expense_to_expense(self.name, self.start_date, self.end_date, conditions)

	def on_cancel(self):
		self.ignore_linked_doctypes = ["GL Entry"]
		gl_entries = frappe.get_all(
			"GL Entry",
			fields=["*"],
			filters={"against_voucher_type": self.doctype, "against_voucher": self.name},
		)

		make_gl_entries(gl_map=gl_entries, cancel=1)
