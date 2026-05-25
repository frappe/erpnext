# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PartyImportLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address_created: DF.Check
		contact_created: DF.Check
		docname: DF.Data | None
		message: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party_code: DF.Data | None
		party_created: DF.Check
		party_name: DF.Data | None
		row_index: DF.Int
		status: DF.Literal["Success", "Skipped", "Error"]
	# end: auto-generated types

	pass
