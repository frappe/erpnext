# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class BOMCreatorOperation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bom_node_id: DF.Int
		operation: DF.Link
		operation_id: DF.Int
		output_item: DF.Link | None
		output_node_id: DF.Int
		output_quantity: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		time_in_mins: DF.Float
		workstation_type: DF.Link | None
	# end: auto-generated types

	pass
