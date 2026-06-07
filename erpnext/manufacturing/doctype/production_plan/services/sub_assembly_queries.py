# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Sub-assembly resolution helpers for Production Plan."""

import frappe
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import flt

from erpnext.manufacturing.doctype.bom.bom import get_children as get_bom_children
from erpnext.manufacturing.doctype.production_plan.services.planning_queries import (
	get_bin_details,
	get_uom_conversion_factor,
)


def get_sub_assembly_items(
	sub_assembly_items,
	bin_details,
	bom_no,
	bom_data,
	to_produce_qty,
	company,
	warehouse=None,
	indent=0,
	skip_available_sub_assembly_item=False,
):
	precision = frappe.get_precision("Production Plan Sub Assembly Item", "qty")
	parent_item_code = frappe.get_cached_value("BOM", bom_no, "item")

	for d in get_bom_children(parent=bom_no):
		if not d.expandable:
			continue

		stock_qty = _add_sub_assembly_child(
			d,
			parent_item_code,
			bom_no,
			bom_data,
			sub_assembly_items,
			bin_details,
			to_produce_qty,
			company,
			warehouse,
			indent,
			precision,
			skip_available_sub_assembly_item,
		)
		if d.value:
			get_sub_assembly_items(
				sub_assembly_items,
				bin_details,
				d.value,
				bom_data,
				stock_qty,
				company,
				warehouse,
				indent=indent + 1,
				skip_available_sub_assembly_item=skip_available_sub_assembly_item,
			)


def _add_sub_assembly_child(
	d,
	parent_item_code,
	bom_no,
	bom_data,
	sub_assembly_items,
	bin_details,
	to_produce_qty,
	company,
	warehouse,
	indent,
	precision,
	skip_available,
):
	required_qty = (d.stock_qty / d.parent_bom_qty) * flt(to_produce_qty)
	stock_qty = _resolve_available_sub_assembly(
		d, required_qty, sub_assembly_items, bin_details, company, warehouse, skip_available
	)
	if not d.is_phantom_item:
		bom_data.append(
			_sub_assembly_row(
				d, parent_item_code, bom_no, bin_details, stock_qty, required_qty, indent, precision
			)
		)
	return stock_qty


def _resolve_available_sub_assembly(
	d, stock_qty, sub_assembly_items, bin_details, company, warehouse, skip_available
):
	if skip_available and d.item_code not in sub_assembly_items:
		bin_details.setdefault(d.item_code, get_bin_details(d, company, for_warehouse=warehouse))
		return _consume_projected_qty(d, stock_qty, sub_assembly_items, bin_details)

	if warehouse:
		bin_details.setdefault(d.item_code, get_bin_details(d, company, for_warehouse=warehouse))
	return stock_qty


def _consume_projected_qty(d, stock_qty, sub_assembly_items, bin_details):
	for _bin_dict in bin_details[d.item_code]:
		_bin_dict.original_projected_qty = _bin_dict.projected_qty
		if _bin_dict.original_projected_qty <= 0:
			continue

		if _bin_dict.original_projected_qty >= stock_qty:
			_bin_dict.original_projected_qty -= stock_qty
			stock_qty = 0
			continue

		stock_qty -= _bin_dict.original_projected_qty
		sub_assembly_items.append(d.item_code)
	return stock_qty


def _sub_assembly_row(d, parent_item_code, bom_no, bin_details, stock_qty, required_qty, indent, precision):
	bins = bin_details.get(d.item_code)
	actual_qty = bins[0].get("actual_qty", 0) if bins else 0
	projected_qty = bins[0].get("projected_qty", 0) if bins else 0
	return frappe._dict(
		{
			"actual_qty": actual_qty,
			"parent_item_code": parent_item_code,
			"description": d.description,
			"production_item": d.item_code,
			"item_name": d.item_name,
			"stock_uom": d.stock_uom,
			"uom": d.stock_uom,
			"bom_no": d.value,
			"is_sub_contracted_item": d.is_sub_contracted_item,
			"bom_level": indent,
			"indent": indent,
			"stock_qty": flt(stock_qty, precision),
			"required_qty": flt(required_qty, precision),
			"projected_qty": projected_qty,
			"main_bom": bom_no,
		}
	)


def get_raw_materials_of_sub_assembly_items(
	existing_sub_assembly_items,
	item_details,
	company,
	bom_no,
	include_non_stock_items,
	sub_assembly_items,
	planned_qty=1,
):
	for item in _sub_assembly_rm_query(company, bom_no, include_non_stock_items, planned_qty):
		_process_sub_assembly_rm(
			item,
			existing_sub_assembly_items,
			item_details,
			company,
			include_non_stock_items,
			sub_assembly_items,
		)
	return item_details


def _sub_assembly_rm_query(company, bom_no, include_non_stock_items, planned_qty):
	bei = frappe.qb.DocType("BOM Item")
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
		.select(*_sub_assembly_rm_columns(bei, bom, item, item_default, item_uom, planned_qty))
		.where(_sub_assembly_rm_filter(bei, bom, item, bom_no, include_non_stock_items))
		.groupby(bei.item_code, bei.stock_uom)
	).run(as_dict=True)


def _sub_assembly_rm_columns(bei, bom, item, item_default, item_uom, planned_qty):
	return [
		(IfNull(Sum(bei.stock_qty / IfNull(bom.quantity, 1)), 0) * planned_qty).as_("qty"),
		item.item_name,
		item.name.as_("item_code"),
		bei.description,
		bei.stock_uom,
		bei.is_phantom_item,
		bei.bom_no,
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


def _sub_assembly_rm_filter(bei, bom, item, bom_no, include_non_stock_items):
	stock_filter = item.is_stock_item.isin([0, 1]) if include_non_stock_items else item.is_stock_item == 1
	return (
		(bei.docstatus == 1)
		& (bei.is_sub_assembly_item == 0)
		& (bom.name == bom_no)
		& (stock_filter | (bei.is_phantom_item == 1))
	)


def _process_sub_assembly_rm(
	item, existing_sub_assembly_items, item_details, company, include_non_stock_items, sub_assembly_items
):
	key = (item.item_code, item.bom_no)
	existing_key = (item.item_code, item.bom_no or item.main_bom)

	if item.bom_no and not item.is_phantom_item and key not in sub_assembly_items:
		return
	if not item.is_phantom_item and existing_key in existing_sub_assembly_items:
		return

	if not item.bom_no:
		_merge_sub_assembly_rm(item, item_details)
		return

	recursion_qty = flt(item.get("qty")) if item.is_phantom_item else flt(sub_assembly_items[key])
	get_raw_materials_of_sub_assembly_items(
		existing_sub_assembly_items,
		item_details,
		company,
		item.bom_no,
		include_non_stock_items,
		sub_assembly_items,
		planned_qty=recursion_qty,
	)
	if not item.is_phantom_item:
		existing_sub_assembly_items.add(existing_key)


def _merge_sub_assembly_rm(item, item_details):
	if not item.conversion_factor and item.purchase_uom:
		item.conversion_factor = get_uom_conversion_factor(item.item_code, item.purchase_uom)

	key = (item.get("item_code"), item.get("main_bom"))
	if details := item_details.get(key):
		details.qty += item.get("qty")
	else:
		item_details.setdefault(key, item)
