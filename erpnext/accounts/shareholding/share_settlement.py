# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Settle the clearing account of a share transaction with a Payment Entry."""

import frappe
from frappe import _
from frappe.utils import nowdate

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.share_accounting_settings.share_accounting_settings import validate_account
from erpnext.accounts.shareholding.company_lock import lock_company

PAYMENT_TRANSACTION_TYPES = {"Issue", "Buyback", "Reissue"}
SETTLEMENT_ROOT_TYPES = {
	"clearing_account": {"Asset", "Liability"},
	"bank_account": {"Asset", "Liability"},
}
PAYMENT_FIELDS = (
	"accounting_mode",
	"clearing_account",
	"mode_of_payment",
	"bank_account",
	"reference_no",
	"reference_date",
)


@frappe.whitelist()
def get_mode_of_payment_account(mode_of_payment: str | None, company: str):
	if not mode_of_payment:
		return None
	frappe.has_permission("Mode of Payment", "read", mode_of_payment, throw=True)
	frappe.has_permission("Company", "read", company, throw=True)
	return frappe.db.get_value(
		"Mode of Payment Account", {"parent": mode_of_payment, "company": company}, "default_account"
	)


class TransactionSettlement:
	@frappe.whitelist(methods=["POST"])
	def make_payment_entry(
		self,
		bank_account: str | None = None,
		mode_of_payment: str | None = None,
		reference_no: str | None = None,
		reference_date: str | None = None,
		posting_date: str | None = None,
	):
		frappe.db.get_value("Share Transaction", self.name, "name", for_update=True)
		self.reload()
		self.check_permission("read")
		frappe.has_permission("Payment Entry", "create", throw=True)
		lock_company(self.company)
		self.validate_can_create_payment_entry()
		self.set_payment_details(bank_account, mode_of_payment, reference_no, reference_date)
		self.validate_settlement_account("bank_account")
		return self.create_settlement_payment_entry(posting_date=posting_date or nowdate())

	def set_payment_defaults(self, settings):
		if self.transaction_type not in PAYMENT_TRANSACTION_TYPES:
			self.clear_payment_fields()
			return
		if not settings:
			return
		self.accounting_mode = self.accounting_mode or settings.accounting_mode
		self.clearing_account = self.clearing_account or settings.clearing_account
		self.bank_account = (
			self.bank_account or self.get_mode_of_payment_account() or settings.default_bank_account
		)

	def clear_payment_fields(self):
		for field in PAYMENT_FIELDS:
			self.set(field, None)

	def get_mode_of_payment_account(self):
		return get_mode_of_payment_account(self.mode_of_payment, self.company)

	def validate_payment_details(self):
		if self.transaction_type not in PAYMENT_TRANSACTION_TYPES or self.accounting_mode != "Direct":
			return
		bank_account = self.validate_settlement_account("bank_account")
		if bank_account == self.clearing_account:
			frappe.throw(_("Bank or Cash Account and Clearing Account must be different."))

	def validate_settlement_account(self, field):
		account = self.get(field)
		if not account:
			frappe.throw(_("Set {0} on the Share Transaction.").format(_(self.meta.get_label(field))))
		validate_account(account, self.company, self.currency, SETTLEMENT_ROOT_TYPES[field])
		return account

	def create_direct_payment_entry(self):
		if self.transaction_type in PAYMENT_TRANSACTION_TYPES and self.accounting_mode == "Direct":
			self.create_settlement_payment_entry(submit=True)

	def create_settlement_payment_entry(self, submit=False, posting_date=None):
		payment_entry = self.build_payment_entry(posting_date)
		payment_entry.insert()
		if submit:
			payment_entry.submit()
		self.db_set(
			{
				"payment_entry": payment_entry.name,
				"mode_of_payment": self.mode_of_payment,
				"bank_account": self.bank_account,
				"reference_no": self.reference_no,
				"reference_date": self.reference_date,
			},
			update_modified=False,
		)
		return payment_entry.name

	def build_payment_entry(self, posting_date=None):
		paid_from, paid_to = self.get_payment_entry_direction()
		payment_entry = frappe.new_doc("Payment Entry")
		for dimension in get_accounting_dimensions():
			payment_entry.set(dimension, self.get(dimension))
		payment_entry.update(
			{
				"payment_type": "Internal Transfer",
				"company": self.company,
				"posting_date": posting_date or self.posting_date,
				"mode_of_payment": self.mode_of_payment,
				"paid_from": paid_from,
				"paid_to": paid_to,
				"paid_amount": self.total_amount,
				"received_amount": self.total_amount,
				"source_exchange_rate": 1,
				"target_exchange_rate": 1,
				"reference_no": self.reference_no,
				"reference_date": self.reference_date,
				"remarks": _("Settlement of Share Transaction {0}").format(self.name),
			}
		)
		return payment_entry

	def get_payment_entry_direction(self):
		if self.transaction_type == "Buyback":
			return self.bank_account, self.clearing_account
		return self.clearing_account, self.bank_account

	def set_payment_details(self, bank_account, mode_of_payment, reference_no, reference_date):
		self.bank_account = bank_account or self.bank_account
		self.mode_of_payment = mode_of_payment or self.mode_of_payment
		self.reference_no = reference_no or self.reference_no
		self.reference_date = reference_date or self.reference_date

	def validate_can_create_payment_entry(self):
		if self.docstatus != 1 or self.transaction_type not in PAYMENT_TRANSACTION_TYPES:
			frappe.throw(_("Submit an Issue, Buyback or Reissue before creating its Payment Entry."))
		if self.get_active_payment_entry():
			frappe.throw(
				_("Payment Entry {0} already exists for this Share Transaction.").format(self.payment_entry)
			)

	def get_active_payment_entry(self):
		if not self.payment_entry:
			return None
		status = frappe.db.get_value("Payment Entry", self.payment_entry, "docstatus")
		return self.payment_entry if status in (0, 1) else None

	def assert_payment_entry_unreconciled(self):
		if self.payment_entry and self.has_bank_allocation():
			frappe.throw(_("Unreconcile the linked Payment Entry before cancelling this Share Transaction."))

	def has_bank_allocation(self):
		payment = frappe.qb.DocType("Bank Transaction Payments")
		bank = frappe.qb.DocType("Bank Transaction")
		return (
			frappe.qb.from_(payment)
			.join(bank)
			.on(bank.name == payment.parent)
			.select(payment.name)
			.where(
				(payment.payment_document == "Payment Entry")
				& (payment.payment_entry == self.payment_entry)
				& (bank.docstatus == 1)
				& (payment.allocated_amount > 0)
			)
			.limit(1)
		).run()

	def cancel_payment_entry(self):
		active = self.get_active_payment_entry()
		if not active:
			return
		payment_entry = frappe.get_doc("Payment Entry", active, for_update=True)
		if payment_entry.docstatus == 1:
			payment_entry.flags.ignore_links = True
			payment_entry.cancel()
			return
		self.db_set("payment_entry", None, update_modified=False)
		frappe.delete_doc("Payment Entry", active)
