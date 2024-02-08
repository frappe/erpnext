# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SubcontractingReceiptSuppliedItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		available_qty_for_consumption: DF.Float
		batch_no: DF.Link | None
		bom_detail_no: DF.Data | None
		consumed_qty: DF.Float
		conversion_factor: DF.Float
		current_stock: DF.Float
		description: DF.TextEditor | None
		item_name: DF.Data | None
		main_item_code: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rate: DF.Currency
		reference_name: DF.Data | None
		required_qty: DF.Float
		rm_item_code: DF.Link | None
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.Text | None
		stock_uom: DF.Link | None
		subcontracting_order: DF.Link | None
		use_serial_batch_fields: DF.Check
	# end: auto-generated types

	pass
