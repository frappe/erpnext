# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SlabSeed(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		line: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		seed: DF.Int
		seed_month: DF.Date
	# end: auto-generated types
	pass
