# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document


class StockEntryType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		add_to_transit: DF.Check
		is_standard: DF.Check
		purpose: DF.Literal[
			"",
			"Material Issue",
			"Material Receipt",
			"Material Transfer",
			"Material Transfer for Manufacture",
			"Material Consumption for Manufacture",
			"Manufacture",
			"Repack",
			"Send to Subcontractor",
			"Disassemble",
		]
	# end: auto-generated types

	def validate(self):
		self.validate_standard_type()
		self.validate_add_to_transit()
		if self.add_to_transit and self.purpose != "Material Transfer":
			self.add_to_transit = 0

	def validate_add_to_transit(self):
		if self.is_standard and self.add_to_transit:
			frappe.throw(
				_(
					"Add to Transit cannot be enabled on the standard Stock Entry Type {0}. Create a separate Stock Entry Type for transit transfers."
				).format(frappe.bold(self.name))
			)

	def validate_standard_type(self):
		if self.is_standard and self.name not in [
			"Material Issue",
			"Material Receipt",
			"Material Transfer",
			"Material Transfer for Manufacture",
			"Material Consumption for Manufacture",
			"Manufacture",
			"Repack",
			"Send to Subcontractor",
			"Disassemble",
		]:
			frappe.throw(f"Stock Entry Type {self.name} cannot be set as standard")
