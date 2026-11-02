# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BOMCreatorMaterial(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bom_node_id: DF.Int
		from_operation_id: DF.Int
		item_code: DF.Link | None
		operation_id: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		part_node_id: DF.Int
		qty: DF.Float
		uom: DF.Link | None
	# end: auto-generated types

	pass
