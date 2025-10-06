# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


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

	pass
