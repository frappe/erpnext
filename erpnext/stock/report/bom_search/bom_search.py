# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from frappe import _


def execute(filters=None):
	data = []
	parents = {
		"Product Bundle Item": "Product Bundle",
		"BOM Explosion Item": "BOM",
		"BOM Item": "BOM",
	}

	doctypes = ["Product Bundle Item", "BOM Item"]
	if filters.search_sub_assemblies:
		doctypes.append("BOM Explosion Item")

	all_boms = {}
	for doctype in doctypes:
		for d in get_items(doctype):
			all_boms.setdefault((d.parent, parents[doctype]), set()).add(d.item_code)

	for parent, items in all_boms.items():
		valid = True
		for key, item in filters.items():
			if key != "search_sub_assemblies":
				if item and item not in items:
					valid = False

		if valid:
			data.append(parent)

	return [
		{
			"fieldname": "parent",
			"label": _("BOM"),
			"width": 200,
			"fieldtype": "Dynamic Link",
			"options": "doctype",
		},
		{"fieldname": "doctype", "label": _("Type"), "width": 200, "fieldtype": "Select"},
	], data


def get_items(doctype):
	item = frappe.qb.DocType(doctype)
	query = frappe.qb.from_(item).select(item.parent, item.item_code)

	if doctype != "Product Bundle Item":
		bom = frappe.qb.DocType("BOM")
		submitted_boms = frappe.qb.from_(bom).select(bom.name).where(bom.docstatus == 1)
		query = query.where(item.parent.isin(submitted_boms))

	return query.run(as_dict=True)
