# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_link_to_form

MAX_DIGITS = 9


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

	def validate_bank_account(self):
		if not frappe.db.get_value("Bank Account", self.bank_account, "is_company_account"):
			frappe.throw(
				_("Bank Account {0} is not a Company Account").format(frappe.bold(self.bank_account))
			)

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

		if len(self.cheque_start_no) != len(self.cheque_end_no):
			frappe.throw(
				_(
					"Cheque Start No and Cheque End No must have the same number of digits, including leading zeros"
				)
			)

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
			self.cheque_end_no = str(end_no).zfill(len(self.cheque_start_no))

		elif self.cheque_end_no and self.no_of_cheques:
			start_no = int(self.cheque_end_no) - self.no_of_cheques + 1
			if start_no < 0:
				frappe.throw(_("Number of Cheques cannot be more than Cheque End No"))
			self.cheque_start_no = str(start_no).zfill(len(self.cheque_end_no))

		else:
			frappe.throw(_("Enter any two of Cheque Start No, Cheque End No and Number of Cheques"))

	def validate_overlapping_range(self):
		other_books = frappe.get_all(
			"Cheque Book",
			filters={
				"bank_account": self.bank_account,
				"docstatus": ("<", 2),
				"name": ("!=", self.name or ""),
			},
			fields=["name", "cheque_start_no", "cheque_end_no"],
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

	def format_cheque_no(self, cheque_no):
		"""Pad a typed number to the printed width, e.g. 103 -> 000103"""
		cheque_no = (cheque_no or "").strip()
		return cheque_no.zfill(len(self.cheque_start_no)) if cheque_no.isdigit() else cheque_no

	def is_in_range(self, cheque_no):
		return (
			cheque_no.isdigit()
			and len(cheque_no) == len(self.cheque_start_no)
			and int(self.cheque_start_no) <= int(cheque_no) <= int(self.cheque_end_no)
		)

	def next_no_after(self, cheque_no):
		return str(int(cheque_no) + 1).zfill(len(self.cheque_start_no))

	def is_used(self, cheque_no):
		return bool(
			frappe.db.exists("Cancelled Cheque", {"cheque_book": self.name, "cheque_no": cheque_no})
			or frappe.db.exists(
				"Payment Entry",
				{"cheque_book": self.name, "reference_no": cheque_no, "docstatus": 1},
			)
		)

	def advance_next_cheque_no(self, used_cheque_no):
		"""Step the next cheque no past the cheque just used, and past any used ones after it"""
		if used_cheque_no != self.next_cheque_no:
			return

		cheque_no = self.next_no_after(used_cheque_no)
		while self.is_in_range(cheque_no) and self.is_used(cheque_no):
			cheque_no = self.next_no_after(cheque_no)

		values = {"next_cheque_no": cheque_no}
		if not self.is_in_range(cheque_no):
			values["status"] = "Finished"

		self.db_set(values)


@frappe.whitelist()
def get_next_cheque_book_no(bank_account: str) -> str:
	"""Suggest the number after the highest numbered cheque book of the bank account, else 01.

	Cancelled books count too, because the cheque book no is part of the name.
	"""
	frappe.has_permission("Cheque Book", throw=True)
	numbers = [
		no
		for no in frappe.get_all(
			"Cheque Book", filters={"bank_account": bank_account}, pluck="cheque_book_no"
		)
		if no.isdigit()
	]
	if not numbers:
		return "01"

	last_no = max(numbers, key=int)
	return str(int(last_no) + 1).zfill(len(last_no))


@frappe.whitelist()
def get_next_cheque(account: str, cheque_book: str | None = None) -> dict:
	"""Return the cheque book (the given one, else the oldest active one) and its next cheque no."""
	filters = {"name": cheque_book} if cheque_book else {"account": account}
	books = frappe.get_list(
		"Cheque Book",
		filters={**filters, "docstatus": 1, "status": "Submitted"},
		fields=["name", "next_cheque_no", "cheque_end_no"],
		order_by="creation",
	)

	for book in books:
		if cint(book.next_cheque_no) <= cint(book.cheque_end_no):
			return {
				"cheque_book": book.name,
				"cheque_no": book.next_cheque_no,
				# the numbers still ahead in the book, counting any cancelled ones among them
				"remaining": cint(book.cheque_end_no) - cint(book.next_cheque_no) + 1,
			}

	return {}


def is_cheque_payment(payment_entry) -> bool:
	# The setup wizard creates this Mode of Payment as _("Cheque"), "Check" in the US
	return payment_entry.payment_type in ("Pay", "Internal Transfer") and payment_entry.mode_of_payment in {
		"Cheque",
		"Check",
		_("Cheque"),
		_("Check"),
	}


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
		if frappe.db.exists("Cheque Book", {"account": doc.paid_from, "docstatus": 1, "status": "Submitted"}):
			frappe.throw(_("Please select a Cheque Book"))
		return

	if doc.docstatus == 1:
		# Lock the book so two Payment Entries can't submit the same cheque at once
		frappe.db.get_value("Cheque Book", doc.cheque_book, "name", for_update=True)

	book = frappe.get_doc("Cheque Book", doc.cheque_book)
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
		frappe.throw(_("No unused cheque left in Cheque Book {0}").format(frappe.bold(book.name)))

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
		"Cancelled Cheque", {"cheque_book": book.name, "cheque_no": doc.reference_no}, "reason"
	):
		frappe.throw(_("Cheque No {0} is cancelled ({1})").format(frappe.bold(doc.reference_no), reason))

	filters = {"cheque_book": book.name, "reference_no": doc.reference_no, "name": ("!=", doc.name)}
	if used_in := frappe.db.get_value("Payment Entry", {**filters, "docstatus": 1}):
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
		book = frappe.get_doc("Cheque Book", payment_entry.cheque_book)
		book.advance_next_cheque_no(payment_entry.reference_no)
