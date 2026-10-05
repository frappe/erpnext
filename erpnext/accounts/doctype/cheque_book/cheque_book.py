# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_link_to_form

MAX_DIGITS = 6


class ChequeBook(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		amended_from: DF.Link | None
		bank_account: DF.Link
		cheque_book_no: DF.Data
		cheque_end_no: DF.Data
		cheque_start_no: DF.Data
		company: DF.Link | None
		next_cheque_no: DF.Data | None
		no_of_cheques: DF.Int
		status: DF.Literal["Draft", "Submitted", "Finished", "Disabled", "Cancelled"]
	# end: auto-generated types

	def validate(self):
		self.validate_bank_account()
		self.validate_cheque_range()
		self.validate_overlapping_range()

	def before_submit(self):
		self.status = "Submitted"
		# an amended book keeps its place, unless the new range no longer covers it
		if not self.is_in_range(self.next_cheque_no or ""):
			self.next_cheque_no = self.cheque_start_no

	def before_update_after_submit(self):
		if self.has_value_changed("next_cheque_no"):
			frappe.throw(_("Next Cheque No is managed automatically"))

	def validate_bank_account(self):
		bank_account = frappe.db.get_value(
			"Bank Account",
			self.bank_account,
			["is_company_account", "disabled"],
			as_dict=True,
			for_update=True,
		)
		if not bank_account or not bank_account.is_company_account:
			frappe.throw(
				_("Bank Account {0} is not a Company Account").format(frappe.bold(self.bank_account))
			)
		if bank_account.disabled and self.has_value_changed("bank_account"):
			frappe.throw(_("Bank Account {0} is disabled").format(frappe.bold(self.bank_account)))

	def validate_cheque_range(self):
		self.cheque_start_no = (self.cheque_start_no or "").strip()
		self.cheque_end_no = (self.cheque_end_no or "").strip()

		for fieldname in ("cheque_start_no", "cheque_end_no"):
			value = self.get(fieldname)
			if value and not (value.isdigit() and len(value) <= MAX_DIGITS):
				frappe.throw(
					_("{0} must be a number of at most {1} digits").format(
						_(self.meta.get_label(fieldname)), MAX_DIGITS
					)
				)

		self.set_missing_range_value()
		if len(self.cheque_start_no) > MAX_DIGITS or len(self.cheque_end_no) > MAX_DIGITS:
			frappe.throw(_("Cheque numbers must have at most {0} digits").format(MAX_DIGITS))
		self.cheque_start_no = self.cheque_start_no.zfill(MAX_DIGITS)
		self.cheque_end_no = self.cheque_end_no.zfill(MAX_DIGITS)

		if int(self.cheque_end_no) < int(self.cheque_start_no):
			frappe.throw(_("Cheque End No cannot be less than Cheque Start No"))

	def set_missing_range_value(self):
		"""Any two of start no, end no and number of cheques give the third"""
		self.no_of_cheques = cint(self.no_of_cheques)
		if self.no_of_cheques < 0 or (
			self.no_of_cheques == 0 and not (self.cheque_start_no and self.cheque_end_no)
		):
			frappe.throw(_("Number of Cheques must be at least 1"))

		if self.cheque_start_no and self.cheque_end_no:
			self.no_of_cheques = int(self.cheque_end_no) - int(self.cheque_start_no) + 1

		elif self.cheque_start_no and self.no_of_cheques:
			end_no = int(self.cheque_start_no) + self.no_of_cheques - 1
			self.cheque_end_no = str(end_no)

		elif self.cheque_end_no and self.no_of_cheques:
			start_no = int(self.cheque_end_no) - self.no_of_cheques + 1
			if start_no < 0:
				frappe.throw(_("Number of Cheques cannot be more than Cheque End No"))
			self.cheque_start_no = str(start_no)

		else:
			frappe.throw(_("Enter any two of Cheque Start No, Cheque End No and Number of Cheques"))

	def validate_overlapping_range(self):
		# The account lock serializes creation; this locking read sees newly committed ranges.
		other_books = frappe.db.get_values(
			"Cheque Book",
			filters={
				"bank_account": self.bank_account,
				"docstatus": ("<", 2),
				"name": ("!=", self.name or ""),
			},
			fieldname=["name", "cheque_start_no", "cheque_end_no"],
			as_dict=True,
			for_update=True,
		)
		for book in other_books:
			if int(self.cheque_start_no) <= int(book.cheque_end_no) and int(book.cheque_start_no) <= int(
				self.cheque_end_no
			):
				frappe.throw(
					_("Cheque range overlaps with Cheque Book {0} ({1} - {2})").format(
						get_link_to_form("Cheque Book", book.name), book.cheque_start_no, book.cheque_end_no
					)
				)

	def on_cancel(self):
		# Submitted Payment Entries using this book already block the cancellation
		if cheque_no := frappe.db.get_value("Cancelled Cheque", {"cheque_book": self.name}, "cheque_no"):
			frappe.throw(
				_("Cannot cancel {0} because cheque {1} is marked as cancelled").format(
					frappe.bold(self.name), frappe.bold(cheque_no)
				)
			)

		self.db_set("status", "Cancelled")

	@staticmethod
	def format_cheque_no(cheque_no):
		"""Normalize a typed number to six digits."""
		cheque_no = (cheque_no or "").strip()
		return cheque_no.zfill(MAX_DIGITS) if cheque_no.isdigit() else cheque_no

	def is_in_range(self, cheque_no):
		return (
			cheque_no.isdigit()
			and len(cheque_no) == MAX_DIGITS
			and int(self.cheque_start_no) <= int(cheque_no) <= int(self.cheque_end_no)
		)

	def next_no_after(self, cheque_no):
		return str(int(cheque_no) + 1).zfill(MAX_DIGITS)

	def is_used(self, cheque_no):
		return bool(
			frappe.db.get_value("Cancelled Cheque", f"{self.name}-{cheque_no}", for_update=True)
			or frappe.db.get_value(
				"Payment Entry",
				{"cheque_book": self.name, "reference_no": cheque_no, "docstatus": 1},
				for_update=True,
			)
		)

	def advance_next_cheque_no(self, cheque_no, *, freed=False):
		"""Advance after use, or reopen a Finished book when a cheque is freed."""
		if freed:
			cheque_no = self.format_cheque_no(cheque_no)
			if self.status == "Finished" and not self.is_used(cheque_no):
				self.db_set({"next_cheque_no": cheque_no, "status": "Submitted"})
			return

		if cheque_no != self.next_cheque_no and self.is_in_range(self.next_cheque_no):
			return

		next_no = self.next_cheque_no
		if cheque_no == next_no:
			next_no = self.next_no_after(cheque_no)
			if self.is_in_range(next_no):
				occupied = get_occupied_cheque_nos(self, from_no=next_no, for_update=True)
				while self.is_in_range(next_no) and int(next_no) in occupied:
					next_no = self.next_no_after(next_no)

		values = {}
		if next_no != self.next_cheque_no:
			values["next_cheque_no"] = next_no
		if not self.is_in_range(next_no) and self.status == "Submitted":
			if count_free_cheques(self, for_update=True) == 0:
				values["status"] = "Finished"

		if values:
			self.db_set(values)


def get_occupied_cheque_nos(book, from_no=None, for_update=False):
	issued_filters = {"cheque_book": book.name, "docstatus": 1}
	cancelled_filters = {"cheque_book": book.name}
	if from_no:
		issued_filters["reference_no"] = (">=", from_no)
		cancelled_filters["cheque_no"] = (">=", from_no)

	issued = frappe.db.get_values(
		"Payment Entry",
		issued_filters,
		"reference_no",
		pluck=True,
		for_update=for_update,
	)
	cancelled = frappe.db.get_values(
		"Cancelled Cheque",
		cancelled_filters,
		"cheque_no",
		pluck=True,
		for_update=for_update,
	)
	start, end = int(book.cheque_start_no), int(book.cheque_end_no)
	return {int(no) for no in issued + cancelled if no and no.isdigit() and start <= int(no) <= end}


def count_free_cheques(book, for_update=False):
	return book.no_of_cheques - len(get_occupied_cheque_nos(book, for_update=for_update))


@frappe.whitelist()
def get_next_cheque_book_no(bank_account: str) -> str:
	"""Suggest the number after the highest numbered cheque book of the bank account, else 01.

	Cancelled books count too, because the cheque book no is part of the name.
	"""
	frappe.has_permission("Cheque Book", throw=True)
	frappe.has_permission("Bank Account", doc=bank_account, ptype="read", throw=True)
	numbers = [
		no
		for no in frappe.get_list(
			"Cheque Book", filters={"bank_account": bank_account}, pluck="cheque_book_no"
		)
		if no.isdigit()
	]
	if not numbers:
		return "01"

	last_no = max(numbers, key=int)
	return str(int(last_no) + 1).zfill(len(last_no))


@frappe.whitelist()
def get_next_cheque(account: str, cheque_book: str | None = None, include_free: bool = False) -> dict:
	"""Return the cheque book (the given one, else the oldest active one) and its next cheque no."""
	enabled_bank_accounts = frappe.get_all(
		"Bank Account",
		filters={"account": account, "is_company_account": 1, "disabled": 0},
		pluck="name",
	)
	if not enabled_bank_accounts:
		return {}

	filters = {"name": cheque_book} if cheque_book else {"account": account}
	books = frappe.get_list(
		"Cheque Book",
		filters={
			**filters,
			"bank_account": ("in", enabled_bank_accounts),
			"docstatus": 1,
			"status": "Submitted",
		},
		fields=["name", "next_cheque_no", "cheque_start_no", "cheque_end_no", "no_of_cheques"],
		order_by="creation",
	)

	if not books:
		return {}
	book = next((book for book in books if int(book.next_cheque_no) <= int(book.cheque_end_no)), books[0])
	result = {"cheque_book": book.name}
	if int(book.next_cheque_no) <= int(book.cheque_end_no):
		result["cheque_no"] = book.next_cheque_no
	if include_free:
		result["free"] = count_free_cheques(book)
	return result


def is_cheque_payment(payment_entry) -> bool:
	return payment_entry.payment_type in ("Pay", "Internal Transfer") and payment_entry.mode_of_payment in (
		"Cheque",
		"Check",
	)


def validate_cheque(payment_entry):
	doc = payment_entry
	if not is_cheque_payment(doc):
		doc.cheque_book = None
		return

	if doc.docstatus == 0 and not doc.reference_no:
		cheque = get_next_cheque(doc.paid_from, doc.cheque_book)
		doc.cheque_book = cheque.get("cheque_book", doc.cheque_book)
		doc.reference_no = cheque.get("cheque_no")
		doc.reference_date = doc.reference_date or doc.posting_date

	if not doc.cheque_book:
		if frappe.db.exists("Cheque Book", {"account": doc.paid_from, "docstatus": 1}):
			frappe.throw(_("Please select a Cheque Book"))
		return

	if doc.docstatus == 1:
		# Match Cheque Book validation's account-then-book lock order.
		bank_account = frappe.db.get_value("Cheque Book", doc.cheque_book, "bank_account")
		is_company_account, disabled = frappe.db.get_value(
			"Bank Account", bank_account, ["is_company_account", "disabled"], for_update=True
		)
		book = frappe.get_doc("Cheque Book", doc.cheque_book, for_update=True)
	else:
		book = frappe.get_doc("Cheque Book", doc.cheque_book)
		is_company_account, disabled = frappe.db.get_value(
			"Bank Account", book.bank_account, ["is_company_account", "disabled"]
		)

	if not is_company_account:
		frappe.throw(_("Bank Account {0} is not a Company Account").format(frappe.bold(book.bank_account)))
	if disabled:
		frappe.throw(_("Bank Account {0} is disabled").format(frappe.bold(book.bank_account)))

	# A finished book still accepts a number, so a payment on its last cheque can be amended
	if book.docstatus != 1 or book.status == "Disabled":
		frappe.throw(_("Cheque Book {0} must be submitted and enabled").format(frappe.bold(book.name)))

	if book.account != doc.paid_from:
		frappe.throw(
			_("Cheque Book {0} belongs to account {1}, but Account Paid From is {2}").format(
				frappe.bold(book.name), frappe.bold(book.account), frappe.bold(doc.paid_from)
			)
		)

	if not doc.reference_no:
		frappe.throw(_("Please enter a Cheque No for Cheque Book {0}").format(frappe.bold(book.name)))

	doc.reference_no = book.format_cheque_no(doc.reference_no)
	if not book.is_in_range(doc.reference_no):
		frappe.throw(
			_("Cheque No {0} is not in the range {1} - {2} of Cheque Book {3}").format(
				frappe.bold(doc.reference_no),
				book.cheque_start_no,
				book.cheque_end_no,
				frappe.bold(book.name),
			)
		)

	if reason := frappe.db.get_value(
		"Cancelled Cheque",
		f"{book.name}-{doc.reference_no}",
		"reason",
		for_update=doc.docstatus == 1,
	):
		frappe.throw(_("Cheque No {0} is cancelled ({1})").format(frappe.bold(doc.reference_no), reason))

	filters = {"cheque_book": book.name, "reference_no": doc.reference_no, "name": ("!=", doc.name)}
	if used_in := frappe.db.get_value(
		"Payment Entry", {**filters, "docstatus": 1}, for_update=doc.docstatus == 1
	):
		frappe.throw(
			_("Cheque No {0} is already used in {1}").format(
				frappe.bold(doc.reference_no), get_link_to_form("Payment Entry", used_in)
			)
		)

	if doc.docstatus == 0 and (draft := frappe.db.get_value("Payment Entry", {**filters, "docstatus": 0})):
		frappe.msgprint(
			_("Cheque No {0} is also used in draft {1}").format(
				frappe.bold(doc.reference_no), get_link_to_form("Payment Entry", draft)
			),
			alert=True,
			indicator="orange",
		)


def update_cheque_book(payment_entry):
	if is_cheque_payment(payment_entry) and payment_entry.cheque_book:
		book = frappe.get_doc("Cheque Book", payment_entry.cheque_book, for_update=True)
		book.advance_next_cheque_no(payment_entry.reference_no)


@frappe.whitelist(methods=["POST"])
def cancel_cheque_payment(
	name: str,
	reason: str,
	remarks: str | None = None,
	ignore_doctypes_on_cancel_all: str | list[str] | None = None,
):
	"""Cancel the payment and record its voided cheque in the same transaction."""
	from frappe.desk.form.linked_with import (
		MAX_SYNCHRONOUS_LINKED_DOCS,
		cancel_all_linked_docs,
		collect_cancellation_blockers,
	)

	payment = frappe.get_doc("Payment Entry", name)
	payment.check_permission("cancel")
	if payment.docstatus != 1 or not payment.cheque_book or not is_cheque_payment(payment) or not reason:
		frappe.throw(_("Select a cancellation reason for a submitted cheque Payment Entry"))

	ignored = frappe.parse_json(ignore_doctypes_on_cancel_all) or []
	linked, truncated = collect_cancellation_blockers(
		"Payment Entry", name, ignored, limit=MAX_SYNCHRONOUS_LINKED_DOCS
	)
	if truncated:
		frappe.throw(_("Cancel linked documents separately before cancelling this cheque Payment Entry"))
	if linked:
		cancel_all_linked_docs(linked, ignored, "Payment Entry", name)
	else:
		payment.cancel()

	if frappe.db.get_value("Payment Entry", name, "docstatus") != 2:
		frappe.throw(_("Payment Entry cancellation must finish before marking its cheque cancelled"))
	frappe.get_doc(
		{
			"doctype": "Cancelled Cheque",
			"cheque_book": payment.cheque_book,
			"cheque_no": payment.reference_no,
			"payment_entry": name,
			"reason": reason,
			"remarks": remarks,
		}
	).insert()
