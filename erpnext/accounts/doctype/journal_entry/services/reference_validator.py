# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _, scrub
from frappe.utils import cstr, flt, fmt_money

from erpnext.accounts.deferred_revenue import get_deferred_booking_accounts
from erpnext.accounts.doctype.invoice_discounting.invoice_discounting import (
	get_party_account_based_on_invoice_discounting,
)
from erpnext.accounts.utils import get_account_currency

REFERENCE_PARTY_ACCOUNT_FIELDS = {
	"Sales Invoice": ["Customer", "Debit To"],
	"Purchase Invoice": ["Supplier", "Credit To"],
	"Sales Order": ["Customer"],
	"Purchase Order": ["Supplier"],
}


class JournalEntryReferenceValidator:
	"""Validates Journal Entry account rows against their referenced documents.

	For each row that links a Sales/Purchase Invoice or Order, this checks the
	debit/credit direction, party and account match, and aggregates per-reference
	totals (held on the document as ``reference_totals``/``reference_types``/
	``reference_accounts``) which are then validated against the referenced
	orders and invoices.
	"""

	def __init__(self, doc) -> None:
		self.doc = doc

	def validate(self) -> None:
		"""Validate every reference-bearing row, then the referenced orders and invoices."""
		self.doc.reference_totals = {}
		self.doc.reference_types = {}
		self.doc.reference_accounts = {}
		for row in self.doc.get("accounts"):
			self._normalize_reference_fields(row)
			if not self._has_party_reference(row):
				continue
			self._validate_order_direction(row)
			self._register_reference(row)
			self._validate_reference_party_and_account(row)

		self._validate_orders()
		self._validate_invoices()

	def _normalize_reference_fields(self, row) -> None:
		if not row.reference_type:
			row.reference_name = None
		if not row.reference_name:
			row.reference_type = None

	def _has_party_reference(self, row) -> bool:
		return bool(
			row.reference_type and row.reference_name and row.reference_type in REFERENCE_PARTY_ACCOUNT_FIELDS
		)

	def _reference_amount_field(self, row) -> str:
		if row.reference_type in ("Sales Order", "Sales Invoice"):
			return "credit_in_account_currency"
		return "debit_in_account_currency"

	def _validate_order_direction(self, row) -> None:
		"""An order can only be linked on the side that records an advance."""
		if row.reference_type == "Sales Order" and flt(row.debit) > 0:
			frappe.throw(
				_("Row {0}: Debit entry can not be linked with a {1}").format(row.idx, row.reference_type)
			)
		if row.reference_type == "Purchase Order" and flt(row.credit) > 0:
			frappe.throw(
				_("Row {0}: Credit entry can not be linked with a {1}").format(row.idx, row.reference_type)
			)

	def _register_reference(self, row) -> None:
		"""Aggregate the row's amount, type and account onto the per-reference lookups."""
		if row.reference_name not in self.doc.reference_totals:
			self.doc.reference_totals[row.reference_name] = 0.0
		if self.doc.voucher_type not in ("Deferred Revenue", "Deferred Expense"):
			self.doc.reference_totals[row.reference_name] += flt(row.get(self._reference_amount_field(row)))
		self.doc.reference_types[row.reference_name] = row.reference_type
		self.doc.reference_accounts[row.reference_name] = row.account

	def _validate_reference_party_and_account(self, row) -> None:
		"""Reject a missing reference, then check party/account against the linked document."""
		party_fields = REFERENCE_PARTY_ACCOUNT_FIELDS[row.reference_type]
		against_voucher = frappe.db.get_value(
			row.reference_type, row.reference_name, [scrub(f) for f in party_fields]
		)
		if not against_voucher:
			frappe.throw(_("Row {0}: Invalid reference {1}").format(row.idx, row.reference_name))

		if row.reference_type in ("Sales Invoice", "Purchase Invoice"):
			self._validate_invoice_party_and_account(row, against_voucher, party_fields)
		elif row.reference_type in ("Sales Order", "Purchase Order"):
			self._validate_order_party(row, against_voucher)

	def _validate_invoice_party_and_account(self, row, against_voucher, party_fields) -> None:
		party_account, against_party = self._resolve_invoice_party_account(row, against_voucher)
		if self.doc.voucher_type == "Exchange Gain Or Loss":
			return
		if against_party != cstr(row.party) or party_account != row.account:
			frappe.throw(
				_("Row {0}: Party / Account does not match with {1} / {2} in {3} {4}").format(
					row.idx, party_fields[0], party_fields[1], row.reference_type, row.reference_name
				)
			)

	def _resolve_invoice_party_account(self, row, against_voucher) -> tuple:
		"""Expected (party_account, party) for an invoice row, honouring deferred booking
		and invoice-discounting accounts."""
		if self.doc.voucher_type in ("Deferred Revenue", "Deferred Expense") and row.reference_detail_no:
			debit_or_credit = "Debit" if row.debit else "Credit"
			party_account = get_deferred_booking_accounts(
				row.reference_type, row.reference_detail_no, debit_or_credit
			)
			return party_account, ""
		if row.reference_type == "Sales Invoice":
			party_account = (
				get_party_account_based_on_invoice_discounting(row.reference_name) or against_voucher[1]
			)
		else:
			party_account = against_voucher[1]
		return party_account, against_voucher[0]

	def _validate_order_party(self, row, against_voucher) -> None:
		if against_voucher != row.party:
			frappe.throw(
				_("Row {0}: {1} {2} does not match with {3}").format(
					row.idx, row.party_type, row.party, row.reference_type
				)
			)

	def _validate_orders(self) -> None:
		"""Validate totals, closed and docstatus for referenced orders."""
		for reference_name, total in self.doc.reference_totals.items():
			reference_type = self.doc.reference_types[reference_name]
			account = self.doc.reference_accounts[reference_name]
			if reference_type not in ("Sales Order", "Purchase Order"):
				continue

			order = frappe.get_doc(reference_type, reference_name)
			self._validate_order_status(order, reference_type, reference_name)
			self._validate_order_advance_total(order, account, total, reference_type, reference_name)

	def _validate_order_status(self, order, reference_type, reference_name) -> None:
		if order.docstatus != 1:
			frappe.throw(_("{0} {1} is not submitted").format(reference_type, reference_name))
		if flt(order.per_billed) >= 100:
			frappe.throw(_("{0} {1} is fully billed").format(reference_type, reference_name))
		if cstr(order.status) == "Closed":
			frappe.throw(_("{0} {1} is closed").format(reference_type, reference_name))

	def _validate_order_advance_total(self, order, account, total, reference_type, reference_name) -> None:
		"""The advance paid against an order cannot exceed its grand total."""
		account_currency = get_account_currency(account)
		if account_currency == self.doc.company_currency:
			voucher_total = order.base_grand_total
			field = "base_grand_total"
		else:
			voucher_total = order.grand_total
			field = "grand_total"

		if flt(voucher_total) < (flt(order.advance_paid) + total):
			formatted_voucher_total = fmt_money(
				voucher_total, order.precision(field), currency=account_currency
			)
			frappe.throw(
				_("Advance paid against {0} {1} cannot be greater than Grand Total {2}").format(
					reference_type, reference_name, formatted_voucher_total
				)
			)

	def _validate_invoices(self) -> None:
		"""Validate totals and docstatus for referenced invoices."""
		if self.doc.voucher_type in ("Debit Note", "Credit Note"):
			return
		for reference_name, total in self.doc.reference_totals.items():
			reference_type = self.doc.reference_types[reference_name]
			if reference_type not in ("Sales Invoice", "Purchase Invoice"):
				continue
			invoice = frappe.get_doc(reference_type, reference_name)
			self._validate_invoice_outstanding(invoice, total, reference_type, reference_name)

	def _validate_invoice_outstanding(self, invoice, total, reference_type, reference_name) -> None:
		"""Payment booked against an invoice cannot exceed its outstanding amount."""
		if invoice.docstatus != 1:
			frappe.throw(_("{0} {1} is not submitted").format(reference_type, reference_name))

		precision = invoice.precision("outstanding_amount")
		if total and flt(invoice.outstanding_amount, precision) < flt(total, precision):
			frappe.throw(
				_("Payment against {0} {1} cannot be greater than Outstanding Amount {2}").format(
					reference_type, reference_name, invoice.outstanding_amount
				)
			)
