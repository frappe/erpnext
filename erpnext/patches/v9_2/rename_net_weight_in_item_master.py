from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	frappe.reload_doc("stock", "doctype", "item")
	if frappe.db.has_column('Item', 'net_weight'):
		rename_field("Item", "net_weight", "weight_per_unit")
