# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class UOMConversionFactor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		category: DF.Link
		from_uom: DF.Link
		to_uom: DF.Link
		value: DF.Float
	# end: auto-generated types

	def validate(self):
		if flt(self.value) <= 0:
			frappe.throw(_("Value must be greater than zero."))

		if self.from_uom == self.to_uom:
			frappe.throw(_("From UOM and To UOM must be different."))

		filters = {
			"category": self.category,
			"from_uom": ["in", (self.from_uom, self.to_uom)],
			"to_uom": ["in", (self.from_uom, self.to_uom)],
		}
		if self.name:
			filters["name"] = ["!=", self.name]

		if frappe.db.exists("UOM Conversion Factor", filters):
			frappe.throw(_("A conversion factor already exists between these UOMs."))
