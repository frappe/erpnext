# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Prepare and reverse the company journals for numbered share transactions."""

import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.accounts.shareholding.locking import lock_company
from erpnext.accounts.shareholding.ranges import get_treasury_cost

ACCOUNTING_TRANSACTION_TYPES = {"Issue", "Buyback", "Retirement", "Reissue"}


class TransactionAccounting:
	def set_display_accounting_values(self):
		"""Populate amounts that can be calculated before folios are resolved."""
		self.share_capital_amount = 0
		self.securities_premium_amount = 0
		self.treasury_cost_per_share = 0
		self.treasury_cost = 0
		self.equity_adjustment_amount = 0

		if self.transaction_type == "Issue" and flt(self.face_value_per_share) > 0:
			self.share_capital_amount = self.money(
				flt(self.face_value_per_share) * cint(self.number_of_shares)
			)
			self.securities_premium_amount = self.money(
				flt(self.total_amount) - flt(self.share_capital_amount)
			)
		elif self.transaction_type == "Buyback":
			self.treasury_cost_per_share = flt(self.rate_per_share)
			self.treasury_cost = flt(self.total_amount)

	def calculate_accounting_values(self):
		self.set_display_accounting_values()
		quantity = cint(self.number_of_shares)
		face_amount = self.money(flt(self.face_value_per_share) * quantity)

		if self.transaction_type == "Issue":
			self.share_capital_amount = face_amount
			self.securities_premium_amount = self.money(flt(self.total_amount) - self.share_capital_amount)
			if self.securities_premium_amount < 0:
				frappe.throw(
					_(
						"Issuing shares below face value is not supported. Rate Per Share must be at least {0}."
					).format(frappe.bold(self.face_value_per_share))
				)

		elif self.transaction_type == "Buyback":
			self.treasury_cost_per_share = flt(self.rate_per_share)
			self.treasury_cost = flt(self.total_amount)

		elif self.transaction_type in {"Retirement", "Reissue"}:
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
				comparison_amount = face_amount
			else:
				comparison_amount = flt(self.total_amount)

			self.equity_adjustment_amount = self.money(comparison_amount - flt(self.treasury_cost))

	def validate_accounting(self):
		from erpnext.accounts.doctype.equity_accounting_settings.equity_accounting_settings import (
			ACCOUNT_FIELDS,
			validate_account,
		)

		if self.transaction_type not in ACCOUNTING_TRANSACTION_TYPES:
			return

		settings_name = frappe.db.get_value("Equity Accounting Settings", {"company": self.company})
		if not settings_name:
			frappe.throw(
				_("Configure Equity Accounting Settings for company {0} before submitting.").format(
					self.company
				)
			)
		settings = frappe.get_doc("Equity Accounting Settings", settings_name)
		self.settlement_account = settings.cash_or_bank_account
		# Ignore any account values supplied through the transaction API.
		for field in ACCOUNT_FIELDS:
			self.set(field, settings.get(field))

		required = []
		if self.transaction_type in {"Issue", "Buyback", "Reissue"}:
			required.append("cash_or_bank_account")
		if self.transaction_type in {"Issue", "Retirement"}:
			required.append("share_capital_account")
		if self.transaction_type in {"Buyback", "Retirement", "Reissue"}:
			required.append("treasury_shares_account")
		if flt(self.securities_premium_amount):
			required.append("securities_premium_account")
		if flt(self.equity_adjustment_amount):
			required.append("equity_adjustment_account")

		currency = frappe.db.get_value("Company", self.company, "default_currency")
		if self.currency != currency:
			frappe.throw(_("Equity accounting requires the company currency {0}.").format(currency))
		for field in required:
			account = self.get(field)
			if not account:
				frappe.throw(
					_("Set {0} in Equity Accounting Settings for {1}.").format(
						settings.meta.get_label(field), self.company
					)
				)
			roots = {"Asset", "Liability"} if field == "cash_or_bank_account" else {"Equity", "Liability"}
			validate_account(account, self.company, currency, roots)
		if len({self.get(field) for field in required}) != len(required):
			frappe.throw(_("Each accounting role must use a separate Account."))

	def money(self, value):
		return flt(value, self.precision("total_amount"))

	@frappe.whitelist(methods=["POST"])
	def create_accounting_journal_entry(self):
		self.reload()
		self.check_permission("write")
		# Document submission and cancellation lock the transaction before the company.
		frappe.db.get_value("Share Transaction", self.name, "name", for_update=True)
		self.reload()
		lock_company(self.company)
		if self.transaction_type == "Transfer":
			frappe.throw(_("A shareholder-to-shareholder Transfer does not create a company Journal Entry."))
		if self.transaction_type not in ACCOUNTING_TRANSACTION_TYPES:
			frappe.throw(_("This transaction type does not support accounting automation."))
		if self.docstatus != 1:
			frappe.throw(_("Submit the Share Transaction before creating its Journal Entry."))

		existing = frappe.db.get_value(
			"Journal Entry", {"share_transaction": self.name, "docstatus": ["!=", 2]}, "name"
		)
		if existing:
			frappe.get_doc("Journal Entry", existing).check_permission("read")
			return existing
		if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
			frappe.throw(
				_("The linked Journal Entry was cancelled. Cancel and amend the Share Transaction to repost.")
			)

		self.calculate_accounting_values()
		self.validate_accounting()

		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.voucher_type = "Journal Entry"
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date
		journal_entry.share_transaction = self.name
		journal_entry.user_remark = _(
			"Equity accounting for Share Transaction {0}. Draft only: verify settlement/payment "
			"and accounts before submitting."
		).format(self.name)

		accounting_rows = self.get_accounting_rows()
		journal_entry.set_new_name()
		self.db_set(
			{
				"journal_entry": journal_entry.name,
				"accounting_snapshot": frappe.as_json(accounting_rows),
				"settlement_account": self.settlement_account,
			},
			update_modified=False,
		)
		for row in accounting_rows:
			journal_entry.append("accounts", row)

		journal_entry.insert()
		self.db_set(
			{
				"journal_entry": journal_entry.name,
				"settlement_account": self.settlement_account,
				"share_capital_amount": self.share_capital_amount,
				"securities_premium_amount": self.securities_premium_amount,
				"treasury_cost_per_share": self.treasury_cost_per_share,
				"treasury_cost": self.treasury_cost,
				"equity_adjustment_amount": self.equity_adjustment_amount,
			},
			update_modified=False,
		)
		return journal_entry.name

	def get_accounting_rows(self):
		rows = []

		def debit(account, amount):
			if flt(amount):
				rows.append({"account": account, "debit_in_account_currency": self.money(amount)})

		def credit(account, amount):
			if flt(amount):
				rows.append({"account": account, "credit_in_account_currency": self.money(amount)})

		if self.transaction_type == "Issue":
			debit(self.cash_or_bank_account, self.total_amount)
			credit(self.share_capital_account, self.share_capital_amount)
			credit(self.securities_premium_account, self.securities_premium_amount)

		elif self.transaction_type == "Buyback":
			debit(self.treasury_shares_account, self.treasury_cost)
			credit(self.cash_or_bank_account, self.treasury_cost)

		elif self.transaction_type == "Reissue":
			debit(self.cash_or_bank_account, self.total_amount)
			credit(self.treasury_shares_account, self.treasury_cost)
			if flt(self.equity_adjustment_amount) > 0:
				credit(self.equity_adjustment_account, self.equity_adjustment_amount)
			elif flt(self.equity_adjustment_amount) < 0:
				debit(self.equity_adjustment_account, abs(self.equity_adjustment_amount))

		elif self.transaction_type == "Retirement":
			debit(self.share_capital_account, self.share_capital_amount)
			credit(self.treasury_shares_account, self.treasury_cost)
			if flt(self.equity_adjustment_amount) > 0:
				credit(self.equity_adjustment_account, self.equity_adjustment_amount)
			elif flt(self.equity_adjustment_amount) < 0:
				debit(self.equity_adjustment_account, abs(self.equity_adjustment_amount))

		return rows

	def cancel_accounting_journal_entry(self):
		if not self.journal_entry or not frappe.db.exists("Journal Entry", self.journal_entry):
			return

		journal_entry = frappe.get_doc("Journal Entry", self.journal_entry)
		if journal_entry.docstatus == 1:
			previous = frappe.flags.get("share_transaction_cancelling")
			frappe.flags.share_transaction_cancelling = self.name
			try:
				journal_entry.cancel()
			finally:
				frappe.flags.share_transaction_cancelling = previous
		elif journal_entry.docstatus == 0:
			self.db_set("journal_entry", None, update_modified=False)
			frappe.delete_doc("Journal Entry", journal_entry.name)
