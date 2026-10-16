# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Cheques in Payment Entry: suggest, validate, issue and cancel."""

import frappe
from frappe import _
from frappe.utils import get_link_to_form

from erpnext.accounts.doctype.cheque.cheque import Cheque, require_reason
from erpnext.accounts.doctype.cheque_book.cheque_book import format_cheque_no


@frappe.whitelist()
def get_next_cheque(account: str) -> str | None:
	"""Suggest a cheque for a payment from the bank ledger.

	It is the cheque after the highest used one, in the oldest active book that has such a cheque.
	Cheques that a user skipped stay free for a manual pick.
	"""
	bank_accounts = frappe.get_all(
		"Bank Account", filters={"account": account, "is_company_account": 1, "disabled": 0}, pluck="name"
	)
	if not bank_accounts:
		return None

	books = frappe.get_list(
		"Cheque Book",
		filters={"bank_account": ("in", bank_accounts), "docstatus": 1, "status": "Submitted"},
		fields=["name", "cheque_start_no", "cheque_end_no"],
		order_by="creation asc, name asc",
	)
	if not books:
		return None

	highest_used = {}
	for cheque_book, cheque_no in frappe.get_all(
		"Cheque",
		filters={"cheque_book": ("in", [book.name for book in books]), "status": ("!=", "Available")},
		fields=["cheque_book", "cheque_no"],
		as_list=True,
	):
		highest_used[cheque_book] = max(highest_used.get(cheque_book, 0), int(cheque_no))

	for book in books:
		next_no = highest_used.get(book.name, int(book.cheque_start_no) - 1) + 1
		if next_no <= int(book.cheque_end_no):
			return f"{book.name}-{format_cheque_no(str(next_no))}"
	return None


@frappe.whitelist()
def get_cheque_summary(cheque: str) -> dict:
	"""The cheque number, and the range and free count of its book, for the Payment Entry form."""
	frappe.has_permission("Cheque", "read", cheque, throw=True)
	cheque_no, cheque_book = frappe.db.get_value("Cheque", cheque, ["cheque_no", "cheque_book"])
	summary = frappe.db.get_value(
		"Cheque Book", cheque_book, ["cheque_start_no", "cheque_end_no"], as_dict=True
	)
	summary.cheque_no = cheque_no
	summary.free = frappe.db.count("Cheque", {"cheque_book": cheque_book, "status": "Available"})
	return summary


def validate_cheque(payment_entry):
	"""Check the cheque of a payment and copy its number. Payment Entry validate calls this."""
	doc = payment_entry
	if not is_cheque_payment(doc):
		doc.cheque = None
		return
	if not doc.cheque:
		return

	cheque = get_cheque_for_payment(doc.cheque)
	# Frappe's link check already refuses a cancelled cheque
	if not cheque:
		frappe.throw(_("Cheque {0} does not exist").format(frappe.bold(doc.cheque)))
	if cheque.status == "Issued" and cheque.payment_entry != doc.name:
		frappe.throw(
			_("Cheque {0} is already used in {1}").format(
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
			_("Cheque {0} is for account {1}, but Account Paid From is {2}").format(
				frappe.bold(cheque.cheque_no), frappe.bold(cheque.account), frappe.bold(doc.paid_from)
			)
		)

	doc.reference_no = cheque.cheque_no
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
	if cheque.status != "Available":  # another payment took it after this one was validated
		frappe.throw(_("Cheque {0} is no longer available").format(frappe.bold(cheque.cheque_no)))
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
	# Lock order: the payment, then the book, then the cheque, as on submit
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
	"""Lock the book, then the cheque: the order that every cheque writer uses."""
	cheque_book = frappe.db.get_value("Cheque", name, "cheque_book")  # never changes, so no lock
	frappe.db.get_value("Cheque Book", cheque_book, "name", for_update=True)
	return frappe.get_doc("Cheque", name, for_update=True)


def get_cheque_for_payment(name: str):
	"""The cheque with the status of its book and the details of its bank account, in one query."""
	rows = frappe.qb.get_query(
		"Cheque",
		fields=[
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
