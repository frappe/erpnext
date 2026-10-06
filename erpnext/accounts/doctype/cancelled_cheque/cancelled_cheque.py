# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form

from erpnext.accounts.doctype.cheque_book.cheque_book import ChequeBook
from erpnext.accounts.doctype.cheque_usage.cheque_usage import (
	claim_cheque,
	get_cheque_usage,
	release_cheque,
)


class CancelledCheque(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		cheque_book: DF.Link
		cheque_no: DF.Data
		payment_entry: DF.Link | None
		reason: DF.Autocomplete
		remarks: DF.SmallText | None
	# end: auto-generated types

	def before_validate(self):
		self.cheque_no = ChequeBook.format_cheque_no(self.cheque_no)

	def get_invalid_links(self, is_submittable=False, link_value_cache=None):
		invalid, cancelled = super().get_invalid_links(is_submittable, link_value_cache)
		# This audit link intentionally points to a cancelled payment; validate checks its identity.
		return invalid, [link for link in cancelled if link[0] != "payment_entry"]

	def validate(self):
		# Share the book lock with Payment Entry submission before checking whether the cheque is used.
		book = frappe.get_doc("Cheque Book", self.cheque_book, for_update=True)
		if book.docstatus != 1:
			frappe.throw(_("Cheque Book {0} is not submitted").format(frappe.bold(book.name)))

		if not book.is_in_range(self.cheque_no):
			frappe.throw(
				_("Cheque No {0} is not in the range {1} - {2}").format(
					frappe.bold(self.cheque_no), book.cheque_start_no, book.cheque_end_no
				)
			)

		usage = get_cheque_usage(book.name, self.cheque_no, for_update=True)
		if usage and usage.source_type == "Payment Entry":
			frappe.throw(
				_("Cheque No {0} is used in {1}. Cancel the Payment Entry first.").format(
					frappe.bold(self.cheque_no), get_link_to_form("Payment Entry", usage.source_name)
				)
			)
		if usage and usage.source_type == self.doctype and usage.source_name != self.name:
			frappe.throw(
				_("Cheque No {0} is already marked as cancelled in {1}").format(
					frappe.bold(self.cheque_no), get_link_to_form(self.doctype, usage.source_name)
				)
			)

		if self.payment_entry:
			linked_payment = frappe.db.get_value(
				"Payment Entry",
				self.payment_entry,
				["docstatus", "cheque_book", "reference_no"],
				as_dict=True,
			)
			if (
				not linked_payment
				or linked_payment.docstatus != 2
				or linked_payment.cheque_book != book.name
				or not (linked_payment.reference_no or "").isdigit()
				or int(linked_payment.reference_no) != int(self.cheque_no)
			):
				frappe.throw(
					_("Payment Entry {0} must be cancelled and use cheque {1} from Cheque Book {2}").format(
						frappe.bold(self.payment_entry), frappe.bold(self.cheque_no), frappe.bold(book.name)
					)
				)

	def on_submit(self):
		book = frappe.get_doc("Cheque Book", self.cheque_book, for_update=True)
		claim_cheque(book, self.cheque_no, self.doctype, self.name, self.reason)
		book.advance_next_cheque_no(self.cheque_no)

	def before_cancel(self):
		frappe.get_doc("Cheque Book", self.cheque_book, for_update=True)

	def on_cancel(self):
		book = frappe.get_doc("Cheque Book", self.cheque_book, for_update=True)
		release_cheque(book, self.cheque_no, self.doctype, self.name)
		book.advance_next_cheque_no(self.cheque_no, freed=True)

	def on_trash(self):
		frappe.throw(_("Cancelled Cheque records cannot be deleted. Cancel the record to reverse it."))
