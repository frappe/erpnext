# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("buying", "doctype", "supplier_quotation_item")

	for doctype in ['Purchase Order','Supplier Quotation']:
		frappe.db.sql("""
			Update
				`tab{doctype} Item`, `tabMaterial Request Item`
			set
				`tab{doctype} Item`.sales_order = `tabMaterial Request Item`.sales_order
			where
				`tab{doctype} Item`.material_request= `tabMaterial Request Item`.parent
				and `tab{doctype} Item`.material_request_item = `tabMaterial Request Item`.name
				and `tabMaterial Request Item`.sales_order is not null""".format(doctype=doctype))