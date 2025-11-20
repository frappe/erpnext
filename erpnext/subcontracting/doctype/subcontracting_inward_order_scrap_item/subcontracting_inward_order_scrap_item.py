# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SubcontractingInwardOrderScrapItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		delivered_qty: DF.Float
		fg_item_code: DF.Link
		item_code: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		produced_qty: DF.Float
		reference_name: DF.Data
		stock_uom: DF.Link
		warehouse: DF.Link
	# end: auto-generated types

	pass
