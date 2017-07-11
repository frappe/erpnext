# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	# reload schema
	for doctype in ("Production Order", "Production Order Item", "Production Order Operation", 
		"BOM Item", "BOM Explosion Item", "BOM"):
			frappe.reload_doctype(doctype)

	# fetch all draft and submitted production orders
	fields = ["name"]
	if "source_warehouse" in frappe.db.get_table_columns("Production Order"):
		fields.append("source_warehouse")
		
	pro_orders = frappe.get_all("Production Order", filters={"docstatus": ["!=", 2]}, fields=fields)
	
	count = 0
	for p in pro_orders:
		pro_order = frappe.get_doc("Production Order", p.name)
		count += 1

		# set required items table
		pro_order.set_required_items()
		
		for item in pro_order.get("required_items"):
			# set source warehouse based on parent
			if not item.source_warehouse and "source_warehouse" in fields:
				item.source_warehouse = pro_order.get("source_warehouse")
			item.db_update()
		
		if pro_order.docstatus == 1:
			# update transferred qty based on Stock Entry, it also updates db
			pro_order.update_transaferred_qty_for_required_items()
			
			# Set status where it was 'Unstopped', as it is deprecated
			if pro_order.status == "Unstopped":
				status = pro_order.get_status()
				pro_order.db_set("status", status)
			elif pro_order.status == "Stopped":
				pro_order.update_reserved_qty_for_production()
		
		if count % 200 == 0:
			frappe.db.commit()