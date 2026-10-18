# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form


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

	@property
	def clearance_date(self):
		# Bank clearance writes the date on the Payment Entry only, so read it from there
		if self.payment_entry:
			return frappe.db.get_value("Payment Entry", self.payment_entry, "clearance_date")

	def check_if_latest(self):
		# Every cheque writer locks the book, then the cheque. Frappe locks this cheque in the
		# parent method, so lock the book first, unless the book is cancelling and holds its lock.
		if self.cheque_book and not self.flags.cancelling_book:
			frappe.db.get_value("Cheque Book", self.cheque_book, "name", for_update=True)
		super().check_if_latest()

	def validate(self):
		# Cheque Book makes cheques with a bulk insert, so only a manual insert or save gets here
		self.refuse_manual_change()

	def before_update_after_submit(self):
		self.refuse_manual_change()

	def on_update_after_submit(self):
		frappe.get_doc("Cheque Book", self.cheque_book, for_update=True).update_status()

	def before_cancel(self):
		self.refuse_manual_change()
		self.status = "Cancelled"

	def on_cancel(self):
		if not self.flags.cancelling_book:
			frappe.get_doc("Cheque Book", self.cheque_book, for_update=True).update_status()

	@frappe.whitelist(methods=["POST"])
	def cancel_with_reason(self, reason: str, remarks: str | None = None):
		"""Cancel a spoiled or lost cheque that no payment uses."""
		if self.status == "Issued":
			frappe.throw(
				_("Cheque {0} is used in {1}. Cancel the Payment Entry to cancel the cheque.").format(
					frappe.bold(self.cheque_no), get_link_to_form("Payment Entry", self.payment_entry)
				)
			)
		self.void(require_reason(reason), remarks)

	def issue(self, payment_entry: str):
		"""Record the payment that uses this cheque. The fetched fields copy its party and amount."""
		self.status = "Issued"
		self.payment_entry = payment_entry
		self.save_as_system()

	def keep_cancellation_reason(self, reason: str, remarks: str | None):
		"""Store why the cheque is cancelled, so that its payment cancel can use it."""
		self.cancellation_reason = reason
		self.remarks = remarks
		self.save_as_system()

	def void(self, reason: str | None = None, remarks: str | None = None):
		"""Cancel the cheque and record why. The caller decides if the cheque can be cancelled."""
		self.cancellation_reason = reason
		self.remarks = remarks
		self.flags.system_change = True
		self.cancel()

	def save_as_system(self):
		self.flags.system_change = True
		self.flags.ignore_permissions = True
		self.save()

	def refuse_manual_change(self):
		if not self.flags.system_change:
			frappe.throw(
				_(
					"A cheque changes only through its Cheque Book, its Payment Entry or Cancel Cheque with a reason"
				),
				title=_("Cheque is read only"),
			)


def require_reason(reason: str) -> str:
	if not reason.strip():
		frappe.throw(_("Enter a reason to cancel the cheque"), frappe.MandatoryError)
	return reason.strip()
