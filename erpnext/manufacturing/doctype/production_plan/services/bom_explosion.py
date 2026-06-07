# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""BOM explosion helpers for Production Plan material planning."""

import frappe
from frappe.query_builder.functions import IfNull, Sum

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
	return (
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


def _exploded_item_columns(bei, bom, item, item_default, item_uom, planned_qty):
	return [
		(IfNull(Sum(bei.stock_qty / IfNull(bom.quantity, 1)), 0) * planned_qty).as_("qty"),
		item.item_name,
		item.name.as_("item_code"),
		bei.description,
		bei.stock_uom,
		item.min_order_qty,
		bei.source_warehouse,
		item.default_material_request_type,
		item.min_order_qty,
		item_default.default_warehouse,
		item.purchase_uom,
		item_uom.conversion_factor,
		item.safety_stock,
		bom.item.as_("main_bom_item"),
		bom.name.as_("main_bom"),
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
	return (
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
		.orderby(bom_item.idx)
	).run(as_dict=True)


def _subitem_columns(bom_item, bom, item, item_default, item_uom, parent_qty, planned_qty):
	qty = IfNull(parent_qty * Sum(bom_item.stock_qty / IfNull(bom.quantity, 1)) * planned_qty, 0).as_("qty")
	return [
		bom_item.item_code,
		item.default_material_request_type,
		item.item_name,
		qty,
		item.is_sub_contracted_item.as_("is_sub_contracted"),
		bom_item.source_warehouse,
		item.default_bom.as_("default_bom"),
		bom_item.description.as_("description"),
		bom_item.stock_uom.as_("stock_uom"),
		item.min_order_qty.as_("min_order_qty"),
		item.safety_stock.as_("safety_stock"),
		item_default.default_warehouse,
		item.purchase_uom,
		item_uom.conversion_factor,
		bom.item.as_("main_bom_item"),
		bom.name.as_("main_bom"),
		bom_item.is_phantom_item,
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
