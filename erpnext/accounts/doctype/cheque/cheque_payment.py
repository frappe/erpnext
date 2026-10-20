# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Cheques in Payment Entry: suggest, validate, issue and cancel."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import get_link_to_form

from erpnext.accounts.doctype.cheque.cheque import Cheque, require_reason
from erpnext.accounts.doctype.cheque_book.cheque_book import format_cheque_no


@frappe.whitelist()
def get_next_cheque(account: str, cheque_book: str | None = None) -> dict:
	"""Suggest a cheque book of the bank ledger and its next cheque number, with the free count.

	The next number is the one after the highest used cheque, so cheques that a user skipped stay
	free for a manual pick. Without a cheque book, take the oldest active book that has a next number.
	"""
	bank_accounts = frappe.get_all(
		"Bank Account", filters={"account": account, "is_company_account": 1, "disabled": 0}, pluck="name"
	)
	if not bank_accounts:
		return {}

	filters = {"bank_account": ("in", bank_accounts), "docstatus": 1, "status": "Submitted"}
	if cheque_book:
		filters["name"] = cheque_book
	books = frappe.get_list(
		"Cheque Book",
		filters=filters,
		fields=["name", "cheque_start_no", "cheque_end_no", "no_of_cheques"],
		order_by="creation asc, name asc",
	)
	if not books:
		return {}

	used = defaultdict(list)
	for book_name, cheque_no in frappe.get_all(
		"Cheque",
		filters={"cheque_book": ("in", [book.name for book in books]), "status": ("!=", "Available")},
		fields=["cheque_book", "cheque_no"],
		as_list=True,
	):
		used[book_name].append(int(cheque_no))

	for book in books:
		next_no = max(used[book.name], default=int(book.cheque_start_no) - 1) + 1
		has_next = next_no <= int(book.cheque_end_no)
		if has_next or cheque_book:
			suggestion = {
				"cheque_book": book.name,
				"free": book.no_of_cheques - len(used[book.name]),
				"cheque_start_no": book.cheque_start_no,
				"cheque_end_no": book.cheque_end_no,
			}
			if has_next:
				suggestion["cheque_no"] = format_cheque_no(str(next_no))
			return suggestion
	return {}


def validate_cheque(payment_entry):
	"""Find the cheque from the cheque book and the cheque number, and check it.

	Payment Entry validate calls this. The cheque link is set here, so an empty number gets the
	suggestion and a typed number gets padded first.
	"""
	doc = payment_entry
	doc.cheque = None
	if not is_cheque_payment(doc):
		doc.cheque_book = None
		return
	if not doc.cheque_book:
		return

	if doc.docstatus == 0 and not doc.reference_no:
		doc.reference_no = get_next_cheque(doc.paid_from, doc.cheque_book).get("cheque_no")
	doc.reference_no = format_cheque_no(doc.reference_no)
	if not doc.reference_no:
		frappe.throw(_("Enter a cheque number of Cheque Book {0}").format(frappe.bold(doc.cheque_book)))

	cheque = get_cheque_for_payment(f"{doc.cheque_book}-{doc.reference_no}")
	if not cheque:
		frappe.throw(
			_("Cheque No {0} is not in Cheque Book {1}").format(
				frappe.bold(doc.reference_no), frappe.bold(doc.cheque_book)
			)
		)
	if cheque.status == "Cancelled":
		frappe.throw(
			_("Cheque No {0} is cancelled. Enter another cheque number.").format(
				frappe.bold(cheque.cheque_no)
			)
		)
	if cheque.status == "Issued" and cheque.payment_entry != doc.name:
		frappe.throw(
			_("Cheque No {0} is already used in {1}").format(
				frappe.bold(cheque.cheque_no), get_link_to_form("Payment Entry", cheque.payment_entry)
			)
		)
	if cheque.book_status == "Disabled":
		frappe.throw(_("Cheque Book {0} is disabled").format(frappe.bold(cheque.cheque_book)))
	if not cheque.is_company_account or cheque.bank_account_disabled:
		frappe.throw(
			_("Bank Account {0} must be an enabled Company Account").format(frappe.bold(cheque.bank_account))
		)
	if cheque.account != doc.paid_from:
		frappe.throw(
			_("Cheque No {0} is for account {1}, but Account Paid From is {2}").format(
				frappe.bold(cheque.cheque_no), frappe.bold(cheque.account), frappe.bold(doc.paid_from)
			)
		)

	doc.cheque = cheque.name
	doc.reference_date = doc.reference_date or doc.posting_date
	if doc.docstatus == 0 and (
		draft := frappe.db.get_value(
			"Payment Entry", {"cheque": doc.cheque, "docstatus": 0, "name": ("!=", doc.name)}
		)
	):
		frappe.msgprint(
			_("Cheque {0} is also selected in draft {1}").format(
				frappe.bold(cheque.cheque_no), get_link_to_form("Payment Entry", draft)
			),
			alert=True,
			indicator="orange",
		)


def issue_cheque(payment_entry):
	"""Record a submitted payment on its cheque. Payment Entry on_submit calls this."""
	if not payment_entry.cheque:
		return

	cheque = lock_cheque(payment_entry.cheque)
	# Validate ran before the locks, so read them again: another user may have changed them since
	if cheque.status != "Available":
		frappe.throw(_("Cheque {0} is no longer available").format(frappe.bold(cheque.cheque_no)))
	if frappe.db.get_value("Cheque Book", cheque.cheque_book, "status", for_update=True) == "Disabled":
		frappe.throw(_("Cheque Book {0} is disabled").format(frappe.bold(cheque.cheque_book)))
	bank_account = frappe.db.get_value(
		"Bank Account", cheque.bank_account, ["is_company_account", "disabled"], as_dict=True, for_update=True
	)
	if not bank_account.is_company_account or bank_account.disabled:
		frappe.throw(
			_("Bank Account {0} must be an enabled Company Account").format(frappe.bold(cheque.bank_account))
		)
	cheque.issue(payment_entry.name)


def void_cheque(payment_entry):
	"""Cancel the cheque of a cancelled payment. Payment Entry on_cancel calls this."""
	if not payment_entry.cheque:
		return

	cheque = lock_cheque(payment_entry.cheque)
	if cheque.docstatus != 1 or cheque.payment_entry != payment_entry.name:
		return  # never change a cheque that another payment holds

	cheque.flags.ignore_permissions = True
	cheque.void(
		cheque.cancellation_reason,
		cheque.remarks or _("Cancelled with Payment Entry {0}").format(payment_entry.name),
	)


@frappe.whitelist(methods=["POST"])
def cancel_cheque_payment(
	name: str,
	reason: str,
	remarks: str | None = None,
	ignore_doctypes_on_cancel_all: str | list[str] | None = None,
):
	"""Cancel a cheque payment, its linked documents and its cheque with the reason, in one transaction."""
	from frappe.desk.form.linked_with import (
		MAX_SYNCHRONOUS_LINKED_DOCS,
		cancel_all_linked_docs,
		collect_cancellation_blockers,
	)

	reason = require_reason(reason)
	# Lock order: the payment, then the bank account, the book and the cheque, as on submit
	payment = frappe.get_doc("Payment Entry", name, for_update=True)
	payment.check_permission("cancel")
	if payment.docstatus != 1 or not payment.cheque:
		frappe.throw(_("Payment Entry {0} is not a submitted cheque payment").format(frappe.bold(name)))

	cheque = lock_cheque(payment.cheque)
	if cheque.docstatus != 1 or cheque.payment_entry != name:
		frappe.throw(_("Cheque {0} is not issued for {1}").format(frappe.bold(cheque.cheque_no), name))
	cheque.keep_cancellation_reason(reason, remarks)

	ignored = frappe.parse_json(ignore_doctypes_on_cancel_all) or []
	linked, truncated = collect_cancellation_blockers(
		"Payment Entry", name, ignored, limit=MAX_SYNCHRONOUS_LINKED_DOCS
	)
	if truncated:
		frappe.throw(_("Cancel the linked documents separately before you cancel this Payment Entry"))
	if linked:
		cancel_all_linked_docs(linked, ignored, "Payment Entry", name)
	else:
		payment.cancel()

	# A cancel that moved to a background job would cancel the cheque without this request
	if frappe.db.get_value("Payment Entry", name, "docstatus") != 2:
		frappe.throw(_("Payment Entry {0} was not cancelled").format(frappe.bold(name)))


def is_cheque_payment(payment_entry) -> bool:
	return payment_entry.payment_type in ("Pay", "Internal Transfer") and payment_entry.mode_of_payment in (
		"Cheque",
		"Check",
	)


def lock_cheque(name: str) -> Cheque:
	"""Lock the bank account, the book, then the cheque: the order that every cheque writer uses."""
	# Neither field ever changes, so they need no lock
	cheque = frappe.db.get_value("Cheque", name, ["cheque_book", "bank_account"], as_dict=True)
	if not cheque:  # a lock query with no name would lock some other row
		frappe.throw(_("Cheque {0} does not exist").format(frappe.bold(name)), frappe.DoesNotExistError)
	frappe.db.get_value("Bank Account", cheque.bank_account, "name", for_update=True)
	frappe.db.get_value("Cheque Book", cheque.cheque_book, "name", for_update=True)
	return frappe.get_doc("Cheque", name, for_update=True)


def get_cheque_for_payment(name: str):
	"""The cheque with the status of its book and the details of its bank account, in one query."""
	rows = frappe.qb.get_query(
		"Cheque",
		fields=[
			"name",
			"cheque_no",
			"status",
			"payment_entry",
			"cheque_book",
			"bank_account",
			"cheque_book.status as book_status",
			"bank_account.account as account",
			"bank_account.is_company_account as is_company_account",
			"bank_account.disabled as bank_account_disabled",
		],
		filters={"name": name},
	).run(as_dict=True)
	return rows[0] if rows else None
