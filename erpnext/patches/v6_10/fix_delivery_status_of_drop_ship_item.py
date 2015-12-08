from __future__ import unicode_literals
import frappe

def execute():
	sales_orders_to_update = []

	for item in frappe.get_all("Purchase Order Item", filters={"delivered_by_supplier": 1}, 
		fields=["prevdoc_doctype", "prevdoc_docname"]):
		
		if item.prevdoc_doctype == "Sales Order":
			if item.prevdoc_docname not in sales_orders_to_update:
				sales_orders_to_update.append(item.prevdoc_docname)

	for so_name in sales_orders_to_update:
		so = frappe.get_doc("Sales Order", so_name)
		so.update_delivery_status()
		so.set_status(update=True, update_modified=False)