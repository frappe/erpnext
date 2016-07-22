# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	
	qty_list = get_quantity_list(filters.item)
	
	data = get_quote_list(filters.item, qty_list)
	
	columns = get_columns(qty_list)
	
	return columns, data

	
def get_quote_list(item, qty_list):
	
	out = []
	
	if item:
		price_data = []
		suppliers = []
		# Get the list of suppliers
		for root in frappe.db.sql("""select parent, qty, rate from `tabSupplier Quotation Item` where item_code=%s and docstatus < 2""", item, as_dict=1):
			for splr in frappe.db.sql("""SELECT supplier from `tabSupplier Quotation` where name =%s and docstatus < 2""", root.parent, as_dict=1):
				ip = frappe._dict({
				"supplier": splr.supplier,
				"qty": root.qty,
				"parent": root.parent,
				"rate": root.rate})
				price_data.append(ip)
				suppliers.append(splr.supplier)
			
		#Add a row for each supplier
		for root in set(suppliers):
			row = frappe._dict({
				"supplier_name": root
			})
			for col in qty_list:
				# Get the quantity for this row
				for item_price in price_data:
					if str(item_price.qty) == col.key and item_price.supplier == root:
						row[col.key] = item_price.rate
						row[col.key + "QUOTE"] = item_price.parent
						break
					else:
						row[col.key] = ""
						row[col.key + "QUOTE"] = ""
			out.append(row)
			

	
	return out
	
def get_quantity_list(item):
	
	out = []
	
			
	if item:
		qty_list = frappe.db.sql("""select distinct qty from `tabSupplier Quotation Item` where ifnull(item_code,'')=%s and docstatus < 2""", item, as_dict=1)
		qty_list.sort(reverse=False)
		for qt in qty_list:
			col = frappe._dict({
				"key": str(qt.qty),
				"label": "Qty: " + str(int(qt.qty))
			})
			out.append(col)

	return out
	
def get_columns(qty_list):
	columns = [{
		"fieldname": "supplier_name",
		"label": "Supplier",
		"fieldtype": "Link",
		"options": "Supplier",
		"width": 200
	}]

	for qty in qty_list:
		columns.append({
			"fieldname": qty.key,
			"label": qty.label,
			"fieldtype": "Currency",
			"options": "currency",
			"width": 80
		})
		columns.append({
			"fieldname": qty.key + "QUOTE",
			"label": "Quotation",
			"fieldtype": "Link",
			"options": "Supplier Quotation",
			"width": 90
		})


	return columns