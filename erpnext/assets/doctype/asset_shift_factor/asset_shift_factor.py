# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AssetShiftFactor(Document):
	def validate(self):
		self.validate_default()

	def validate_default(self):
		if self.default:
			existing_default_shift_factor = frappe.db.get_value(
				"Asset Shift Factor", {"default": 1}, "name"
			)

			if existing_default_shift_factor:
				frappe.throw(
					_("Asset Shift Factor {0} is set as default currently. Please change it first.").format(
						frappe.bold(existing_default_shift_factor)
					)
				)
