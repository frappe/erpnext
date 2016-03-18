# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	
	doc_list = ["Production Order", "BOM", "Purchase Invoice Item", "Sales Invoice", 
		"Purchase Order Item", "Stock Entry", "Delivery Note", "Sales Order", 
		"Purchase Receipt Item", "Supplier Quotation Item"]
	
	for doctype in doc_list:
		frappe.reload_doctype(doctype)
		rename_field(doctype, "project_name", "project")
	