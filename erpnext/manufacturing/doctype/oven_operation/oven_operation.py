# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class OvenOperation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		bottom_edge_centre: DF.Float
		bottom_left_vertex: DF.Float
		bottom_right_vertex: DF.Float
		date: DF.Datetime
		in_time: DF.Time
		left_edge_centre: DF.Float
		lower_shelf_temp: DF.Float
		out_time: DF.Time | None
		oven: DF.Link
		oven_rack: DF.Link
		remarks: DF.Text | None
		right_edge_centre: DF.Float
		shift: DF.Link
		slab: DF.Link
		slab_bottom_temp: DF.Float
		slab_color: DF.Link
		slab_top_temp: DF.Float
		top_edge_center: DF.Float
		top_left_vertex: DF.Float
		top_right_vertex: DF.Float
		total_time_in_minutes: DF.Float
		upper_shelf_temp: DF.Float
	# end: auto-generated types
	pass
