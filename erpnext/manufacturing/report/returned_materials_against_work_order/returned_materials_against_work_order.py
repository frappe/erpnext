# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	data = get_data(filters)
	columns = get_columns(filters)
	return columns, data

def get_data(report_filters):
	fields = get_fields()
	filters = get_filter_condition(report_filters)

	returned_items = {}
	for d in frappe.get_all("Stock Entry", filters = filters, fields=fields, debug=1):
		returned_items.setdefault((d.name, d.production_item), []).append(d)

	data = []
	for key, ste_data in returned_items.items():
		for index, row in enumerate(ste_data):
			if index != 0:
				for field in ["name", "production_item"]:
					row[field] = ""
			else:
				row["production_item"] = frappe.get_cached_value("Work Order",
					row.work_order, "production_item")

			data.append(row)

	return data

def get_fields():
	return ["`tabStock Entry Detail`.`parent`", "`tabStock Entry Detail`.`item_code` as raw_material_item_code",
		"`tabStock Entry Detail`.`item_name` as raw_material_name", "`tabStock Entry Detail`.`qty`",
		"`tabStock Entry Detail`.`s_warehouse`", "`tabStock Entry Detail`.`t_warehouse`",
		"`tabStock Entry`.`work_order`", "`tabStock Entry`.`is_return`", "`tabStock Entry`.`name`"]

def get_filter_condition(report_filters):
	filters = {
		"docstatus": 1, "is_return": 1,
		"posting_date": ("between", [report_filters.from_date, report_filters.to_date])
	}

	for field in ["company", "work_order"]:
		value = report_filters.get(field)
		if value:
			key = "`{0}`".format(field)
			filters.update({key: value})

	return filters

def get_columns(filters):
	return [
		{
			"label": _("Id"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Stock Entry",
			"width": 120
		},
		{
			"label": _("Production Item"),
			"fieldname": "production_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 130
		},
		{
			"label": _("Raw Material Item"),
			"fieldname": "raw_material_item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 130
		},
		{
			"label": _("Item Name"),
			"fieldname": "raw_material_name",
			"width": 130
		},
		{
			"label": _("From Warehouse"),
			"fieldname": "s_warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150
		},
		{
			"label": _("To Warehouse"),
			"fieldname": "t_warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150
		},
		{
			"label": _("Returned Qty"),
			"fieldname": "qty",
			"fieldtype": "Float",
			"width": 120
		}
	]