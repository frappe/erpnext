# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	# reload schema
	for doctype in ("Work Order", "Work Order Item", "Work Order Operation", 
		"BOM Item", "BOM Explosion Item", "BOM"):
			frappe.reload_doctype(doctype)

	frappe.reload_doc("stock", "doctype", "item")
	frappe.reload_doc("stock", "doctype", "item_default")

	# fetch all draft and submitted work orders
	fields = ["name"]
	if "source_warehouse" in frappe.db.get_table_columns("Work Order"):
		fields.append("source_warehouse")
		
	wo_orders = frappe.get_all("Work Order", filters={"docstatus": ["!=", 2]}, fields=fields)
	
	count = 0
	for p in wo_orders:
		wo_order = frappe.get_doc("Work Order", p.name)
		count += 1

		# set required items table
		wo_order.set_required_items()
		
		for item in wo_order.get("required_items"):
			# set source warehouse based on parent
			if not item.source_warehouse and "source_warehouse" in fields:
				item.source_warehouse = wo_order.get("source_warehouse")
			item.db_update()
		
		if wo_order.docstatus == 1:
			# update transferred qty based on Stock Entry, it also updates db
			wo_order.update_transaferred_qty_for_required_items()
			
			# Set status where it was 'Unstopped', as it is deprecated
			if wo_order.status == "Unstopped":
				status = wo_order.get_status()
				wo_order.db_set("status", status)
			elif wo_order.status == "Stopped":
				wo_order.update_reserved_qty_for_production()
		
		if count % 200 == 0:
			frappe.db.commit()