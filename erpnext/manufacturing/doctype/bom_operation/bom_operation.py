# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class BOMOperation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		base_cost_per_unit: DF.Float
		base_hour_rate: DF.Currency
		base_operating_cost: DF.Currency
		batch_size: DF.Int
		cost_per_unit: DF.Float
		description: DF.TextEditor | None
		fixed_time: DF.Check
		hour_rate: DF.Currency
		image: DF.Attach | None
		operating_cost: DF.Currency
		operation: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		sequence_id: DF.Int
		set_cost_based_on_bom_qty: DF.Check
		time_in_mins: DF.Float
		workstation: DF.Link | None
		workstation_type: DF.Link | None
	# end: auto-generated types

	pass
