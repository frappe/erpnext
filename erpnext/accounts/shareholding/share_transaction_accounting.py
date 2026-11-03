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
from erpnext.accounts.shareholding.share_ranges import get_treasury_cost
from erpnext.accounts.shareholding.share_settlement import PAYMENT_TRANSACTION_TYPES

ACCOUNTING_TRANSACTION_TYPES = {"Issue", "Buyback", "Retirement", "Reissue"}
EQUITY_ACCOUNT_FIELDS = (
	"share_capital_account",
	"securities_premium_account",
	"treasury_shares_account",
	"treasury_gain_loss_account",
)
EQUITY_ACCOUNTS_BY_TYPE = {
	"Issue": ("share_capital_account", "securities_premium_account"),
	"Buyback": ("treasury_shares_account",),
	"Reissue": ("treasury_shares_account", "treasury_gain_loss_account"),
	"Retirement": ("share_capital_account", "treasury_shares_account", "treasury_gain_loss_account"),
}


class TransactionAccounting:
	@property
	def company_currency(self):
		return self.currency

	def set_accounting_defaults(self):
		settings = self.find_accounting_settings()
		self.set_equity_account_defaults(settings)
		self.set_payment_defaults(settings)

	def set_equity_account_defaults(self, settings):
		used = EQUITY_ACCOUNTS_BY_TYPE.get(self.transaction_type, ())
		for field in EQUITY_ACCOUNT_FIELDS:
			if field not in used:
				self.set(field, None)
			elif not self.get(field) and settings:
				self.set(field, settings.get(field))

	def find_accounting_settings(self):
		name = frappe.db.get_value("Share Accounting Settings", {"company": self.company})
		return frappe.get_doc("Share Accounting Settings", name) if name else None

	def set_display_accounting_values(self):
		"""Populate amounts that can be calculated before folios are resolved."""
		self.share_capital_amount = 0
		self.securities_premium_amount = 0
		self.treasury_cost_per_share = 0
		self.treasury_cost = 0
		self.treasury_gain_loss_amount = 0

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
		# Retirement compares the cost with face value; Reissue with the price received.
		comparison_amount = face_amount if self.transaction_type == "Retirement" else flt(self.total_amount)
		self.treasury_gain_loss_amount = self.money(comparison_amount - flt(self.treasury_cost))

	def validate_accounting(self):
		if self.transaction_type not in ACCOUNTING_TRANSACTION_TYPES:
			return
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
		if flt(self.treasury_gain_loss_amount):
			required.append("treasury_gain_loss_account")
		return required

	def validate_accounts(self):
		required = self.get_required_equity_fields()
		accounts = [self.validate_equity_account(field) for field in required]
		if self.transaction_type in PAYMENT_TRANSACTION_TYPES:
			accounts.append(self.validate_settlement_account("clearing_account"))
		if len(set(accounts)) != len(accounts):
			frappe.throw(_("Each accounting role must use a separate Account."))

	def validate_equity_account(self, field):
		account = self.get(field)
		if not account:
			frappe.throw(
				_("Set {0} on the Share Transaction or in Share Accounting Settings for {1}.").format(
					_(self.meta.get_label(field)), self.company
				)
			)
		validate_account(account, self.company, self.currency, ACCOUNT_ROOT_TYPES[field])
		return account

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
			self.credit(self.share_capital_account, self.share_capital_amount),
			self.credit(self.securities_premium_account, self.securities_premium_amount),
		]

	def get_buyback_rows(self):
		return [
			self.debit(self.treasury_shares_account, self.treasury_cost),
			self.credit(self.clearing_account, self.treasury_cost),
		]

	def get_reissue_rows(self):
		return [
			self.debit(self.clearing_account, self.total_amount),
			self.credit(self.treasury_shares_account, self.treasury_cost),
			*self.get_gain_loss_rows(),
		]

	def get_retirement_rows(self):
		return [
			self.debit(self.share_capital_account, self.share_capital_amount),
			self.credit(self.treasury_shares_account, self.treasury_cost),
			*self.get_gain_loss_rows(),
		]

	def get_gain_loss_rows(self):
		account = self.treasury_gain_loss_account
		amount = flt(self.treasury_gain_loss_amount)
		return [self.credit(account, amount)] if amount > 0 else [self.debit(account, abs(amount))]

	def debit(self, account, amount):
		return {"account": account, "debit": self.money(amount), "credit": 0}

	def credit(self, account, amount):
		return {"account": account, "debit": 0, "credit": self.money(amount)}

	def make_accounting_gl_entries(self):
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

	@frappe.whitelist()
	def get_accounting_preview(self):
		if self.transaction_type not in ACCOUNTING_TRANSACTION_TYPES:
			return []
		if self.docstatus == 1:
			return self.get_posted_accounting_rows()
		self.set_accounting_defaults()
		self.prepare_preview_amounts()
		return self.get_accounting_rows()

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
			self.set_face_value()
		self.calculate_accounting_values()
