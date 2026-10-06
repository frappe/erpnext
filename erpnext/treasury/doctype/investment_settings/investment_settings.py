# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.treasury.doctype.investment.investment import ACCOUNT_FIELDS, validate_company_links


class InvestmentSettings(Document):
	def validate(self):
		validate_company_links(self, ACCOUNT_FIELDS)


def get_default_account(company, fieldname):
	"""Default ledger account from Investment Settings, only when they are set up for this company."""
	settings = frappe.get_cached_doc("Investment Settings")
	if settings.company != company:
		return None

	return settings.get(fieldname)
