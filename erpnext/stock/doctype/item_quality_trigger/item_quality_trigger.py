# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class ItemQualityTrigger(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		applicable_warehouse: DF.Link | None
		condition: DF.Code | None
		customer: DF.Link | None
		document_type: DF.Literal[
			"Purchase Receipt",
			"Purchase Invoice",
			"Subcontracting Receipt",
			"Delivery Note",
			"Sales Invoice",
			"Stock Entry",
		]
		inspection_basis: DF.Literal["Sample", "Each Quantity"]
		inspection_template: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qc_mode: DF.Literal["Quarantine", "Block", "Warn", "Monitor"]
		sample_size: DF.Float
		sample_size_is_percentage: DF.Check
		supplier: DF.Link | None
		transaction_sub_type: DF.Literal[
			"",
			"Material Receipt",
			"Material Issue",
			"Material Transfer",
			"Material Transfer for Manufacture",
			"Manufacture",
			"Repack",
			"Send to Subcontractor",
			"Disassemble",
		]
		warehouse_role: DF.Literal["Inbound", "Outbound"]
	# end: auto-generated types

	pass
