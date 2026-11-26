# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class WorkstationTypeShape(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		depth: DF.Float
		finish: DF.Literal[
			"",
			"Steel",
			"Dark",
			"Plate",
			"Product",
			"Heat",
			"Red",
			"Amber",
			"Cream",
			"Blue",
			"Green",
			"Violet",
			"Gray",
		]
		height: DF.Float
		is_small: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		radius: DF.Float
		shakes: DF.Check
		shape: DF.Literal[
			"Box", "Tank", "Open Tank", "Band", "Agitator", "Steam", "Bubbles", "Fizz", "Flow Strip"
		]
		shows_level: DF.Check
		width: DF.Float
		x: DF.Float
		y: DF.Float
		z: DF.Float
	# end: auto-generated types

	pass
