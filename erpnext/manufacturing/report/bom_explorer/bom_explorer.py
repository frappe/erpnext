# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from collections import defaultdict

import frappe
from frappe import _


def execute(filters=None):
	data = []
	columns = get_columns()
	get_data(filters, data)
	return columns, data


def get_data(filters, data):
	children_map = fetch_exploded_bom_items(filters.bom)
	build_exploded_rows(filters.bom, children_map, data)


def fetch_exploded_bom_items(root_bom):
	"""Every BOM Item in the exploded tree of `root_bom`, grouped by its parent BOM, in one
	recursive CTE -- replaces a query-per-node walk with a single query. UNION keeps it cycle-safe
	and fetches each sub-BOM's items only once even when it is reused across the tree."""
	bom_item = frappe.qb.DocType("BOM Item")
	tree = frappe.qb.Table("exploded_bom")
	fields = [
		bom_item.parent,
		bom_item.qty,
		bom_item.bom_no,
		bom_item.item_code,
		bom_item.item_name,
		bom_item.description,
		bom_item.uom,
		bom_item.idx,
		bom_item.is_phantom_item,
	]
	seed = frappe.qb.from_(bom_item).select(*fields).where(bom_item.parent == root_bom)
	recursion = (
		frappe.qb.from_(bom_item)
		.join(tree)
		.on(bom_item.parent == tree.bom_no)
		.select(*fields)
		.where(tree.bom_no != "")
	)
	rows = (
		frappe.qb.with_(seed + recursion, "exploded_bom", recursive=True).from_(tree).select(tree.star)
	).run(as_dict=True)

	children_map = defaultdict(list)
	for row in rows:
		children_map[row.parent].append(row)
	return children_map


def build_exploded_rows(bom, children_map, data, indent=0, qty=1):
	for item in sorted(children_map.get(bom, []), key=lambda row: row.idx):
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
				"is_phantom_item": item.is_phantom_item,
			}
		)
		if item.bom_no:
			build_exploded_rows(item.bom_no, children_map, data, indent + 1, item.qty)


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
		{"label": _("Is Phantom Item"), "fieldtype": "Check", "fieldname": "is_phantom_item"},
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
