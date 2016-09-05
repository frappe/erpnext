# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import cint, cstr
from erpnext.controllers.buying_controller import BuyingController

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

		self.validate_common()
		self.validate_with_previous_doc()
		self.validate_uom_is_integer("uom", "qty")

	def on_submit(self):
		add_item_prices(self)
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
				["material_request", "material_request"],
				["material_request_item", "material_request_item"]
			],
			"postprocess": update_item
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
			"add_if_empty": True
		},
	}, target_doc, set_missing_values)

	return doclist
	
def add_item_prices(self):
	"""This function adds all the items to item prices (unless the same item has been entered multiple times)"""
	
	def add_item_price(item_doc, price_list, currency):
		# Check to see if there is an item price for the price list
		ip_list = frappe.get_all("Item Price", fields=["name"],filters={"item_code": item_doc.item_code, "price_list": price_list}) 
		
		if len(ip_list) > 0:
			for ip in ip_list: 
				frappe.msgprint(_("Updating Item Price for {0}".format(item_doc.item_code))) 
				ip_doc = frappe.get_doc("Item Price", ip.name)
				ip_doc.price_list_rate = item_doc.rate
				ip_doc.currency = currency
				ip_doc.save()
		else:
			ip_doc = frappe.get_doc({
				"doctype": "Item Price",
				"price_list": price_list,
				"buying": 1,
				"item_code": item_doc.item_code,
				"price_list_rate": item_doc.rate,
				"currency": currency,
				"item_name": item_doc.name,
				"item_description": item_doc.description
			})
			ip_doc.insert()
			frappe.msgprint(_("Creating Item Price for {0}".format(item_doc.item_code))) 
	
	items = []
	
	
	if cint(frappe.db.get_single_value("Buying Settings", "add_item_prices_from_quotations") or 0):
		# Loop through all of the items in the price list to make sure there are no duplicates
		for item_doc in self.items:
			items.append(cstr(item_doc.item_code))
		
		if items and len(items) == len(set(items)):
			for item_doc in self.items:
				add_item_price(item_doc, self.buying_price_list, self.currency)
		else:
			frappe.msgprint("Cannot create Item Prices for multiple items. Item Prices not created.")

		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		