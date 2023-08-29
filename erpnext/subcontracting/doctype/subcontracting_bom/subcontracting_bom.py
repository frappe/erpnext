# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SubcontractingBOM(Document):
	def validate(self):
		self.validate_finished_good()
		self.validate_service_item()
		self.validate_is_active()

	def before_save(self):
		self.set_conversion_factor()

	def validate_finished_good(self):
		disabled, is_stock_item, default_bom, is_sub_contracted_item = frappe.db.get_value(
			"Item",
			self.finished_good,
			["disabled", "is_stock_item", "default_bom", "is_sub_contracted_item"],
		)

		if disabled:
			frappe.throw(_("Finished Good {0} is disabled.").format(frappe.bold(self.finished_good)))
		if not is_stock_item:
			frappe.throw(
				_("Finished Good {0} must be a stock item.").format(frappe.bold(self.finished_good))
			)
		if not default_bom:
			frappe.throw(
				_("Finished Good {0} does not have a default BOM.").format(frappe.bold(self.finished_good))
			)
		if not is_sub_contracted_item:
			frappe.throw(
				_("Finished Good {0} must be a sub-contracted item.").format(frappe.bold(self.finished_good))
			)

	def validate_service_item(self):
		disabled, is_stock_item = frappe.db.get_value(
			"Item", self.service_item, ["disabled", "is_stock_item"]
		)

		if disabled:
			frappe.throw(_("Service Item {0} is disabled.").format(frappe.bold(self.service_item)))
		if is_stock_item:
			frappe.throw(
				_("Service Item {0} must be a non-stock item.").format(frappe.bold(self.service_item))
			)

	def validate_is_active(self):
		if self.is_active:
			if sb := frappe.db.exists(
				"Subcontracting BOM",
				{"finished_good": self.finished_good, "is_active": 1, "name": ["!=", self.name]},
			):
				frappe.throw(
					_("There is already an active Subcontracting BOM {0} for the Finished Good {1}.").format(
						frappe.bold(sb), frappe.bold(self.finished_good)
					)
				)

	def set_conversion_factor(self):
		self.conversion_factor = flt(self.service_item_qty) / flt(self.finished_good_qty)
