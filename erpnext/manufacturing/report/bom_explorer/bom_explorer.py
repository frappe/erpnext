# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	data = []
	columns = get_columns()
	get_data(filters, data)
	return columns, data


def get_data(filters, data):
	get_exploded_items(filters.bom, data)


def get_exploded_items(bom, data, indent=0, qty=1):
	exploded_items = frappe.get_all(
		"BOM Item",
		filters={"parent": bom},
<<<<<<< HEAD
		fields=[
			"qty",
			"bom_no",
			"qty",
			"item_code",
			"item_name",
			"description",
			"uom",
			"idx",
			"is_phantom_item",
		],
=======
		fields=["qty", "bom_no", "qty", "item_code", "item_name", "description", "uom", "idx"],
>>>>>>> 7c4cf3e834 (Favicon.svg)
		order_by="idx ASC",
	)

	for item in exploded_items:
<<<<<<< HEAD
=======
		print(item.bom_no, indent)
>>>>>>> 7c4cf3e834 (Favicon.svg)
		item["indent"] = indent
		data.append(
			{
				"item_code": item.item_code,
				"item_name": item.item_name,
				"indent": indent,
				"bom_level": indent,
				"bom": item.bom_no,
				"qty": item.qty * qty,
				"uom": item.uom,
				"description": item.description,
<<<<<<< HEAD
				"is_phantom_item": item.is_phantom_item,
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
			}
		)
		if item.bom_no:
			get_exploded_items(item.bom_no, data, indent=indent + 1, qty=item.qty)


def get_columns():
	return [
		{
			"label": _("Item Code"),
			"fieldtype": "Link",
			"fieldname": "item_code",
			"width": 300,
			"options": "Item",
		},
		{"label": _("Item Name"), "fieldtype": "data", "fieldname": "item_name", "width": 100},
		{"label": _("BOM"), "fieldtype": "Link", "fieldname": "bom", "width": 150, "options": "BOM"},
<<<<<<< HEAD
		{"label": _("Is Phantom Item"), "fieldtype": "Check", "fieldname": "is_phantom_item"},
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
		{"label": _("Qty"), "fieldtype": "data", "fieldname": "qty", "width": 100},
		{"label": _("UOM"), "fieldtype": "data", "fieldname": "uom", "width": 100},
		{"label": _("BOM Level"), "fieldtype": "Int", "fieldname": "bom_level", "width": 100},
		{
			"label": _("Standard Description"),
			"fieldtype": "data",
			"fieldname": "description",
			"width": 150,
		},
	]
