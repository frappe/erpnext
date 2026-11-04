# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PlantFloor(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		floor_name: DF.Data | None
		warehouse: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_warehouse()

	def validate_warehouse(self):
		if not self.warehouse:
			return

		warehouse = frappe.get_cached_value(
			"Warehouse", self.warehouse, ["is_group", "company"], as_dict=True
		)
		if warehouse.is_group:
			frappe.throw(_("Warehouse {0} is a group warehouse").format(frappe.bold(self.warehouse)))

		if self.company and warehouse.company != self.company:
			frappe.throw(
				_("Warehouse {0} does not belong to company {1}").format(
					frappe.bold(self.warehouse), frappe.bold(self.company)
				)
			)
