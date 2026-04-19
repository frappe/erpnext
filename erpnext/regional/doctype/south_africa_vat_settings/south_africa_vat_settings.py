# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext import get_region


class SouthAfricaVATSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.south_africa_vat_account.south_africa_vat_account import (
			SouthAfricaVATAccount,
		)

		company: DF.Link
		vat_accounts: DF.Table[SouthAfricaVATAccount]
	# end: auto-generated types

	def validate(self):
		self.validate_company_region()

	def validate_company_region(self):
		if self.company and get_region(self.company) != "South Africa":
			frappe.throw(_("Company {0} is not in South Africa.").format(frappe.bold(self.company)))
