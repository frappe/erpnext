# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	data = get_data(filters)
	columns = get_columns(filters)
	return columns, data


def get_data(filters):
	bom_wise_data = {}
	bom_data, report_data = [], []

	bom_operation_data = get_filtered_data(filters)

	for d in bom_operation_data:
		row = get_args()
		if d.name not in bom_data:
			bom_wise_data[d.name] = []
			bom_data.append(d.name)
			row.update(d)
		else:
			row.update(
				{"operation": d.operation, "workstation": d.workstation, "time_in_mins": d.time_in_mins}
			)

		# maintain BOM wise data for grouping such as:
		# {"BOM A": [{Row1}, {Row2}], "BOM B": ...}
		bom_wise_data[d.name].append(row)

	used_as_subassembly_items = get_bom_count(bom_data)

	for d in bom_wise_data:
		for row in bom_wise_data[d]:
			row.used_as_subassembly_items = used_as_subassembly_items.get(row.name, 0)
			report_data.append(row)

	return report_data


def get_filtered_data(filters):
	bom = frappe.qb.DocType("BOM")
	bom_ops = frappe.qb.DocType("BOM Operation")

	bom_ops_query = (
		frappe.qb.from_(bom)
		.join(bom_ops)
		.on(bom.name == bom_ops.parent)
		.select(
			bom.name,
			bom.item,
			bom.item_name,
			bom.uom,
			bom_ops.operation,
			bom_ops.workstation,
			bom_ops.time_in_mins,
		)
		.where((bom.docstatus == 1) & (bom.is_active == 1))
	)

	if filters.get("item_code"):
		bom_ops_query = bom_ops_query.where(bom.item == filters.get("item_code"))

	if filters.get("bom_id"):
		bom_ops_query = bom_ops_query.where(bom.name.isin(filters.get("bom_id")))

	if filters.get("workstation"):
		bom_ops_query = bom_ops_query.where(bom_ops.workstation == filters.get("workstation"))

	bom_operation_data = bom_ops_query.run(as_dict=True)

	return bom_operation_data


def get_bom_count(bom_data):
	data = frappe.get_all(
		"BOM Item",
		fields=["count(name) as count", "bom_no"],
		filters={"bom_no": ("in", bom_data)},
		group_by="bom_no",
	)

	bom_count = {}
	for d in data:
		bom_count.setdefault(d.bom_no, d.count)

	return bom_count


def get_args():
	return frappe._dict({"name": "", "item": "", "item_name": "", "uom": ""})


def get_columns(filters):
	return [
		{"label": _("BOM ID"), "options": "BOM", "fieldname": "name", "fieldtype": "Link", "width": 220},
		{
			"label": _("Item Code"),
			"options": "Item",
			"fieldname": "item",
			"fieldtype": "Link",
			"width": 150,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 110},
		{"label": _("UOM"), "options": "UOM", "fieldname": "uom", "fieldtype": "Link", "width": 100},
		{
			"label": _("Operation"),
			"options": "Operation",
			"fieldname": "operation",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Workstation"),
			"options": "Workstation",
			"fieldname": "workstation",
			"fieldtype": "Link",
			"width": 110,
		},
		{"label": _("Time (In Mins)"), "fieldname": "time_in_mins", "fieldtype": "Float", "width": 120},
		{
			"label": _("Sub-assembly BOM Count"),
			"fieldname": "used_as_subassembly_items",
			"fieldtype": "Int",
			"width": 200,
		},
	]
