# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if filters.from_date >= filters.to_date:
		frappe.msgprint(_("To Date must be greater than From Date"))

	data = []
	columns = get_columns()
	get_data(data , filters)
	return columns, data

def get_columns():
	return [
		{
			"label": _("Purchase Order"),
			"fieldtype": "Link",
			"fieldname": "purchase_order",
			"options": "Purchase Order",
			"width": 150
		},
		{
			"label": _("Date"),
			"fieldtype": "Date",
			"fieldname": "date",
			"hidden": 1,
			"width": 150
		},
		{
			"label": _("Supplier"),
			"fieldtype": "Link",
			"fieldname": "supplier",
			"options": "Supplier",
			"width": 150
		},
		{
			"label": _("Item Code"),
			"fieldtype": "Data",
			"fieldname": "rm_item_code",
			"width": 100
		},
		{
			"label": _("Required Quantity"),
			"fieldtype": "Float",
			"fieldname": "r_qty",
			"width": 100
		},
		{
			"label": _("Transferred Quantity"),
			"fieldtype": "Float",
			"fieldname": "t_qty",
			"width": 100
		},
		{
			"label": _("Pending Quantity"),
			"fieldtype": "Float",
			"fieldname": "p_qty",
			"width": 100
		}
	]

def get_data(data, filters):
	po = get_po(filters)
	po_transferred_qty_map = frappe._dict(get_transferred_quantity([v.name for v in po]))

	sub_items = get_purchase_order_item_supplied([v.name for v in po])

	for order in po:
		for item in sub_items:
			if order.name == item.parent and order.name in po_transferred_qty_map and \
				item.required_qty != po_transferred_qty_map.get(order.name).get(item.rm_item_code):
				transferred_qty = po_transferred_qty_map.get(order.name).get(item.rm_item_code) \
				if po_transferred_qty_map.get(order.name).get(item.rm_item_code) else 0
				row ={
					'purchase_order': item.parent,
					'date': order.transaction_date,
					'supplier': order.supplier,
					'rm_item_code': item.rm_item_code,
					'r_qty': item.required_qty,
					't_qty':transferred_qty,
					'p_qty':item.required_qty - transferred_qty
				}

				data.append(row)

	return(data)

def get_po(filters):
	record_filters = [
			["is_subcontracted", "=", "Yes"],
			["supplier", "=", filters.supplier],
			["transaction_date", "<=", filters.to_date],
			["transaction_date", ">=", filters.from_date],
			["docstatus", "=", 1]
		]
	return frappe.get_all("Purchase Order", filters=record_filters, fields=["name", "transaction_date", "supplier"])

def get_transferred_quantity(po_name):
	stock_entries = get_stock_entry(po_name)
	stock_entries_detail = get_stock_entry_detail([v.name for v in stock_entries])
	po_transferred_qty_map = {}


	for entry in stock_entries:
		for details in stock_entries_detail:
			if details.parent == entry.name:
				details["Purchase_order"] = entry.purchase_order
				if entry.purchase_order not in po_transferred_qty_map:
					po_transferred_qty_map[entry.purchase_order] = {}
					po_transferred_qty_map[entry.purchase_order][details.item_code] = details.qty
				else:
					po_transferred_qty_map[entry.purchase_order][details.item_code] = po_transferred_qty_map[entry.purchase_order].get(details.item_code, 0) + details.qty

	return po_transferred_qty_map


def get_stock_entry(po):
	return frappe.get_all("Stock Entry", filters=[
			('purchase_order', 'IN', po),
			('stock_entry_type', '=', 'Send to Subcontractor'),
			('docstatus', '=', 1)
	], fields=["name", "purchase_order"])

def get_stock_entry_detail(se):
	return frappe.get_all("Stock Entry Detail", filters=[
			["parent", "in", se]
		],
		fields=["parent", "item_code", "qty"])

def get_purchase_order_item_supplied(po):
	return frappe.get_all("Purchase Order Item Supplied", filters=[
			('parent', 'IN', po)
	], fields=['parent', 'rm_item_code', 'required_qty'])
