# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Oven(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		code: DF.Data
		line: DF.Link
		oven_name: DF.Data
		slab_bottom_temp: DF.Float
		slab_top_temp: DF.Float
	# end: auto-generated types
	pass
