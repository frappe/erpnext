# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AddRawMaterials(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		job_card: DF.Link | None
		qty: DF.Float
		raw_material: DF.Link | None
	# end: auto-generated types

	def autoname(self):
		if not self.raw_material or not self.qty:
			frappe.throw("Raw Material and Qty are required to generate name")
		raw_material = self.raw_material.strip().replace(" ", "_")
		qty = str(self.qty)
		base_name = f"{raw_material}-{qty}"
		self.name = frappe.model.naming.make_autoname(base_name + "-.#####")

