# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
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

		from erpnext.treasury.doctype.investment_default_account.investment_default_account import (
			InvestmentDefaultAccount,
		)

		company: DF.Link | None
		company_accounts: DF.Table[InvestmentDefaultAccount]
	# end: auto-generated types

	def validate(self):
		companies = set()
		for row in self.company_accounts:
			if row.company in companies:
				frappe.throw(
					_("Row #{0}: Company {1} is added more than once").format(
						row.idx, frappe.bold(row.company)
					)
				)

			companies.add(row.company)
			validate_company_links(row, ACCOUNT_FIELDS)


def get_default_account(company, fieldname):
	"""Default ledger account of the company from Investment Settings, if it has one."""
	settings = frappe.get_cached_doc("Investment Settings")
	row = next((row for row in settings.company_accounts if row.company == company), None)
	return row.get(fieldname) if row else None
