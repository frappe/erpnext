# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""BOM explosion helpers for Production Plan material planning."""

import frappe
from frappe.query_builder.functions import Count, IfNull, Max, Min, Sum
from frappe.utils.caching import request_cache

from erpnext.manufacturing.doctype.production_plan.services.planning_queries import get_uom_conversion_factor


def get_exploded_items(item_details, company, bom_no, include_non_stock_items, planned_qty=1, doc=None):
	data = _exploded_items_query(company, bom_no, include_non_stock_items, planned_qty)
	_apply_exploded_conversion(item_details, data)
	return item_details


def _exploded_items_query(company, bom_no, include_non_stock_items, planned_qty):
	bei = frappe.qb.DocType("BOM Explosion Item")
	bom = frappe.qb.DocType("BOM")
	item = frappe.qb.DocType("Item")
	item_default = frappe.qb.DocType("Item Default")
	item_uom = frappe.qb.DocType("UOM Conversion Detail")
	rows = (
		frappe.qb.from_(bei)
		.join(bom)
		.on(bom.name == bei.parent)
		.join(item)
		.on(item.name == bei.item_code)
		.left_join(item_default)
		.on((item_default.parent == item.name) & (item_default.company == company))
		.left_join(item_uom)
		.on((item.name == item_uom.parent) & (item_uom.uom == item.purchase_uom))
		.select(*_exploded_item_columns(bei, bom, item, item_default, item_uom, planned_qty))
		.where(_exploded_item_filter(bei, bom, item, bom_no, include_non_stock_items))
		.groupby(bei.item_code, bei.stock_uom)
	).run(as_dict=True)

	_apply_representative_lines(
		rows, "BOM Explosion Item", bom_no, ("item_code", "stock_uom"), include_non_stock_items
	)
	return rows


def _apply_representative_lines(rows, doctype, bom_no, keys, include_non_stock_items=True):
	"""Fill description/source_warehouse from a single real BOM line per group.

	Both describe a line, not an item, so a BOM listing the same item more than once holds
	several values per group. Aggregating each independently can pair one line's description
	with another's warehouse, and Max() over text is a sort -- MariaDB folds case, PostgreSQL
	orders by byte value, so the two engines pick differently. Take the first line by idx.

	Only groups built from more than one line need this. Where a group has a single line, Max() of
	one value is that value, so the selected columns are already exact and no query is issued --
	which matters because this runs once per BOM in a recursive explosion.
	"""
	repeated = [row for row in rows if (row.pop("line_count", 1) or 1) > 1]
	if not repeated:
		return

	representative = _representative_lines(doctype, bom_no, tuple(keys), include_non_stock_items)

	for row in repeated:
		line = representative.get(tuple(row.get(key) for key in keys))
		if line:
			row.description = line.description
			row.source_warehouse = line.source_warehouse


@request_cache
def _representative_lines(doctype, bom_no, keys, include_non_stock_items):
	"""Cached per request: the explosion recurses and commonly revisits the same sub-BOM."""
	# only BOM Item carries is_phantom_item, and only its query ORs the phantom flag into the stock
	# filter; the explosion table has neither
	filters_phantom = doctype == "BOM Item"
	fields = ["item_code", "stock_uom", "description", "source_warehouse"]
	if filters_phantom:
		fields.append("is_phantom_item")

	lines = frappe.get_all(
		doctype,
		filters={
			"parent": bom_no,
			"parenttype": "BOM",
			"is_sub_assembly_item": 0,
			"docstatus": ("<", 2),
		},
		fields=fields,
		order_by="idx",
	)

	# mirror the caller's stock filter: a non-stock line the main query excluded must not become
	# the representative for a group that only exists because of a phantom line
	if not include_non_stock_items and filters_phantom and lines:
		stock_items = set(
			frappe.get_all(
				"Item",
				filters={"name": ("in", list({line.item_code for line in lines})), "is_stock_item": 1},
				pluck="name",
			)
		)
		lines = [line for line in lines if line.item_code in stock_items or line.is_phantom_item]

	representative = {}
	for line in lines:
		representative.setdefault(tuple(line.get(key) for key in keys), line)

	return representative


def _exploded_item_columns(bei, bom, item, item_default, item_uom, planned_qty):
	# every column here is functionally dependent on the grouped item_code -- Item, Item Default and
	# UOM Conversion Detail are joined on it and the BOM is pinned by the filter -- so Max() returns
	# their single value. The BOM-line columns come from a representative line instead; see
	# _apply_representative_lines.
	return [
		(IfNull(Sum(bei.stock_qty / IfNull(bom.quantity, 1)), 0) * planned_qty).as_("qty"),
		Max(item.item_name).as_("item_name"),
		Max(item.name).as_("item_code"),
		Max(bei.description).as_("description"),
		Max(bei.source_warehouse).as_("source_warehouse"),
		Count(bei.name).distinct().as_("line_count"),
		bei.stock_uom,
		Max(item.min_order_qty).as_("min_order_qty"),
		Max(item.default_material_request_type).as_("default_material_request_type"),
		Max(item.min_order_qty).as_("min_order_qty"),
		Max(item_default.default_warehouse).as_("default_warehouse"),
		Max(item.purchase_uom).as_("purchase_uom"),
		Max(item_uom.conversion_factor).as_("conversion_factor"),
		Max(item.safety_stock).as_("safety_stock"),
		Max(bom.item).as_("main_bom_item"),
		Max(bom.name).as_("main_bom"),
	]


def _exploded_item_filter(bei, bom, item, bom_no, include_non_stock_items):
	stock_filter = item.is_stock_item.isin([0, 1]) if include_non_stock_items else item.is_stock_item == 1
	return (bei.docstatus < 2) & (bei.is_sub_assembly_item == 0) & (bom.name == bom_no) & stock_filter


def _apply_exploded_conversion(item_details, data):
	for d in data:
		if not d.conversion_factor and d.purchase_uom:
			d.conversion_factor = get_uom_conversion_factor(d.item_code, d.purchase_uom)
		item_details.setdefault(d.get("item_code"), d)


def get_subitems(
	doc,
	data,
	item_details,
	bom_no,
	company,
	include_non_stock_items,
	include_subcontracted_items,
	parent_qty,
	planned_qty=1,
):
	for d in _subitems_query(company, bom_no, include_non_stock_items, parent_qty, planned_qty):
		_process_subitem(
			doc, data, item_details, d, company, include_non_stock_items, include_subcontracted_items
		)
	return {key: value for key, value in item_details.items() if not value.get("is_phantom_item")}


def _subitems_query(company, bom_no, include_non_stock_items, parent_qty, planned_qty):
	bom_item = frappe.qb.DocType("BOM Item")
	bom = frappe.qb.DocType("BOM")
	item = frappe.qb.DocType("Item")
	item_default = frappe.qb.DocType("Item Default")
	item_uom = frappe.qb.DocType("UOM Conversion Detail")
	rows = (
		frappe.qb.from_(bom_item)
		.join(bom)
		.on(bom.name == bom_item.parent)
		.join(item)
		.on(bom_item.item_code == item.name)
		.left_join(item_default)
		.on((item.name == item_default.parent) & (item_default.company == company))
		.left_join(item_uom)
		.on((item.name == item_uom.parent) & (item_uom.uom == item.purchase_uom))
		.select(*_subitem_columns(bom_item, bom, item, item_default, item_uom, parent_qty, planned_qty))
		.where(_subitem_filter(bom_item, bom, item, bom_no, include_non_stock_items))
		.groupby(bom_item.item_code)
		# idx is not grouped; Min() preserves the original ordering and is valid on postgres
		.orderby(Min(bom_item.idx))
	).run(as_dict=True)

	_apply_representative_lines(rows, "BOM Item", bom_no, ("item_code",), include_non_stock_items)
	return rows


def _subitem_columns(bom_item, bom, item, item_default, item_uom, parent_qty, planned_qty):
	qty = IfNull(parent_qty * Sum(bom_item.stock_qty / IfNull(bom.quantity, 1)) * planned_qty, 0).as_("qty")
	# only item_code is grouped; the remaining item-attribute columns are functionally dependent on it,
	# so Max() returns their single value on both engines. is_phantom_item is the exception: the same
	# item_code can sit on a phantom line and a real-RM line in one BOM, and get_subitems() drops any
	# row whose is_phantom_item is truthy. Max() would let a single phantom line mask the real material
	# and silently drop it; Min() instead treats the item as phantom only when EVERY line is phantom, so
	# a real raw material is never lost. Deterministic and identical on MariaDB and Postgres.
	return [
		bom_item.item_code,
		Max(item.default_material_request_type).as_("default_material_request_type"),
		Max(item.item_name).as_("item_name"),
		qty,
		Max(item.is_sub_contracted_item).as_("is_sub_contracted"),
		Max(bom_item.description).as_("description"),
		Max(bom_item.source_warehouse).as_("source_warehouse"),
		Count(bom_item.name).distinct().as_("line_count"),
		Max(item.default_bom).as_("default_bom"),
		Max(bom_item.stock_uom).as_("stock_uom"),
		Max(item.min_order_qty).as_("min_order_qty"),
		Max(item.safety_stock).as_("safety_stock"),
		Max(item_default.default_warehouse).as_("default_warehouse"),
		Max(item.purchase_uom).as_("purchase_uom"),
		Max(item_uom.conversion_factor).as_("conversion_factor"),
		Max(bom.item).as_("main_bom_item"),
		Max(bom.name).as_("main_bom"),
		Min(bom_item.is_phantom_item).as_("is_phantom_item"),
	]


def _subitem_filter(bom_item, bom, item, bom_no, include_non_stock_items):
	stock_filter = item.is_stock_item.isin([0, 1]) if include_non_stock_items else item.is_stock_item == 1
	return (
		(bom.name == bom_no)
		& (bom_item.is_sub_assembly_item == 0)
		& (bom_item.docstatus < 2)
		& (stock_filter | (bom_item.is_phantom_item == 1))
	)


def _process_subitem(
	doc, data, item_details, d, company, include_non_stock_items, include_subcontracted_items
):
	if not data.get("include_exploded_items") or not d.default_bom:
		_merge_subitem(item_details, d)

	if d.is_phantom_item or (data.get("include_exploded_items") and d.default_bom):
		if _should_explode_subitem(d, include_subcontracted_items) and d.qty > 0:
			get_subitems(
				doc,
				data,
				item_details,
				d.default_bom,
				company,
				include_non_stock_items,
				include_subcontracted_items,
				d.qty,
			)


def _merge_subitem(item_details, d):
	if d.item_code in item_details:
		item_details[d.item_code].qty = item_details[d.item_code].qty + d.qty
		return

	if not d.conversion_factor and d.purchase_uom:
		d.conversion_factor = get_uom_conversion_factor(d.item_code, d.purchase_uom)
	item_details[d.item_code] = d


def _should_explode_subitem(d, include_subcontracted_items):
	return bool(
		(d.default_material_request_type in ["Manufacture", "Purchase"] and not d.is_sub_contracted)
		or (d.is_sub_contracted and include_subcontracted_items)
		or d.is_phantom_item
	)
