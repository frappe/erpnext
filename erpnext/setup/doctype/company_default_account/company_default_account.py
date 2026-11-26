# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CompanyDefaultAccount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		purpose: DF.Autocomplete
	# end: auto-generated types

	_DOCTYPE_NAME = "Company Default Account"
