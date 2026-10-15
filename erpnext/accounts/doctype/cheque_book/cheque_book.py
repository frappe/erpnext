# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ChequeBook(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		bank_account: DF.Link
		cheque_end_no: DF.Data
		cheque_start_no: DF.Data
		company: DF.Link | None
		no_of_cheques: DF.Int
		status: DF.Literal["Draft", "Submitted", "Finished", "Disabled", "Cancelled"]
	# end: auto-generated types

	@property
	def current_account(self):
		if self.bank_account:
			return frappe.db.get_value("Bank Account", self.bank_account, "account")
