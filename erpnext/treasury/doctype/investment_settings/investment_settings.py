# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.treasury.doctype.investment.investment import ACCOUNT_FIELDS, validate_company_links


class InvestmentSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		accrued_interest_account: DF.Link | None
		charges_account: DF.Link | None
		company: DF.Link | None
		dividend_income_account: DF.Link | None
		fair_value_adjustment_account: DF.Link | None
		interest_income_account: DF.Link | None
		investment_account: DF.Link | None
		realised_gain_loss_account: DF.Link | None
		tax_withheld_receivable_account: DF.Link | None
		unrealised_gain_loss_account: DF.Link | None
	# end: auto-generated types

	def validate(self):
		validate_company_links(self, ACCOUNT_FIELDS)


def get_default_account(company, fieldname):
	"""Default ledger account from Investment Settings, only when they are set up for this company."""
	settings = frappe.get_cached_doc("Investment Settings")
	if settings.company != company:
		return None

	return settings.get(fieldname)
