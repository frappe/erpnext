# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	frappe.reload_doc('stock', 'doctype', 'material_request_item')
	rename_field("Material Request Item", "sales_order_no", "sales_order")
	
	frappe.reload_doc('support', 'doctype', 'maintenance_schedule_item')
	rename_field("Maintenance Schedule Item", "prevdoc_docname", "sales_order")
	