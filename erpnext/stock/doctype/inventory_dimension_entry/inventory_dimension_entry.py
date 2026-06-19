# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class InventoryDimensionEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		is_cancelled: DF.Check
		is_outward: DF.Check
		item_code: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		posting_datetime: DF.Datetime | None
		qty: DF.Float
		voucher_detail_no: DF.Data | None
		voucher_no: DF.Data | None
		voucher_type: DF.Data | None
		warehouse: DF.Link | None
	# end: auto-generated types

	pass
