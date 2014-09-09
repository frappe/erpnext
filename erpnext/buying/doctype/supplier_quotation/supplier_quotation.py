# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.mapper import get_mapped_doc

from erpnext.controllers.buying_controller import BuyingController

form_grid_templates = {
	"quotation_items": "templates/form_grid/item_grid.html"
}

class SupplierQuotation(BuyingController):
	tname = "Supplier Quotation Item"
	fname = "quotation_items"

	def validate(self):
		super(SupplierQuotation, self).validate()

		if not self.status:
			self.status = "Draft"

		from erpnext.utilities import validate_status
		validate_status(self.status, ["Draft", "Submitted", "Stopped",
			"Cancelled"])

		self.validate_common()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("uom", "qty")

	def on_submit(self):
		frappe.db.set(self, "status", "Submitted")

	def on_cancel(self):
		frappe.db.set(self, "status", "Cancelled")

	def on_trash(self):
		pass

	def validate_with_previous_doc(self):
		super(SupplierQuotation, self).validate_with_previous_doc(self.tname, {
			"Material Request": {
				"ref_dn_field": "prevdoc_docname",
				"compare_fields": [["company", "="]],
			},
			"Material Request Item": {
				"ref_dn_field": "prevdoc_detail_docname",
				"compare_fields": [["item_code", "="], ["uom", "="]],
				"is_child_table": True
			}
		})


	def validate_common(self):
		pc = frappe.get_doc('Purchase Common')
		pc.validate_for_items(self)

@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("get_schedule_dates")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		target.conversion_factor = 1

	doclist = get_mapped_doc("Supplier Quotation", source_name,		{
		"Supplier Quotation": {
			"doctype": "Purchase Order",
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		"Supplier Quotation Item": {
			"doctype": "Purchase Order Item",
			"field_map": [
				["name", "supplier_quotation_item"],
				["parent", "supplier_quotation"],
				["uom", "stock_uom"],
				["uom", "uom"],
				["prevdoc_detail_docname", "prevdoc_detail_docname"],
				["prevdoc_doctype", "prevdoc_doctype"],
				["prevdoc_docname", "prevdoc_docname"]
			],
			"postprocess": update_item
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
			"add_if_empty": True
		},
	}, target_doc, set_missing_values)

	return doclist
