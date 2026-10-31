# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PlantFloorStage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		operation: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		semi_finished_good: DF.Link | None
		stage_name: DF.Data
		time_in_mins: DF.Float
		workstation: DF.Link
		workstation_type: DF.Link | None
		yield_percentage: DF.Percent
	# end: auto-generated types

	pass
