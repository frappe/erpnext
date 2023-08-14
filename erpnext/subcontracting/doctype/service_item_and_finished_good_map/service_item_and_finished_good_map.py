# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ServiceItemandFinishedGoodMap(Document):
	def validate(self):
		self.validate_service_item()
		self.validate_finished_good_item()

	def validate_service_item(self):
		disabled, is_stock_item = frappe.db.get_value(
			"Item", self.service_item, ["disabled", "is_stock_item"]
		)

		if disabled:
			frappe.throw(f"Service Item {self.service_item} is disabled.")
		if is_stock_item:
			frappe.throw(f"Service Item {self.service_item} is a stock item.")

	def validate_finished_good_item(self):
		disabled, is_stock_item, default_bom, is_sub_contracted_item = frappe.db.get_value(
			"Item", self.finished_good_item, ["disabled", "is_stock_item", "default_bom", "is_sub_contracted_item"]
		)

		if disabled:
			frappe.throw(f"Finished Good Item {self.finished_good_item} is disabled.")
		if not is_stock_item:
			frappe.throw(f"Finished Good Item {self.finished_good_item} is not a stock item.")
		if not default_bom:
			frappe.throw(f"Finished Good Item {self.finished_good_item} does not have a default BOM.")
		if not is_sub_contracted_item:
			frappe.throw(f"Finished Good Item {self.finished_good_item} is not a sub-contracted item.")
