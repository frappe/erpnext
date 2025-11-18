# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SubcontractReturnDetails(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		item_code: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		po_item_code: DF.Link | None
		po_qty: DF.Float
		purchase_order: DF.Link | None
		return_qty: DF.Float
		stock_entry: DF.Link | None
		subcontracting_order: DF.Link | None
		uom: DF.Data | None
	# end: auto-generated types
	pass
