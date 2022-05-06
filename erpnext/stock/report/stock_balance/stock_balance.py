# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from operator import itemgetter
from typing import Any, Dict, List, Optional, TypedDict

import frappe
from frappe import _
from frappe.query_builder.functions import CombineDatetime
from frappe.utils import cint, date_diff, flt, getdate
from frappe.utils.nestedset import get_descendants_of
from pypika.terms import ExistsCriterion

import erpnext
from erpnext.stock.report.stock_ageing.stock_ageing import FIFOSlots, get_average_age
from erpnext.stock.utils import add_additional_uom_columns, is_reposting_item_valuation_in_progress


class StockBalanceFilter(TypedDict):
	company: Optional[str]
	from_date: str
	to_date: str
	item_group: Optional[str]
	item: Optional[str]
	warehouse: Optional[str]
	warehouse_type: Optional[str]
	include_uom: Optional[str]  # include extra info in converted UOM
	show_stock_ageing_data: bool
	show_variant_attributes: bool


SLEntry = Dict[str, Any]


def execute(filters: Optional[StockBalanceFilter] = None):
	is_reposting_item_valuation_in_progress()
	if not filters:
		filters = {}

	if filters.get("company"):
		company_currency = erpnext.get_company_currency(filters.get("company"))
	else:
		company_currency = frappe.db.get_single_value("Global Defaults", "default_currency")

	include_uom = filters.get("include_uom")
	columns = get_columns(filters)
	items = get_items(filters)
	sle = get_stock_ledger_entries(filters, items)

	if filters.get("show_stock_ageing_data"):
		filters["show_warehouse_wise_stock"] = True
		item_wise_fifo_queue = FIFOSlots(filters, sle).generate()

	# if no stock ledger entry found return
	if not sle:
		return columns, []

	iwb_map = get_item_warehouse_map(filters, sle)
	item_map = get_item_details(items, sle, filters)
	item_reorder_detail_map = get_item_reorder_details(item_map.keys())

	data = []
	conversion_factors = {}

	_func = itemgetter(1)

	to_date = filters.get("to_date")
	for (company, item, warehouse) in sorted(iwb_map):
		if item_map.get(item):
			qty_dict = iwb_map[(company, item, warehouse)]
			item_reorder_level = 0
			item_reorder_qty = 0
			if item + warehouse in item_reorder_detail_map:
				item_reorder_level = item_reorder_detail_map[item + warehouse]["warehouse_reorder_level"]
				item_reorder_qty = item_reorder_detail_map[item + warehouse]["warehouse_reorder_qty"]

			report_data = {
				"currency": company_currency,
				"item_code": item,
				"warehouse": warehouse,
				"company": company,
				"reorder_level": item_reorder_level,
				"reorder_qty": item_reorder_qty,
			}
			report_data.update(item_map[item])
			report_data.update(qty_dict)

			if include_uom:
				conversion_factors.setdefault(item, item_map[item].conversion_factor)

			if filters.get("show_stock_ageing_data"):
				fifo_queue = item_wise_fifo_queue[(item, warehouse)].get("fifo_queue")

				stock_ageing_data = {"average_age": 0, "earliest_age": 0, "latest_age": 0}
				if fifo_queue:
					fifo_queue = sorted(filter(_func, fifo_queue), key=_func)
					if not fifo_queue:
						continue

					stock_ageing_data["average_age"] = get_average_age(fifo_queue, to_date)
					stock_ageing_data["earliest_age"] = date_diff(to_date, fifo_queue[0][1])
					stock_ageing_data["latest_age"] = date_diff(to_date, fifo_queue[-1][1])

				report_data.update(stock_ageing_data)

			data.append(report_data)

	add_additional_uom_columns(columns, data, include_uom, conversion_factors)
	return columns, data


def get_columns(filters: StockBalanceFilter):
	"""return columns"""
	columns = [
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 100,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "width": 150},
		{
			"label": _("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 100,
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 100,
		},
		{
			"label": _("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 90,
		},
		{
			"label": _("Balance Qty"),
			"fieldname": "bal_qty",
			"fieldtype": "Float",
			"width": 100,
			"convertible": "qty",
		},
		{
			"label": _("Balance Value"),
			"fieldname": "bal_val",
			"fieldtype": "Currency",
			"width": 100,
			"options": "currency",
		},
		{
			"label": _("Opening Qty"),
			"fieldname": "opening_qty",
			"fieldtype": "Float",
			"width": 100,
			"convertible": "qty",
		},
		{
			"label": _("Opening Value"),
			"fieldname": "opening_val",
			"fieldtype": "Currency",
			"width": 110,
			"options": "currency",
		},
		{
			"label": _("In Qty"),
			"fieldname": "in_qty",
			"fieldtype": "Float",
			"width": 80,
			"convertible": "qty",
		},
		{"label": _("In Value"), "fieldname": "in_val", "fieldtype": "Float", "width": 80},
		{
			"label": _("Out Qty"),
			"fieldname": "out_qty",
			"fieldtype": "Float",
			"width": 80,
			"convertible": "qty",
		},
		{"label": _("Out Value"), "fieldname": "out_val", "fieldtype": "Float", "width": 80},
		{
			"label": _("Valuation Rate"),
			"fieldname": "val_rate",
			"fieldtype": "Currency",
			"width": 90,
			"convertible": "rate",
			"options": "currency",
		},
		{
			"label": _("Reorder Level"),
			"fieldname": "reorder_level",
			"fieldtype": "Float",
			"width": 80,
			"convertible": "qty",
		},
		{
			"label": _("Reorder Qty"),
			"fieldname": "reorder_qty",
			"fieldtype": "Float",
			"width": 80,
			"convertible": "qty",
		},
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 100,
		},
	]

	if filters.get("show_stock_ageing_data"):
		columns += [
			{"label": _("Average Age"), "fieldname": "average_age", "width": 100},
			{"label": _("Earliest Age"), "fieldname": "earliest_age", "width": 100},
			{"label": _("Latest Age"), "fieldname": "latest_age", "width": 100},
		]

	if filters.get("show_variant_attributes"):
		columns += [
			{"label": att_name, "fieldname": att_name, "width": 100}
			for att_name in get_variants_attributes()
		]

	return columns


def apply_conditions(query, filters):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	warehouse_table = frappe.qb.DocType("Warehouse")

	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))

	if to_date := filters.get("to_date"):
		query = query.where(sle.posting_date <= to_date)
	else:
		frappe.throw(_("'To Date' is required"))

	if company := filters.get("company"):
		query = query.where(sle.company == company)

	if warehouse := filters.get("warehouse"):
		lft, rgt = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"])
		chilren_subquery = (
			frappe.qb.from_(warehouse_table)
			.select(warehouse_table.name)
			.where(
				(warehouse_table.lft >= lft)
				& (warehouse_table.rgt <= rgt)
				& (warehouse_table.name == sle.warehouse)
			)
		)
		query = query.where(ExistsCriterion(chilren_subquery))
	elif warehouse_type := filters.get("warehouse_type"):
		query = (
			query.join(warehouse_table)
			.on(warehouse_table.name == sle.warehouse)
			.where(warehouse_table.warehouse_type == warehouse_type)
		)

	return query


def get_stock_ledger_entries(filters: StockBalanceFilter, items: List[str]) -> List[SLEntry]:
	sle = frappe.qb.DocType("Stock Ledger Entry")

	query = (
		frappe.qb.from_(sle)
		.select(
			sle.item_code,
			sle.warehouse,
			sle.posting_date,
			sle.actual_qty,
			sle.valuation_rate,
			sle.company,
			sle.voucher_type,
			sle.qty_after_transaction,
			sle.stock_value_difference,
			sle.item_code.as_("name"),
			sle.voucher_no,
			sle.stock_value,
			sle.batch_no,
		)
		.where((sle.docstatus < 2) & (sle.is_cancelled == 0))
		.orderby(CombineDatetime(sle.posting_date, sle.posting_time))
		.orderby(sle.creation)
		.orderby(sle.actual_qty)
	)

	if items:
		query = query.where(sle.item_code.isin(items))

	query = apply_conditions(query, filters)
	return query.run(as_dict=True)


def get_item_warehouse_map(filters: StockBalanceFilter, sle: List[SLEntry]):
	iwb_map = {}
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	for d in sle:
		key = (d.company, d.item_code, d.warehouse)
		if key not in iwb_map:
			iwb_map[key] = frappe._dict(
				{
					"opening_qty": 0.0,
					"opening_val": 0.0,
					"in_qty": 0.0,
					"in_val": 0.0,
					"out_qty": 0.0,
					"out_val": 0.0,
					"bal_qty": 0.0,
					"bal_val": 0.0,
					"val_rate": 0.0,
				}
			)

		qty_dict = iwb_map[(d.company, d.item_code, d.warehouse)]

		if d.voucher_type == "Stock Reconciliation" and not d.batch_no:
			qty_diff = flt(d.qty_after_transaction) - flt(qty_dict.bal_qty)
		else:
			qty_diff = flt(d.actual_qty)

		value_diff = flt(d.stock_value_difference)

		if d.posting_date < from_date or (
			d.posting_date == from_date
			and d.voucher_type == "Stock Reconciliation"
			and frappe.db.get_value("Stock Reconciliation", d.voucher_no, "purpose") == "Opening Stock"
		):
			qty_dict.opening_qty += qty_diff
			qty_dict.opening_val += value_diff

		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(qty_diff, float_precision) >= 0:
				qty_dict.in_qty += qty_diff
				qty_dict.in_val += value_diff
			else:
				qty_dict.out_qty += abs(qty_diff)
				qty_dict.out_val += abs(value_diff)

		qty_dict.val_rate = d.valuation_rate
		qty_dict.bal_qty += qty_diff
		qty_dict.bal_val += value_diff

	iwb_map = filter_items_with_no_transactions(iwb_map, float_precision)

	return iwb_map


def filter_items_with_no_transactions(iwb_map, float_precision: float):
	for (company, item, warehouse) in sorted(iwb_map):
		qty_dict = iwb_map[(company, item, warehouse)]

		no_transactions = True
		for key, val in qty_dict.items():
			val = flt(val, float_precision)
			qty_dict[key] = val
			if key != "val_rate" and val:
				no_transactions = False

		if no_transactions:
			iwb_map.pop((company, item, warehouse))

	return iwb_map


def get_items(filters: StockBalanceFilter) -> List[str]:
	"Get items based on item code, item group or brand."
	if item_code := filters.get("item_code"):
		return [item_code]
	else:
		item_filters = {}
		if item_group := filters.get("item_group"):
			children = get_descendants_of("Item Group", item_group, ignore_permissions=True)
			item_filters["item_group"] = ("in", children + [item_group])
		if brand := filters.get("brand"):
			item_filters["brand"] = brand

		return frappe.get_all("Item", filters=item_filters, pluck="name", order_by=None)


def get_item_details(items: List[str], sle: List[SLEntry], filters: StockBalanceFilter):
	item_details = {}
	if not items:
		items = list(set(d.item_code for d in sle))

	if not items:
		return item_details

	item_table = frappe.qb.DocType("Item")

	query = (
		frappe.qb.from_(item_table)
		.select(
			item_table.name,
			item_table.item_name,
			item_table.description,
			item_table.item_group,
			item_table.brand,
			item_table.stock_uom,
		)
		.where(item_table.name.isin(items))
	)

	if uom := filters.get("include_uom"):
		uom_conv_detail = frappe.qb.DocType("UOM Conversion Detail")
		query = (
			query.left_join(uom_conv_detail)
			.on((uom_conv_detail.parent == item_table.name) & (uom_conv_detail.uom == uom))
			.select(uom_conv_detail.conversion_factor)
		)

	result = query.run(as_dict=1)

	for item_table in result:
		item_details.setdefault(item_table.name, item_table)

	if filters.get("show_variant_attributes"):
		variant_values = get_variant_values_for(list(item_details))
		item_details = {k: v.update(variant_values.get(k, {})) for k, v in item_details.items()}

	return item_details


def get_item_reorder_details(items):
	item_reorder_details = frappe._dict()

	if items:
		item_reorder_details = frappe.get_all(
			"Item Reorder",
			["parent", "warehouse", "warehouse_reorder_qty", "warehouse_reorder_level"],
			filters={"parent": ("in", items)},
		)

	return dict((d.parent + d.warehouse, d) for d in item_reorder_details)


def get_variants_attributes() -> List[str]:
	"""Return all item variant attributes."""
	return frappe.get_all("Item Attribute", pluck="name")


def get_variant_values_for(items):
	"""Returns variant values for items."""
	attribute_map = {}

	attribute_info = frappe.get_all(
		"Item Variant Attribute",
		["parent", "attribute", "attribute_value"],
		{
			"parent": ("in", items),
		},
	)

	for attr in attribute_info:
		attribute_map.setdefault(attr["parent"], {})
		attribute_map[attr["parent"]].update({attr["attribute"]: attr["attribute_value"]})

	return attribute_map
