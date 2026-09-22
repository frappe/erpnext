# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form


class CancelledCheque(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cheque_book: DF.Link
		cheque_no: DF.Data
		payment_entry: DF.Link | None
		reason: DF.Data
		remarks: DF.SmallText | None
	# end: auto-generated types

	def before_insert(self):
		# Runs before naming, so the name gets the padded number
		self.cheque_no = frappe.get_doc("Cheque Book", self.cheque_book).format_cheque_no(self.cheque_no)

	def validate(self):
		book = frappe.get_doc("Cheque Book", self.cheque_book)
		if book.docstatus != 1:
			frappe.throw(_("Cheque Book {0} is not submitted").format(frappe.bold(book.name)))

		if not book.is_in_range(self.cheque_no):
			frappe.throw(
				_("Cheque No {0} is not in the range {1} - {2}").format(
					frappe.bold(self.cheque_no), book.cheque_start_no, book.cheque_end_no
				)
			)

		if payment_entry := frappe.db.get_value(
			"Payment Entry", {"cheque_book": book.name, "reference_no": self.cheque_no, "docstatus": 1}
		):
			frappe.throw(
				_("Cheque No {0} is used in {1}. Cancel the Payment Entry first.").format(
					frappe.bold(self.cheque_no), get_link_to_form("Payment Entry", payment_entry)
				)
			)

	def after_insert(self):
		frappe.get_doc("Cheque Book", self.cheque_book).advance_next_cheque_no(self.cheque_no)
