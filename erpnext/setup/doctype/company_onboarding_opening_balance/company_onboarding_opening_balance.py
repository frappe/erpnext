# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CompanyOnboardingOpeningBalance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		credit: DF.Currency
		debit: DF.Currency
		journal_entry: DF.Link | None
		original_account: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		root_type: DF.Data | None
		status: DF.Literal["Draft", "Posted"]
	# end: auto-generated types

	_DOCTYPE_NAME = "Company Onboarding Opening Balance"
