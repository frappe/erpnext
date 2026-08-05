# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Bin(Document):
	def validate(self):
		self.validate_rack_warehouse()

	def validate_rack_warehouse(self):
		if not self.rack or not self.warehouse:
			return

		rack_warehouse = frappe.get_cached_value("Rack", self.rack, "warehouse")
		if rack_warehouse and rack_warehouse != self.warehouse:
			frappe.throw(
				_("Rack {0} belongs to warehouse {1}, not {2}.").format(
					self.rack, rack_warehouse, self.warehouse
				)
			)
