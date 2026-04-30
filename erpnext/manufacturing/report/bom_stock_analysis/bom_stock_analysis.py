# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder.functions import Floor, IfNull, Sum
from frappe.utils import flt, fmt_money
from frappe.utils.data import comma_and
from pypika.terms import ExistsCriterion


def execute(filters=None):
	filters = filters or {}
	if filters.get("qty_to_make"):
		columns = get_columns_with_qty_to_make()
		data = get_data_with_qty_to_make(filters)
	else:
		columns = get_columns_without_qty_to_make()
		data = get_data_without_qty_to_make(filters)

	return columns, data


def fmt_qty(value):
	"""Format a float quantity for display as a string, so blank rows stay blank."""
	return frappe.utils.fmt_money(value, precision=2, currency=None)


def fmt_rate(value):
	"""Format a currency rate for display as a string."""
	currency = frappe.defaults.get_global_default("currency")
	return frappe.utils.fmt_money(value, precision=2, currency=currency)


def get_data_with_qty_to_make(filters):
	bom_data = get_bom_data(filters)
	manufacture_details = get_manufacturer_records()
	purchase_rates = batch_fetch_purchase_rates(bom_data)
	qty_to_make = flt(filters.get("qty_to_make"))

	data = []
	for row in bom_data:
		qty_per_unit = flt(row.qty_per_unit) if row.qty_per_unit > 0 else 0
		required_qty = qty_to_make * qty_per_unit
		difference_qty = flt(row.actual_qty) - required_qty
		rate = purchase_rates.get(row.item_code, 0)

		data.append(
			{
				"item": row.item_code,
				"description": row.description,
				"from_bom_no": row.from_bom_no,
				"manufacturer": comma_and(
					manufacture_details.get(row.item_code, {}).get("manufacturer", []), add_quotes=False
				),
				"manufacturer_part_number": comma_and(
					manufacture_details.get(row.item_code, {}).get("manufacturer_part", []), add_quotes=False
				),
				"qty_per_unit": fmt_qty(qty_per_unit),
				"available_qty": fmt_qty(row.actual_qty),
				"required_qty": fmt_qty(required_qty),
				"difference_qty": fmt_qty(difference_qty),
				"last_purchase_rate": fmt_rate(rate),
				"_available_qty": flt(row.actual_qty),
				"_qty_per_unit": qty_per_unit,
			}
		)

	min_producible = (
		min(int(r["_available_qty"] // r["_qty_per_unit"]) for r in data if r["_qty_per_unit"]) if data else 0
	)

	for row in data:
		row.pop("_available_qty", None)
		row.pop("_qty_per_unit", None)

	# blank spacer row
	data.append({})

	data.append(
		{
			"item": _("Maximum Producible Items"),
			"description": min_producible,
			"from_bom_no": "",
			"manufacturer": "",
			"manufacturer_part_number": "",
			"qty_per_unit": "",
			"available_qty": "",
			"required_qty": "",
			"difference_qty": "",
			"last_purchase_rate": "",
			"bold": 1,
		}
	)

	return data


def get_columns_with_qty_to_make():
	return [
		{"fieldname": "item", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 180},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 160},
		{
			"fieldname": "from_bom_no",
			"label": _("From BOM No"),
			"fieldtype": "Link",
			"options": "BOM",
			"width": 150,
		},
		{"fieldname": "manufacturer", "label": _("Manufacturer"), "fieldtype": "Data", "width": 130},
		{
			"fieldname": "manufacturer_part_number",
			"label": _("Manufacturer Part Number"),
			"fieldtype": "Data",
			"width": 170,
		},
		{"fieldname": "qty_per_unit", "label": _("Qty Per Unit"), "fieldtype": "Data", "width": 110},
		{"fieldname": "available_qty", "label": _("Available Qty"), "fieldtype": "Data", "width": 120},
		{"fieldname": "required_qty", "label": _("Required Qty"), "fieldtype": "Data", "width": 120},
		{"fieldname": "difference_qty", "label": _("Difference Qty"), "fieldtype": "Data", "width": 130},
		{
			"fieldname": "last_purchase_rate",
			"label": _("Last Purchase Rate"),
			"fieldtype": "Data",
			"width": 160,
		},
	]


def get_data_without_qty_to_make(filters):
	raw_rows = get_producible_fg_items(filters)

	data = []
	for row in raw_rows:
		data.append(
			{
				"item": row[0],
				"description": row[1],
				"from_bom_no": row[2],
				"qty_per_unit": fmt_qty(row[3]),
				"available_qty": fmt_qty(row[4]),
			}
		)

	min_producible = min((row[5] or 0) for row in raw_rows) if raw_rows else 0
	# blank spacer row
	data.append({})

	data.append(
		{
			"item": _("Maximum Producible Items"),
			"description": min_producible,
			"from_bom_no": "",
			"qty_per_unit": "",
			"available_qty": "",
			"bold": 1,
		}
	)

	return data


def get_columns_without_qty_to_make():
	return [
		{"fieldname": "item", "label": _("Item"), "fieldtype": "Link", "options": "Item", "width": 180},
		{"fieldname": "description", "label": _("Description"), "fieldtype": "Data", "width": 200},
		{
			"fieldname": "from_bom_no",
			"label": _("From BOM No"),
			"fieldtype": "Link",
			"options": "BOM",
			"width": 160,
		},
		{"fieldname": "qty_per_unit", "label": _("Qty Per Unit"), "fieldtype": "Data", "width": 120},
		{"fieldname": "available_qty", "label": _("Available Qty"), "fieldtype": "Data", "width": 120},
	]


def batch_fetch_purchase_rates(bom_data):
	if not bom_data:
		return {}
	item_codes = [row.item_code for row in bom_data]
	return {
		r.name: r.last_purchase_rate
		for r in frappe.get_all(
			"Item",
			filters={"name": ["in", item_codes]},
			fields=["name", "last_purchase_rate"],
		)
	}


def get_bom_data(filters):
	bom_item_table = "BOM Explosion Item" if filters.get("show_exploded_view") else "BOM Item"

	bom_item = frappe.qb.DocType(bom_item_table)
	bin = frappe.qb.DocType("Bin")

	query = (
		frappe.qb.from_(bom_item)
		.left_join(bin)
		.on(bom_item.item_code == bin.item_code)
		.select(
			bom_item.item_code,
			bom_item.description,
			bom_item.parent.as_("from_bom_no"),
			Sum(bom_item.qty_consumed_per_unit).as_("qty_per_unit"),
			IfNull(Sum(bin.actual_qty), 0).as_("actual_qty"),
		)
		.where((bom_item.parent == filters.get("bom")) & (bom_item.parenttype == "BOM"))
		.groupby(bom_item.item_code)
		.orderby(bom_item.idx)
	)

	if filters.get("warehouse"):
		warehouse_details = frappe.db.get_value(
			"Warehouse", filters.get("warehouse"), ["lft", "rgt"], as_dict=1
		)
		if warehouse_details:
			wh = frappe.qb.DocType("Warehouse")
			query = query.where(
				ExistsCriterion(
					frappe.qb.from_(wh)
					.select(wh.name)
					.where(
						(wh.lft >= warehouse_details.lft)
						& (wh.rgt <= warehouse_details.rgt)
						& (bin.warehouse == wh.name)
					)
				)
			)
		else:
			query = query.where(bin.warehouse == filters.get("warehouse"))

	if bom_item_table == "BOM Item":
		query = query.select(bom_item.bom_no, bom_item.is_phantom_item)

	data = query.run(as_dict=True)
	return explode_phantom_boms(data, filters) if bom_item_table == "BOM Item" else data


def explode_phantom_boms(data, filters):
	original_bom = filters.get("bom")
	replacements = []

	for idx, item in enumerate(data):
		if not item.is_phantom_item:
			continue

		filters["bom"] = item.bom_no
		children = get_bom_data(filters)
		filters["bom"] = original_bom

		for child in children:
			child.qty_per_unit = (child.qty_per_unit or 0) * (item.qty_per_unit or 0)

		replacements.append((idx, children))

	for idx, children in reversed(replacements):
		data.pop(idx)
		data[idx:idx] = children

	return data


def get_manufacturer_records():
	details = frappe.get_all(
		"Item Manufacturer", fields=["manufacturer", "manufacturer_part_no", "item_code"]
	)
	manufacture_details = frappe._dict()
	for detail in details:
		dic = manufacture_details.setdefault(detail.get("item_code"), {})
		dic.setdefault("manufacturer", []).append(detail.get("manufacturer"))
		dic.setdefault("manufacturer_part", []).append(detail.get("manufacturer_part_no"))
	return manufacture_details


def get_producible_fg_items(filters):
	BOM_ITEM = frappe.qb.DocType("BOM Item")
	BOM = frappe.qb.DocType("BOM")
	BIN = frappe.qb.DocType("Bin")
	WH = frappe.qb.DocType("Warehouse")

	warehouse = filters.get("warehouse")
	if not warehouse:
		frappe.throw(_("Warehouse is required to get producible FG Items"))

	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)

	if warehouse_details:
		bin_subquery = (
			frappe.qb.from_(BIN)
			.join(WH)
			.on(BIN.warehouse == WH.name)
			.select(BIN.item_code, Sum(BIN.actual_qty).as_("actual_qty"))
			.where((WH.lft >= warehouse_details.lft) & (WH.rgt <= warehouse_details.rgt))
			.groupby(BIN.item_code)
		)
	else:
		bin_subquery = (
			frappe.qb.from_(BIN)
			.select(BIN.item_code, Sum(BIN.actual_qty).as_("actual_qty"))
			.where(BIN.warehouse == warehouse)
			.groupby(BIN.item_code)
		)

	query = (
		frappe.qb.from_(BOM_ITEM)
		.join(BOM)
		.on(BOM_ITEM.parent == BOM.name)
		.left_join(bin_subquery)
		.on(BOM_ITEM.item_code == bin_subquery.item_code)
		.select(
			BOM_ITEM.item_code,
			BOM_ITEM.description,
			BOM_ITEM.parent.as_("from_bom_no"),
			(BOM_ITEM.stock_qty / BOM.quantity).as_("qty_per_unit"),
			IfNull(bin_subquery.actual_qty, 0).as_("available_qty"),
			Floor(bin_subquery.actual_qty / ((Sum(BOM_ITEM.stock_qty)) / BOM.quantity)),
		)
		.where((BOM_ITEM.parent == filters.get("bom")) & (BOM_ITEM.parenttype == "BOM"))
		.groupby(BOM_ITEM.item_code)
		.orderby(BOM_ITEM.idx)
	)

	return query.run(as_list=True)
