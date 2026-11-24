# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate


class BankAccountBalance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		balance: DF.Currency
		bank_account: DF.Link
		company: DF.Link | None
		date: DF.Date
	# end: auto-generated types

	def validate(self):
		if not frappe.db.get_value("Bank Account", self.bank_account, "is_company_account"):
			frappe.throw(_("Closing balances can only be recorded for company bank accounts."))

		if frappe.db.exists(
			self.doctype,
			{"bank_account": self.bank_account, "date": self.date, "name": ["!=", self.name]},
		):
			frappe.throw(
				_("A closing balance already exists for Bank Account {0} on {1}.").format(
					self.bank_account, formatdate(self.date)
				),
				frappe.DuplicateEntryError,
			)


def on_doctype_update():
	frappe.db.add_unique("Bank Account Balance", ["bank_account", "date"])
