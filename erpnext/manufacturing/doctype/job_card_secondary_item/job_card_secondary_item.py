# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class JobCardSecondaryItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bom_secondary_item: DF.Data | None
		description: DF.SmallText | None
		item_code: DF.Link
		item_name: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		stock_qty: DF.Float
		stock_uom: DF.Link | None
		type: DF.Literal["Co-Product", "By-Product", "Scrap", "Additional Finished Good"]
	# end: auto-generated types

	pass
