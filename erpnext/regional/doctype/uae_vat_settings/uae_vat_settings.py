# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


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

	pass
