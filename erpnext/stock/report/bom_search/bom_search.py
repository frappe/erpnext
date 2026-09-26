# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from frappe import _

from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_masters_condition


def execute(filters=None):
	data = []
	parents = {
		"Product Bundle Item": "Product Bundle",
		"BOM Explosion Item": "BOM",
		"BOM Item": "BOM",
	}

	for doctype in (
		"Product Bundle Item",
		"BOM Explosion Item" if filters.search_sub_assemblies else "BOM Item",
	):
		all_boms = {}
		for d in frappe.get_all(doctype, fields=["parent", "item_code"], filters=get_parent_filters(doctype)):
			all_boms.setdefault(d.parent, []).append(d.item_code)

		for parent, items in all_boms.items():
			valid = True
			for key, item in filters.items():
				if key != "search_sub_assemblies":
					if item and item not in items:
						valid = False

			if valid:
				data.append((parent, parents[doctype]))

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
	if doctype != "Product Bundle Item":
		return []

	bundle = frappe.qb.DocType("Product Bundle")
	condition = get_allowed_masters_condition(bundle.new_item_code, "Item")
	if not condition:
		return []

	allowed_bundles = frappe.qb.from_(bundle).select(bundle.name).where(condition)
	return [frappe.qb.DocType(doctype).parent.isin(allowed_bundles)]
