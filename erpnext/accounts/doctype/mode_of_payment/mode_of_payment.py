# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class ModeofPayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.mode_of_payment_account.mode_of_payment_account import (
			ModeofPaymentAccount,
		)

		accounts: DF.Table[ModeofPaymentAccount]
		enabled: DF.Check
		mode_of_payment: DF.Data
		type: DF.Literal["Cash", "Bank", "General", "Phone"]
	# end: auto-generated types

	def validate(self):
		self.validate_accounts()
		self.validate_repeating_companies()
		self.validate_pos_mode_of_payment()

	def validate_repeating_companies(self):
		"""Error when Same Company is entered multiple times in accounts"""
		accounts_list = []
		for entry in self.accounts:
			accounts_list.append(entry.company)

		if len(accounts_list) != len(set(accounts_list)):
			frappe.throw(_("Same Company is entered more than once"))

	def validate_accounts(self):
		for entry in self.accounts:
			account = frappe.get_cached_value(
				"Account",
				entry.default_account,
				["company", "is_group", "account_type", "disabled"],
				as_dict=True,
			)
			if not account or account.company != entry.company:
				frappe.throw(
					_("Account {0} does not match with Company {1} in Mode of Account: {2}").format(
						entry.default_account, entry.company, self.name
					)
				)

			if account.is_group or account.account_type not in ("Bank", "Cash", "Receivable"):
				frappe.throw(
					_(
						"Row {0}: Account {1} must be a ledger account of type Bank, Cash or Receivable."
					).format(entry.idx, frappe.bold(entry.default_account))
				)
			if account.disabled:
				frappe.throw(
					_("Row {0}: Account {1} is disabled.").format(
						entry.idx, frappe.bold(entry.default_account)
					)
				)

	def validate_pos_mode_of_payment(self):
		if not self.enabled:
			pos_profiles = frappe.get_all(
				"POS Payment Method",
				filters={"parenttype": "POS Profile", "mode_of_payment": self.name},
				pluck="parent",
			)

			if pos_profiles:
				message = _(
					"POS Profile {0} contains Mode of Payment {1}. Please remove them to disable this mode."
				).format(frappe.bold(", ".join(pos_profiles)), frappe.bold(str(self.name)))
				frappe.throw(message, title=_("Not Allowed"))


def validate_enabled_mode_of_payment(mode_of_payment):
	if mode_of_payment and not frappe.get_cached_value("Mode of Payment", mode_of_payment, "enabled"):
		frappe.throw(_("Mode of Payment {0} is disabled.").format(frappe.bold(mode_of_payment)))
