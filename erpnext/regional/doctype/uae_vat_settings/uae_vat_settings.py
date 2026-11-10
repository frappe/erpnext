# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext import get_region


class UAEVATSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.regional.doctype.uae_vat_account.uae_vat_account import UAEVATAccount

		company: DF.Link
		uae_vat_accounts: DF.Table[UAEVATAccount]
	# end: auto-generated types

	def validate(self):
		self.validate_company_region()
		self.validate_accounts()

	def validate_company_region(self):
		if self.company and get_region(self.company) != "United Arab Emirates":
			frappe.throw(_("Company {0} is not in United Arab Emirates.").format(frappe.bold(self.company)))

	def validate_accounts(self):
		accounts = set()
		for row in self.uae_vat_accounts:
			if not row.account:
				frappe.throw(_("Row #{0}: Account is mandatory").format(row.idx))
			if row.account in accounts:
				frappe.throw(_("Row #{0}: Account {1} is added more than once").format(row.idx, row.account))

			self.validate_account(row)
			accounts.add(row.account)

	def validate_account(self, row):
		company, is_group = frappe.get_cached_value("Account", row.account, ["company", "is_group"])
		if company != self.company:
			frappe.throw(
				_("Row #{0}: Account {1} does not belong to company {2}").format(
					row.idx, row.account, self.company
				)
			)
		if is_group:
			frappe.throw(_("Row #{0}: Account {1} is a group account").format(row.idx, row.account))
