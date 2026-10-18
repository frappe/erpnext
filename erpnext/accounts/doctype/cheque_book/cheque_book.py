# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, get_link_to_form, now

CHEQUE_NO_WIDTH = 6
MAX_CHEQUES_PER_BOOK = 1000
# (from, to) status changes a user can make on a submitted book
USER_STATUS_CHANGES = {("Submitted", "Disabled"), ("Finished", "Disabled"), ("Disabled", "Submitted")}


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

	def check_if_latest(self):
		# Every cheque writer locks the bank account, then the book, then the cheque.
		# Frappe locks this book in the parent method, so lock the bank account first.
		if self.bank_account:
			frappe.db.get_value("Bank Account", self.bank_account, "name", for_update=True)
		super().check_if_latest()

	def before_insert(self):
		# Runs before naming, so the name gets the padded numbers
		self.cheque_start_no = format_cheque_no(self.cheque_start_no)
		self.cheque_end_no = format_cheque_no(self.cheque_end_no)

	def validate(self):
		if not (self.bank_account and self.cheque_start_no and self.cheque_end_no):
			return  # the mandatory check names the missing field

		self.validate_bank_account()
		self.validate_cheque_range()
		self.validate_name_length()
		self.validate_amendment()
		self.validate_overlapping_range()
		self.validate_name_is_free()

	def before_submit(self):
		self.status = "Submitted"

	def on_submit(self):
		self.make_cheques()

	def before_update_after_submit(self):
		previous = self.get_doc_before_save().status
		if self.status != previous and (previous, self.status) not in USER_STATUS_CHANGES:
			frappe.throw(_("A submitted Cheque Book can only be disabled or enabled"))

	def on_update_after_submit(self):
		self.update_status()

	def on_cancel(self):
		cheques = self.get_cheques_for_update()
		if issued := next((cheque for cheque in cheques if cheque.status == "Issued"), None):
			frappe.throw(
				_("Cannot cancel {0} because cheque {1} is used in {2}").format(
					frappe.bold(self.name),
					frappe.bold(issued.cheque_no),
					get_link_to_form("Payment Entry", issued.payment_entry),
				)
			)

		# Set first, so the status update of each cheque cancel below skips this book
		self.db_set("status", "Cancelled")
		for cheque in cheques:
			doc = frappe.get_doc("Cheque", cheque.name, for_update=True)
			doc.flags.ignore_permissions = True
			doc.void(remarks=_("Cheque Book {0} cancelled").format(self.name))

	def update_status(self):
		"""Set Finished when no cheque is free. The caller must hold the book lock."""
		if self.status not in ("Submitted", "Finished"):
			return

		free = frappe.db.get_value(
			"Cheque", {"cheque_book": self.name, "status": "Available"}, "name", for_update=True
		)
		status = "Submitted" if free else "Finished"
		if status != self.status:
			self.db_set("status", status)

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
		if bank_account.disabled and self.is_new():
			frappe.throw(_("Bank Account {0} is disabled").format(frappe.bold(self.bank_account)))

	def validate_cheque_range(self):
		for fieldname in ("cheque_start_no", "cheque_end_no"):
			value = self.get(fieldname)
			if not (value.isascii() and value.isdigit()):
				frappe.throw(_("{0} must contain digits only").format(_(self.meta.get_label(fieldname))))

		self.no_of_cheques = int(self.cheque_end_no) - int(self.cheque_start_no) + 1
		if self.no_of_cheques < 1:
			frappe.throw(_("Cheque End No cannot be less than Cheque Start No"))
		if self.no_of_cheques > MAX_CHEQUES_PER_BOOK:
			frappe.throw(_("A Cheque Book can have at most {0} cheques").format(MAX_CHEQUES_PER_BOOK))

	def validate_name_length(self):
		# Each cheque is named "<book>-<cheque no>", and the end number is the longest one
		excess = len(f"{self.name}-{self.cheque_end_no}") - frappe.db.VARCHAR_LEN
		if excess > 0:
			frappe.throw(
				_(
					"Cheque names of this book would be longer than {0} characters. Shorten the name of Company Bank Account {1} by {2} characters."
				).format(frappe.db.VARCHAR_LEN, frappe.bold(self.bank_account), excess)
			)

	def validate_amendment(self):
		"""An amendment takes the name of the cancelled book, so it keeps its bank account and range."""
		if not (self.amended_from and self.is_new()):
			return

		original = frappe.db.get_value(
			"Cheque Book",
			self.amended_from,
			["bank_account", "cheque_start_no", "cheque_end_no"],
			as_dict=True,
		)
		if original and (original.bank_account, original.cheque_start_no, original.cheque_end_no) != (
			self.bank_account,
			self.cheque_start_no,
			self.cheque_end_no,
		):
			frappe.throw(
				_(
					"An amendment of {0} must keep its bank account and cheque range. Create a new Cheque Book for another range."
				).format(frappe.bold(self.amended_from))
			)

	def validate_overlapping_range(self):
		# The bank account lock serializes book saves, and this locking read sees committed ranges
		other_books = frappe.db.get_values(
			"Cheque Book",
			filters={"bank_account": self.bank_account, "docstatus": ("<", 2), "name": ("!=", self.name)},
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

	def validate_name_is_free(self):
		# A live book with this range fails the overlap check, so only a cancelled one gets here
		if self.is_new() and frappe.db.exists("Cheque Book", self.name):
			frappe.throw(
				_("Cancelled Cheque Book {0} has this range. Amend it to use the range again.").format(
					get_link_to_form("Cheque Book", self.name)
				)
			)

	def make_cheques(self):
		# One query for up to 1,000 rows. A new cheque runs no hooks, so nothing is skipped.
		fields = ["name", "cheque_no", "cheque_book", "bank_account", "company", "status", "docstatus"]
		fields += ["owner", "modified_by", "creation", "modified"]
		timestamp, user = now(), frappe.session.user
		shared = (
			self.name,
			self.bank_account,
			self.company,
			"Available",
			1,
			user,
			user,
			timestamp,
			timestamp,
		)
		values = []
		for number in range(int(self.cheque_start_no), int(self.cheque_end_no) + 1):
			cheque_no = format_cheque_no(str(number))
			values.append((f"{self.name}-{cheque_no}", cheque_no, *shared))
		frappe.db.bulk_insert("Cheque", fields, values)

	def get_cheques_for_update(self):
		# Every cheque writer holds this book's lock, so the locked rows stay current
		return frappe.db.get_values(
			"Cheque",
			{"cheque_book": self.name, "docstatus": 1},
			["name", "cheque_no", "status", "payment_entry"],
			as_dict=True,
			order_by="name",
			for_update=True,
		)


def format_cheque_no(cheque_no: str | int | None) -> str:
	"""Strip and zero-pad a typed number. Other text stays as typed, for validation to reject."""
	cheque_no = cstr(cheque_no).strip()  # the API and Data Import can send a number
	if cheque_no.isascii() and cheque_no.isdigit():
		return str(int(cheque_no)).zfill(CHEQUE_NO_WIDTH)
	return cheque_no
