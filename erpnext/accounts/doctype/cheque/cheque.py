# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Cheque(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amount: DF.Currency
		bank_account: DF.Link
		cancellation_reason: DF.Autocomplete | None
		cheque_book: DF.Link
		cheque_date: DF.Date | None
		cheque_no: DF.Data
		company: DF.Link
		currency: DF.Link | None
		party_name: DF.Data | None
		payment_entry: DF.Link | None
		remarks: DF.SmallText | None
		status: DF.Literal["Available", "Issued", "Cancelled"]
	# end: auto-generated types

	def check_if_latest(self):
		# Every cheque writer locks the book, then the cheque.
		# Frappe locks this cheque in the parent method, so lock the book first.
		frappe.db.get_value("Cheque Book", self.cheque_book, "name", for_update=True)
		super().check_if_latest()

	def before_cancel(self):
		self.status = "Cancelled"

	def on_cancel(self):
		frappe.get_doc("Cheque Book", self.cheque_book, for_update=True).update_status()
