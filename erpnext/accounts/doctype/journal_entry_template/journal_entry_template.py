# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class JournalEntryTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.journal_entry_template_account.journal_entry_template_account import (
			JournalEntryTemplateAccount,
		)

		accounts: DF.Table[JournalEntryTemplateAccount]
		company: DF.Link
		is_opening: DF.Literal["No", "Yes"]
		multi_currency: DF.Check
		naming_series: DF.Literal
		template_title: DF.Data
		voucher_type: DF.Literal[
			"Journal Entry",
			"Inter Company Journal Entry",
			"Bank Entry",
			"Cash Entry",
			"Credit Card Entry",
			"Debit Note",
			"Credit Note",
			"Contra Entry",
			"Excise Entry",
			"Write Off Entry",
			"Opening Entry",
			"Depreciation Entry",
			"Exchange Rate Revaluation",
		]
	# end: auto-generated types

	def validate(self):
		self.validate_party()

	def validate_party(self):
		"""
		Loop over all accounts and see if party and party type is set correctly
		"""
		for account in self.accounts:
			if account.party_type:
				account_type = frappe.get_cached_value("Account", account.account, "account_type")
				if account_type not in ["Receivable", "Payable"]:
					frappe.throw(
						_(
							"Check row {0} for account {1}: Party Type is only allowed for Receivable or Payable accounts"
						).format(account.idx, account.account)
					)

			if account.party and not account.party_type:
				frappe.throw(
					_("Check row {0} for account {1}: Party is only allowed if Party Type is set").format(
						account.idx, account.account
					)
				)


@frappe.whitelist()
def get_naming_series():
	return frappe.get_meta("Journal Entry").get_field("naming_series").options
