# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Post the company accounting for numbered share transactions."""

import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.accounts.doctype.share_accounting_settings.share_accounting_settings import (
	ACCOUNT_ROOT_TYPES,
	validate_account,
)
from erpnext.accounts.general_ledger import make_gl_entries, make_reverse_gl_entries
from erpnext.accounts.services.base_gl_composer import get_gl_dict
from erpnext.accounts.shareholding.company_lock import lock_company
from erpnext.accounts.shareholding.share_ranges import get_treasury_cost

ACCOUNTING_TRANSACTION_TYPES = {"Issue", "Buyback", "Retirement", "Reissue"}
PAYMENT_TRANSACTION_TYPES = {"Issue", "Buyback", "Reissue"}
EQUITY_ACCOUNT_FIELDS = (
	"share_capital_account",
	"securities_premium_account",
	"treasury_shares_account",
	"treasury_adjustment_account",
)
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
	return frappe.db.get_value(
		"Mode of Payment Account", {"parent": mode_of_payment, "company": company}, "default_account"
	)


class TransactionAccounting:
	@property
	def company_currency(self):
		return self.currency

	def set_display_accounting_values(self):
		"""Populate amounts that can be calculated before folios are resolved."""
		self.share_capital_amount = 0
		self.securities_premium_amount = 0
		self.treasury_cost_per_share = 0
		self.treasury_cost = 0
		self.treasury_adjustment_amount = 0

		if self.transaction_type == "Issue" and flt(self.face_value_per_share) > 0:
			self.set_issue_amounts()
		elif self.transaction_type == "Buyback":
			self.set_buyback_amounts()

	def set_issue_amounts(self):
		self.share_capital_amount = self.money(flt(self.face_value_per_share) * cint(self.number_of_shares))
		self.securities_premium_amount = self.money(flt(self.total_amount) - self.share_capital_amount)

	def set_buyback_amounts(self):
		self.treasury_cost_per_share = flt(self.rate_per_share)
		self.treasury_cost = flt(self.total_amount)

	def calculate_accounting_values(self):
		self.set_display_accounting_values()
		if self.transaction_type == "Issue":
			self.validate_issue_premium()
		elif self.transaction_type in {"Retirement", "Reissue"}:
			self.set_treasury_disposal_amounts()

	def validate_issue_premium(self):
		if self.securities_premium_amount < 0:
			frappe.throw(
				_(
					"Issuing shares below face value is not supported. Rate Per Share must be at least {0}."
				).format(frappe.bold(self.face_value_per_share))
			)

	def set_treasury_disposal_amounts(self):
		quantity = cint(self.number_of_shares)
		face_amount = self.money(flt(self.face_value_per_share) * quantity)
		self.treasury_cost = get_treasury_cost(
			company=self.company,
			share_class=self.share_class,
			share_folio=self.from_folio,
			start=self.from_share_number,
			end=self.to_share_number,
			currency=self.currency,
			exclude_transaction=self.name,
		)
		self.treasury_cost_per_share = self.treasury_cost / quantity
		if self.transaction_type == "Retirement":
			self.share_capital_amount = face_amount
		comparison_amount = face_amount if self.transaction_type == "Retirement" else flt(self.total_amount)
		self.treasury_adjustment_amount = self.money(comparison_amount - flt(self.treasury_cost))

	def find_accounting_settings(self):
		name = frappe.db.get_value("Share Accounting Settings", {"company": self.company})
		return frappe.get_doc("Share Accounting Settings", name) if name else None

	def get_accounting_settings(self):
		settings = self.find_accounting_settings()
		if not settings:
			frappe.throw(
				_("Configure Share Accounting Settings for company {0} before submitting.").format(
					self.company
				)
			)
		return settings

	def set_accounting_defaults(self):
		if self.transaction_type not in PAYMENT_TRANSACTION_TYPES:
			self.clear_payment_fields()
			return
		settings = self.find_accounting_settings()
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

	def load_equity_accounts(self, settings=None):
		settings = settings or self.get_accounting_settings()
		self.equity_accounts = {field: settings.get(field) for field in EQUITY_ACCOUNT_FIELDS}

	def validate_accounting(self):
		if self.transaction_type not in ACCOUNTING_TRANSACTION_TYPES:
			return
		settings = self.get_accounting_settings()
		self.load_equity_accounts(settings)
		self.validate_company_currency()
		self.validate_accounts()
		self.validate_payment_details()

	def validate_company_currency(self):
		currency = frappe.db.get_value("Company", self.company, "default_currency")
		if self.currency != currency:
			frappe.throw(_("Equity accounting requires the company currency {0}.").format(currency))

	def get_required_equity_fields(self):
		required = []
		if self.transaction_type in {"Issue", "Retirement"}:
			required.append("share_capital_account")
		if self.transaction_type in {"Buyback", "Retirement", "Reissue"}:
			required.append("treasury_shares_account")
		if flt(self.securities_premium_amount):
			required.append("securities_premium_account")
		if flt(self.treasury_adjustment_amount):
			required.append("treasury_adjustment_account")
		return required

	def validate_accounts(self):
		required = self.get_required_equity_fields()
		accounts = [self.validate_equity_account(field) for field in required]
		if self.transaction_type in PAYMENT_TRANSACTION_TYPES:
			accounts.append(self.validate_settlement_account("clearing_account"))
		if len(set(accounts)) != len(accounts):
			frappe.throw(_("Each accounting role must use a separate Account."))

	def validate_equity_account(self, field):
		account = self.equity_accounts.get(field)
		if not account:
			frappe.throw(
				_("Set {0} in Share Accounting Settings for {1}.").format(
					frappe.get_meta("Share Accounting Settings").get_label(field), self.company
				)
			)
		validate_account(account, self.company, self.currency, ACCOUNT_ROOT_TYPES[field])
		return account

	def validate_settlement_account(self, field):
		account = self.get(field)
		if not account:
			frappe.throw(_("Set {0} on the Share Transaction.").format(self.meta.get_label(field)))
		validate_account(account, self.company, self.currency, SETTLEMENT_ROOT_TYPES[field])
		return account

	def validate_payment_details(self):
		if self.transaction_type not in PAYMENT_TRANSACTION_TYPES or self.accounting_mode != "Direct":
			return
		bank_account = self.validate_settlement_account("bank_account")
		if bank_account == self.clearing_account:
			frappe.throw(_("Bank or Cash Account and Clearing Account must be different."))

	def money(self, value):
		return flt(value, self.precision("total_amount"))

	def get_accounting_rows(self):
		builders = {
			"Issue": self.get_issue_rows,
			"Buyback": self.get_buyback_rows,
			"Reissue": self.get_reissue_rows,
			"Retirement": self.get_retirement_rows,
		}
		rows = builders[self.transaction_type]()
		return [row for row in rows if flt(row["debit"]) or flt(row["credit"])]

	def get_issue_rows(self):
		return [
			self.debit(self.clearing_account, self.total_amount),
			self.credit(self.equity_accounts["share_capital_account"], self.share_capital_amount),
			self.credit(self.equity_accounts["securities_premium_account"], self.securities_premium_amount),
		]

	def get_buyback_rows(self):
		return [
			self.debit(self.equity_accounts["treasury_shares_account"], self.treasury_cost),
			self.credit(self.clearing_account, self.treasury_cost),
		]

	def get_reissue_rows(self):
		return [
			self.debit(self.clearing_account, self.total_amount),
			self.credit(self.equity_accounts["treasury_shares_account"], self.treasury_cost),
			*self.get_adjustment_rows(),
		]

	def get_retirement_rows(self):
		return [
			self.debit(self.equity_accounts["share_capital_account"], self.share_capital_amount),
			self.credit(self.equity_accounts["treasury_shares_account"], self.treasury_cost),
			*self.get_adjustment_rows(),
		]

	def get_adjustment_rows(self):
		account = self.equity_accounts["treasury_adjustment_account"]
		amount = flt(self.treasury_adjustment_amount)
		return [self.credit(account, amount)] if amount > 0 else [self.debit(account, abs(amount))]

	def debit(self, account, amount):
		return {"account": account, "debit": self.money(amount), "credit": 0}

	def credit(self, account, amount):
		return {"account": account, "debit": 0, "credit": self.money(amount)}

	def make_accounting_gl_entries(self):
		self.load_equity_accounts()
		rows = self.get_accounting_rows()
		make_gl_entries([self.get_gl_entry(row, rows) for row in rows], merge_entries=False)

	def get_gl_entry(self, row, rows):
		against = ", ".join(
			sorted({other["account"] for other in rows if other["account"] != row["account"]})
		)
		return get_gl_dict(
			self,
			{
				"account": row["account"],
				"against": against,
				"debit": row["debit"],
				"credit": row["credit"],
				"debit_in_account_currency": row["debit"],
				"credit_in_account_currency": row["credit"],
				"remarks": self.remarks or _("Share Transaction {0}").format(self.name),
			},
		)

	def reverse_accounting_gl_entries(self):
		self.ignore_linked_doctypes = ("GL Entry", "Payment Ledger Entry")
		make_reverse_gl_entries(
			voucher_type=self.doctype, voucher_no=self.name, posting_date=self.get_reversal_date()
		)

	def get_payment_entry_direction(self):
		if self.transaction_type == "Buyback":
			return self.bank_account, self.clearing_account
		return self.clearing_account, self.bank_account

	def build_payment_entry(self):
		paid_from, paid_to = self.get_payment_entry_direction()
		payment_entry = frappe.new_doc("Payment Entry")
		payment_entry.update(
			{
				"payment_type": "Internal Transfer",
				"company": self.company,
				"posting_date": self.posting_date,
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

	def create_settlement_payment_entry(self, submit=False):
		payment_entry = self.build_payment_entry()
		payment_entry.insert()
		if submit:
			payment_entry.submit()
		self.db_set("payment_entry", payment_entry.name, update_modified=False)
		return payment_entry.name

	@frappe.whitelist(methods=["POST"])
	def make_payment_entry(self):
		self.reload()
		self.check_permission("write")
		frappe.db.get_value("Share Transaction", self.name, "name", for_update=True)
		lock_company(self.company)
		self.validate_can_create_payment_entry()
		self.validate_settlement_account("bank_account")
		return self.create_settlement_payment_entry()

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

	def create_direct_payment_entry(self):
		if self.transaction_type in PAYMENT_TRANSACTION_TYPES and self.accounting_mode == "Direct":
			self.create_settlement_payment_entry(submit=True)

	def assert_payment_entry_unreconciled(self):
		if not self.payment_entry:
			return
		payment = frappe.qb.DocType("Bank Transaction Payments")
		bank = frappe.qb.DocType("Bank Transaction")
		allocated = (
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
		if allocated:
			frappe.throw(_("Unreconcile the linked Payment Entry before cancelling this Share Transaction."))

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

	@frappe.whitelist()
	def get_accounting_preview(self):
		if self.transaction_type not in ACCOUNTING_TRANSACTION_TYPES:
			return []
		if self.docstatus == 1:
			return self.get_posted_accounting_rows()
		self.set_accounting_defaults()
		self.load_equity_accounts()
		self.prepare_preview_amounts()
		return [self.get_preview_row(row) for row in self.get_accounting_rows()]

	def get_posted_accounting_rows(self):
		return frappe.get_all(
			"GL Entry",
			filters={"voucher_type": self.doctype, "voucher_no": self.name, "is_cancelled": 0},
			fields=["account", "debit", "credit"],
			order_by="creation",
		)

	def prepare_preview_amounts(self):
		self.calculate_quantities_and_values()
		if self.transaction_type in {"Retirement", "Reissue"}:
			self.from_folio = frappe.db.get_value(
				"Share Folio", {"company": self.company, "is_treasury": 1}, "name"
			)
		self.calculate_accounting_values()

	def get_preview_row(self, row):
		return {"account": row["account"], "debit": row["debit"], "credit": row["credit"]}
