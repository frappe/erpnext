# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class BOMOperation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		backflush_from_wip_warehouse: DF.Check
		base_cost_per_unit: DF.Float
		base_hour_rate: DF.Currency
		base_operating_cost: DF.Currency
		batch_size: DF.Int
		bom_no: DF.Link | None
		cost_per_unit: DF.Float
		description: DF.TextEditor | None
		fg_warehouse: DF.Link | None
		finished_good: DF.Link | None
		finished_good_qty: DF.Float
		fixed_time: DF.Check
		hour_rate: DF.Currency
		image: DF.Attach | None
		is_final_finished_good: DF.Check
		is_subcontracted: DF.Check
		operating_cost: DF.Currency
		operation: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		sequence_id: DF.Int
		set_cost_based_on_bom_qty: DF.Check
		skip_material_transfer: DF.Check
		source_warehouse: DF.Link | None
		time_in_mins: DF.Float
		wip_warehouse: DF.Link | None
		workstation: DF.Link | None
		workstation_type: DF.Link | None
	# end: auto-generated types

	pass
