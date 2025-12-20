# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class PurchaseReceiptItemSupplied(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
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
		purchase_order: DF.Link | None
		rate: DF.Currency
		reference_name: DF.Data | None
		required_qty: DF.Float
		rm_item_code: DF.Link | None
		serial_no: DF.Text | None
		stock_uom: DF.Link | None
	# end: auto-generated types

	pass
