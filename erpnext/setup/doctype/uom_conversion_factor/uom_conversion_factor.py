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

		conversion = frappe.qb.DocType("UOM Conversion Factor")
		duplicate = (
			frappe.qb.from_(conversion)
			.select(conversion.name)
			.where(conversion.category == self.category)
			.where(
				((conversion.from_uom == self.from_uom) & (conversion.to_uom == self.to_uom))
				| ((conversion.from_uom == self.to_uom) & (conversion.to_uom == self.from_uom))
			)
			.where(conversion.name != self.name)
			.limit(1)
			.run()
		)
		if duplicate:
			frappe.throw(_("A conversion factor already exists between these UOMs."))
