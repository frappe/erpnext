# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class GoodsInwardNoteItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		item_code: DF.Link
		item_name: DF.Data | None
		order_item: DF.Data | None
		qty: DF.Float
		quality_inspection: DF.Link | None
		received_qty: DF.Float
		returned_qty: DF.Float
		supplier_reference: DF.Data | None
		uom: DF.Link | None
	# end: auto-generated types

	pass
