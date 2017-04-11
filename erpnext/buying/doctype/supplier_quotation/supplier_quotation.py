# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc

from erpnext.controllers.buying_controller import BuyingController
from erpnext.buying.utils import validate_for_items

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class SupplierQuotation(BuyingController):
	def validate(self):
		super(SupplierQuotation, self).validate()

		if not self.status:
			self.status = "Draft"

		from erpnext.controllers.status_updater import validate_status
		validate_status(self.status, ["Draft", "Submitted", "Stopped",
			"Cancelled"])

		validate_for_items(self)
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("uom", "qty")

	def on_submit(self):
		frappe.db.set(self, "status", "Submitted")

	def on_cancel(self):
		frappe.db.set(self, "status", "Cancelled")

	def on_trash(self):
		pass

	def validate_with_previous_doc(self):
		super(SupplierQuotation, self).validate_with_previous_doc({
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

def get_list_context(context=None):
	from erpnext.controllers.website_list_for_contact import get_list_context
	list_context = get_list_context(context)
	list_context.update({
		'show_sidebar': True,
		'show_search': True,
		'no_breadcrumbs': True,
		'title': _('Supplier Quotation'),
	})

	return list_context

@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("get_schedule_dates")
		target.run_method("calculate_taxes_and_totals")

	def update_item(obj, target, source_parent):
		target.stock_qty = flt(obj.qty) * flt(obj.conversion_factor)

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
				["material_request", "material_request"],
				["material_request_item", "material_request_item"]
			],
			"postprocess": update_item
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
		},
	}, target_doc, set_missing_values)

	return doclist

@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc("Supplier Quotation", source_name, {
		"Supplier Quotation": {
			"doctype": "Quotation",
			"field_map": {
				"name": "supplier_quotation",
			}
		},
		"Supplier Quotation Item": {
			"doctype": "Quotation Item",
			"condition": lambda doc: frappe.db.get_value("Item", doc.item_code, "is_sales_item")==1,
			"add_if_empty": True
		}
	}, target_doc)

	return doclist

