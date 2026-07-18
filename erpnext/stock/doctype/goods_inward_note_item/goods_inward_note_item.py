# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class GoodsInwardNoteItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		conversion_factor: DF.Float
		item_code: DF.Link
		item_name: DF.Data | None
		order_item: DF.Data | None
		qty: DF.Float
		received_qty: DF.Float
		stock_qty: DF.Float
		stock_uom: DF.Link | None
		supplier_reference: DF.Data | None
		uom: DF.Link | None
	# end: auto-generated types

	pass
