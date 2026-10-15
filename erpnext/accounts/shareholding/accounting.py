# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.accounts.shareholding.posting import money


def validate_equity_journal_entry(doc, method=None):
	previous = doc.get_doc_before_save()
	if (
		previous
		and previous.get("share_transaction")
		and previous.share_transaction != doc.get("share_transaction")
	):
		frappe.throw(_("The source Share Transaction cannot be changed."))
	if not doc.get("share_transaction"):
		return
	transaction = frappe.get_doc("Share Transaction", doc.share_transaction)
	transaction.check_permission("read")
	if transaction.docstatus != 1:
		frappe.throw(_("The source Share Transaction must be submitted."))
	if transaction.journal_entry != doc.name:
		frappe.throw(_("An active Journal Entry already exists for this Share Transaction."))
	if transaction.company != doc.company:
		frappe.throw(_("Journal Entry and Share Transaction must belong to the same company."))
	if transaction.transaction_type == "Transfer":
		frappe.throw(_("A shareholder Transfer does not create company accounting."))
	currency = frappe.db.get_value("Company", doc.company, "default_currency")
	if doc.multi_currency or any(
		row.account_currency != currency or row.exchange_rate != 1 for row in doc.accounts
	):
		frappe.throw(_("Generated equity accounting uses company currency only."))
	validate_snapshot(doc, transaction, currency)
	if frappe.db.exists(
		"Journal Entry",
		{"share_transaction": transaction.name, "docstatus": ["!=", 2], "name": ["!=", doc.name]},
	):
		frappe.throw(_("An active Journal Entry already exists for this Share Transaction."))


def validate_snapshot(doc, transaction, currency):
	from erpnext.accounts.doctype.equity_accounting_settings.equity_accounting_settings import (
		validate_account,
	)

	if str(doc.posting_date) != str(transaction.posting_date):
		frappe.throw(_("The journal posting date must match the Share Transaction."))
	snapshot = frappe.parse_json(transaction.accounting_snapshot or "[]")
	if not snapshot:
		frappe.throw(_("The source Share Transaction has no accounting snapshot."))
	expected = []
	expected_settlement = []
	for row in snapshot:
		amounts = (
			money(row.get("debit_in_account_currency"), currency),
			money(row.get("credit_in_account_currency"), currency),
		)
		if row["account"] == transaction.settlement_account:
			expected_settlement.append(amounts)
		else:
			expected.append((row["account"], *amounts))
	actual = []
	actual_settlement = []
	protected_accounts = {row[0] for row in expected}
	for row in doc.accounts:
		amounts = (
			money(row.debit_in_account_currency, currency),
			money(row.credit_in_account_currency, currency),
		)
		if row.account in protected_accounts:
			actual.append((row.account, *amounts))
		else:
			validate_account(row.account, doc.company, currency, {"Asset", "Liability"})
			actual_settlement.append(amounts)
	if sorted(expected) != sorted(actual) or sorted(expected_settlement) != sorted(actual_settlement):
		frappe.throw(_("The journal amounts and equity accounts must match the Share Transaction."))


def prevent_independent_cancellation(doc, method=None):
	if doc.get("share_transaction") and frappe.flags.share_transaction_cancelling != doc.share_transaction:
		frappe.throw(_("Cancel the Share Transaction to reverse this journal consistently."))
