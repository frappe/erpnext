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
		for d in frappe.get_all(doctype, fields=["parent", "item_code"], filters=get_parent_filters(doctype)):
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
		{"fieldname": "doctype", "label": _("Type"), "width": 200, "fieldtype": "Link", "options": "DocType"},
	], data


def get_parent_filters(doctype):
	if doctype == "Product Bundle Item":
		return []

	bom = frappe.qb.DocType("BOM")
	submitted_boms = frappe.qb.from_(bom).select(bom.name).where(bom.docstatus == 1)
	return [frappe.qb.DocType(doctype).parent.isin(submitted_boms)]
