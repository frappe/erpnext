# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, get_datetime, get_table_name, getdate
from pypika import functions as fn

from erpnext.deprecation_dumpster import deprecated
from erpnext.stock.doctype.stock_closing_entry.stock_closing_entry import StockClosing
from erpnext.stock.doctype.warehouse.warehouse import apply_warehouse_filter

SLE_COUNT_LIMIT = 100_000


def execute(filters=None):
	if not filters:
		filters = {}

	sle_count = frappe.db.estimate_count("Stock Ledger Entry")

	if (
		sle_count > SLE_COUNT_LIMIT
		and not filters.get("item_code")
		and not filters.get("warehouse")
		and not filters.get("warehouse_type")
	):
		frappe.throw(
			_("Please select either the Item or Warehouse or Warehouse Type filter to generate the report.")
		)

	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date must be before To Date"))

	float_precision = cint(frappe.db.get_default("float_precision")) or 3

	columns = get_columns(filters)
	item_map = get_item_details(filters)
	iwb_map = get_item_warehouse_batch_map(filters, float_precision)

	data = []
	for item in sorted(iwb_map):
		if not filters.get("item") or filters.get("item") == item:
			for wh in sorted(iwb_map[item]):
				for batch in sorted(iwb_map[item][wh]):
					qty_dict = iwb_map[item][wh][batch]
					if qty_dict.opening_qty or qty_dict.in_qty or qty_dict.out_qty or qty_dict.bal_qty:
						data.append(
							[
								item,
								item_map[item]["item_name"],
								item_map[item]["description"],
								wh,
								qty_dict.batch_no,
								flt(qty_dict.opening_qty, float_precision),
								flt(qty_dict.in_qty, float_precision),
								flt(qty_dict.out_qty, float_precision),
								flt(qty_dict.bal_qty, float_precision),
								item_map[item]["stock_uom"],
								flt(
									(qty_dict.bal_value / qty_dict.bal_qty) if qty_dict.bal_qty else 0,
									float_precision,
								),
								flt(qty_dict.bal_value, float_precision),
								qty_dict.batch_id,
							]
						)

	return columns, data


def get_columns(filters):
	"""return columns based on filters"""

	columns = [
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 100},
		{"label": _("Item Name"), "fieldname": "item_name", "width": 150},
		{"label": _("Description"), "fieldname": "description", "width": 150},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 100,
		},
		{
			"label": _("Batch"),
			"fieldname": "batch",
			"fieldtype": "Link",
			"options": "Batch",
			"align": "left",
			"width": 150,
		},
		{"label": _("Opening Qty"), "fieldname": "opening_qty", "fieldtype": "Float", "width": 90},
		{"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float", "width": 80},
		{"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 80},
		{"label": _("Balance Qty"), "fieldname": "bal_qty", "fieldtype": "Float", "width": 90},
		{"label": _("UOM"), "fieldname": "stock_uom", "width": 60},
		{"label": _("Valuation Rate"), "fieldname": "val_rate", "fieldtype": "Float", "width": 120},
		{"label": _("Balance Value"), "fieldname": "bal_val", "fieldtype": "Currency", "width": 140},
		{
			"label": _("Batch ID"),
			"fieldname": "batch_id",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 150,
			"hidden": 1,
		},
	]

	return columns


def get_stock_ledger_entries(filters):
	entries = []

	stk_cl_obj = StockClosing(filters.company, filters.from_date, filters.from_date)
	if stk_cl_obj.last_closing_balance:
		entries += get_stock_closing_balance(stk_cl_obj, filters)
		filters.start_from = stk_cl_obj.last_closing_balance.to_date

	entries += get_stock_ledger_entries_for_batch_no(filters)
	entries += get_stock_ledger_entries_for_batch_bundle(filters)

	return entries


def get_stock_closing_balance(stk_cl_obj, filters):
	query_filters = {}
	for field in ["item_code", "warehouse", "company", "batch_no"]:
		if filters.get(field):
			query_filters[field] = filters.get(field)

	if filters.warehouse_type:
		warehouses = frappe.get_all(
			"Warehouse",
			filters={"warehouse_type": filters.warehouse_type, "is_group": 0},
			pluck="name",
		)
		query_filters["warehouse"] = warehouses

	return stk_cl_obj.get_stock_closing_balance(query_filters, for_batch=True)


@deprecated(f"{__name__}.get_stock_ledger_entries_for_batch_no", "unknown", "v16", "No known instructions.")
def get_stock_ledger_entries_for_batch_no(filters):
	if not filters.get("from_date"):
		frappe.throw(_("'From Date' is required"))
	if not filters.get("to_date"):
		frappe.throw(_("'To Date' is required"))

	posting_datetime = get_datetime(add_to_date(filters["to_date"], days=1))
	title_field = frappe.get_meta("Batch", cached=True).get_title_field()

	sle = frappe.qb.DocType("Stock Ledger Entry")
	batch_table = frappe.qb.DocType("Batch")

	query = (
		frappe.qb.from_(sle)
		.inner_join(batch_table)
		.on(batch_table.name == sle.batch_no)
		.select(
			sle.item_code,
			sle.warehouse,
			sle.batch_no.as_("batch_id"),
			sle.posting_date,
			batch_table[title_field].as_("batch_no"),
			fn.Sum(sle.actual_qty).as_("actual_qty"),
			fn.Sum(sle.stock_value_difference).as_("stock_value_difference"),
		)
		.where(
			(sle.docstatus < 2)
			& (sle.is_cancelled == 0)
			& (sle.batch_no != "")
			& (sle.posting_datetime < posting_datetime)
		)
		.groupby(sle.voucher_no, sle.batch_no, sle.item_code, sle.warehouse)
	)

	query = apply_warehouse_filter(query, sle, filters)
	if filters.warehouse_type and not filters.warehouse:
		warehouses = frappe.get_all(
			"Warehouse",
			filters={"warehouse_type": filters.warehouse_type, "is_group": 0},
			pluck="name",
		)

		if warehouses:
			query = query.where(sle.warehouse.isin(warehouses))

	for field in ["item_code", "batch_no", "company"]:
		if filters.get(field):
			query = query.where(sle[field] == filters.get(field))

	if filters.start_from:
		query = query.where(sle.posting_datetime > get_datetime(filters.start_from))

	return query.run(as_dict=True) or []


def get_stock_ledger_entries_for_batch_bundle(filters):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	batch_package = frappe.qb.DocType("Serial and Batch Entry")
	batch_table = frappe.qb.DocType("Batch")
	to_date = get_datetime(str(filters.to_date) + " 23:59:59")
	title_field = frappe.get_meta("Batch", cached=True).get_title_field()

	query = (
		frappe.qb.from_(sle)
		.inner_join(batch_package)
		.on(batch_package.parent == sle.serial_and_batch_bundle)
		.inner_join(batch_table)
		.on(batch_table.name == batch_package.batch_no)
		.select(
			sle.item_code,
			sle.warehouse,
			batch_package.batch_no.as_("batch_id"),
			sle.posting_date,
			batch_table[title_field].as_("batch_no"),
			fn.Sum(batch_package.qty).as_("actual_qty"),
			fn.Sum(batch_package.stock_value_difference).as_("stock_value_difference"),
		)
		.where(
			(sle.docstatus < 2)
			& (sle.is_cancelled == 0)
			& (sle.has_batch_no == 1)
			& (sle.posting_datetime <= to_date)
		)
		.groupby(sle.voucher_no, batch_package.batch_no, batch_package.warehouse)
	)

	query = apply_warehouse_filter(query, sle, filters)
	if filters.warehouse_type and not filters.warehouse:
		warehouses = frappe.get_all(
			"Warehouse",
			filters={"warehouse_type": filters.warehouse_type, "is_group": 0},
			pluck="name",
		)

		if warehouses:
			query = query.where(sle.warehouse.isin(warehouses))

	for field in ["item_code", "batch_no", "company"]:
		if filters.get(field):
			if field == "batch_no":
				query = query.where(batch_package[field] == filters.get(field))
			else:
				query = query.where(sle[field] == filters.get(field))

	if filters.start_from:
		query = query.where(sle.posting_date > getdate(filters.start_from))

	return query.run(as_dict=True) or []


def get_item_warehouse_batch_map(filters, float_precision):
	sle = get_stock_ledger_entries(filters)
	iwb_map = {}

	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	for d in sle:
		iwb_map.setdefault(d.item_code, {}).setdefault(d.warehouse, {}).setdefault(
			d.batch_no,
			frappe._dict(
				{
					"batch_id": d.batch_id,
					"batch_no": d.batch_no,
					"opening_qty": 0.0,
					"in_qty": 0.0,
					"out_qty": 0.0,
					"bal_qty": 0.0,
					"bal_value": 0.0,
				}
			),
		)
		qty_dict = iwb_map[d.item_code][d.warehouse][d.batch_no]
		if d.posting_date < from_date:
			qty_dict.opening_qty = flt(qty_dict.opening_qty, float_precision) + flt(
				d.actual_qty, float_precision
			)
		elif d.posting_date >= from_date and d.posting_date <= to_date:
			if flt(d.actual_qty) > 0:
				qty_dict.in_qty = flt(qty_dict.in_qty, float_precision) + flt(d.actual_qty, float_precision)
			else:
				qty_dict.out_qty = flt(qty_dict.out_qty, float_precision) + abs(
					flt(d.actual_qty, float_precision)
				)

		qty_dict.bal_qty = flt(qty_dict.bal_qty, float_precision) + flt(d.actual_qty, float_precision)
		qty_dict.bal_value += flt(d.stock_value_difference, float_precision)

	return iwb_map


def get_item_details(filters):
	item_map = {}
	for d in (frappe.qb.from_("Item").select("name", "item_name", "description", "stock_uom")).run(as_dict=1):
		item_map.setdefault(d.name, d)

	return item_map
