# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from erpnext.accounts.utils import get_advance_payment_doctypes, update_voucher_outstanding


class AdvancePaymentLedgerEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		against_voucher_no: DF.DynamicLink | None
		against_voucher_type: DF.Link | None
		amount: DF.Currency
		base_amount: DF.Currency
		company: DF.Link | None
		currency: DF.Link | None
		delinked: DF.Check
		event: DF.Data | None
		exchange_rate: DF.Float
		voucher_no: DF.DynamicLink | None
		voucher_type: DF.Link | None
	# end: auto-generated types

	def on_update(self):
		if (
			self.against_voucher_type in get_advance_payment_doctypes()
			and self.flags.update_outstanding == "Yes"
			and not frappe.flags.is_reverse_depr_entry
		):
			update_voucher_outstanding(self.against_voucher_type, self.against_voucher_no, None, None, None)


def on_doctype_update():
	frappe.db.add_index(
		"Advance Payment Ledger Entry",
		["against_voucher_type", "against_voucher_no"],
	)

	frappe.db.add_index(
		"Advance Payment Ledger Entry",
		["voucher_type", "voucher_no"],
	)
