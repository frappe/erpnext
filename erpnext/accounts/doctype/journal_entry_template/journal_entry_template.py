# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
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

	pass


@frappe.whitelist()
def get_naming_series():
	return frappe.get_meta("Journal Entry").get_field("naming_series").options
