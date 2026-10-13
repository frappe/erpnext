# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.accounts.shareholding.locking import lock_company

ACCOUNT_FIELDS = (
	"cash_or_bank_account",
	"share_capital_account",
	"securities_premium_account",
	"treasury_shares_account",
	"equity_adjustment_account",
)


class EquityAccountingSettings(Document):
	def validate(self):
		lock_company(self.company)
		currency = frappe.db.get_value("Company", self.company, "default_currency")
		accounts = []
		for field in ACCOUNT_FIELDS:
			if not self.get(field):
				continue
			roots = {"Asset", "Liability"} if field == "cash_or_bank_account" else {"Equity", "Liability"}
			validate_account(self.get(field), self.company, currency, roots)
			accounts.append(self.get(field))
		if len(accounts) != len(set(accounts)):
			frappe.throw(_("Each accounting role must use a separate Account."))


def validate_account(name, company, currency, root_types):
	account = frappe.db.get_value(
		"Account",
		name,
		["company", "is_group", "root_type", "account_type", "account_currency", "disabled"],
		as_dict=True,
	)
	if not account or account.disabled or account.is_group:
		frappe.throw(_("Account {0} must be an enabled ledger account.").format(name))
	if account.company != company or account.account_currency != currency:
		frappe.throw(
			_("Account {0} must belong to {1} and use currency {2}.").format(name, company, currency)
		)
	if account.root_type not in root_types:
		frappe.throw(_("Account {0} must have root type {1}.").format(name, ", ".join(sorted(root_types))))
	if account.account_type in {"Receivable", "Payable"}:
		frappe.throw(
			_(
				"Account {0} requires a party. Use a settlement clearing account for this V1 integration."
			).format(name)
		)
