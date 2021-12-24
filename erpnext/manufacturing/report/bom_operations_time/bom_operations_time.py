# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	data = get_data(filters)
	columns = get_columns(filters)
	return columns, data

def get_data(filters):
	data = []

	bom_data = []
	for d in frappe.db.sql("""
		SELECT
			bom.name, bom.item, bom.item_name, bom.uom,
			bomps.operation, bomps.workstation, bomps.time_in_mins
		FROM `tabBOM` bom, `tabBOM Operation` bomps
		WHERE
			bom.docstatus = 1 and bom.is_active = 1 and bom.name = bomps.parent
		""", as_dict=1):
		row = get_args()
		if d.name not in bom_data:
			bom_data.append(d.name)
			row.update(d)
		else:
			row.update({
				"operation": d.operation,
				"workstation": d.workstation,
				"time_in_mins": d.time_in_mins
			})

		data.append(row)

	used_as_subassembly_items = get_bom_count(bom_data)

	for d in data:
		d.used_as_subassembly_items = used_as_subassembly_items.get(d.name, 0)

	return data

def get_bom_count(bom_data):
	data = frappe.get_all("BOM Item",
		fields=["count(name) as count", "bom_no"],
		filters= {"bom_no": ("in", bom_data)}, group_by = "bom_no")

	bom_count = {}
	for d in data:
		bom_count.setdefault(d.bom_no, d.count)

	return bom_count

def get_args():
	return frappe._dict({
		"name": "",
		"item": "",
		"item_name": "",
		"uom": ""
	})

def get_columns(filters):
	return [{
		"label": _("BOM ID"),
		"options": "BOM",
		"fieldname": "name",
		"fieldtype": "Link",
		"width": 140
	}, {
		"label": _("BOM Item Code"),
		"options": "Item",
		"fieldname": "item",
		"fieldtype": "Link",
		"width": 140
	}, {
		"label": _("Item Name"),
		"fieldname": "item_name",
		"fieldtype": "Data",
		"width": 110
	}, {
		"label": _("UOM"),
		"options": "UOM",
		"fieldname": "uom",
		"fieldtype": "Link",
		"width": 140
	}, {
		"label": _("Operation"),
		"options": "Operation",
		"fieldname": "operation",
		"fieldtype": "Link",
		"width": 120
	}, {
		"label": _("Workstation"),
		"options": "Workstation",
		"fieldname": "workstation",
		"fieldtype": "Link",
		"width": 110
	}, {
		"label": _("Time (In Mins)"),
		"fieldname": "time_in_mins",
		"fieldtype": "Int",
		"width": 140
	}, {
		"label": _("Sub-assembly BOM Count"),
		"fieldname": "used_as_subassembly_items",
		"fieldtype": "Int",
		"width": 180
	}]
