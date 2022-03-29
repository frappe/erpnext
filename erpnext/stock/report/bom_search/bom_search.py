# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt


import frappe
from six import iteritems


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
		for d in frappe.get_all(doctype, fields=["parent", "item_code"]):
			all_boms.setdefault(d.parent, []).append(d.item_code)

		for parent, items in iteritems(all_boms):
			valid = True
			for key, item in iteritems(filters):
				if key != "search_sub_assemblies":
					if item and item not in items:
						valid = False

			if valid:
				data.append((parent, parents[doctype]))

	return [
		{
			"fieldname": "parent",
			"label": "BOM",
			"width": 200,
			"fieldtype": "Dynamic Link",
			"options": "doctype",
		},
		{"fieldname": "doctype", "label": "Type", "width": 200, "fieldtype": "Data"},
	], data
