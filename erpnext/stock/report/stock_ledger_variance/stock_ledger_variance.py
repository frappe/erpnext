# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt

from erpnext.stock.report.stock_ledger_invariant_check.stock_ledger_invariant_check import (
	get_data as stock_ledger_invariant_check,
)


def execute(filters=None):
	columns, data = [], []

	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{
			"fieldname": "name",
			"fieldtype": "Link",
			"label": _("Stock Ledger Entry"),
			"options": "Stock Ledger Entry",
		},
		{
			"fieldname": "posting_date",
			"fieldtype": "Data",
			"label": _("Posting Date"),
		},
		{
			"fieldname": "posting_time",
			"fieldtype": "Data",
			"label": _("Posting Time"),
		},
		{
			"fieldname": "creation",
			"fieldtype": "Data",
			"label": _("Creation"),
		},
		{
			"fieldname": "item_code",
			"fieldtype": "Link",
			"label": _("Item"),
			"options": "Item",
		},
		{
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"label": _("Warehouse"),
			"options": "Warehouse",
		},
		{
			"fieldname": "valuation_method",
			"fieldtype": "Data",
			"label": _("Valuation Method"),
		},
		{
			"fieldname": "voucher_type",
			"fieldtype": "Link",
			"label": _("Voucher Type"),
			"options": "DocType",
		},
		{
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"label": _("Voucher No"),
			"options": "voucher_type",
		},
		{
			"fieldname": "batch_no",
			"fieldtype": "Link",
			"label": _("Batch"),
			"options": "Batch",
		},
		{
			"fieldname": "use_batchwise_valuation",
			"fieldtype": "Check",
			"label": _("Batchwise Valuation"),
		},
		{
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"label": _("Qty Change"),
		},
		{
			"fieldname": "incoming_rate",
			"fieldtype": "Float",
			"label": _("Incoming Rate"),
		},
		{
			"fieldname": "consumption_rate",
			"fieldtype": "Float",
			"label": _("Consumption Rate"),
		},
		{
			"fieldname": "qty_after_transaction",
			"fieldtype": "Float",
			"label": _("(A) Qty After Transaction"),
		},
		{
			"fieldname": "expected_qty_after_transaction",
			"fieldtype": "Float",
			"label": _("(B) Expected Qty After Transaction"),
		},
		{
			"fieldname": "difference_in_qty",
			"fieldtype": "Float",
			"label": _("A - B"),
		},
		{
			"fieldname": "stock_queue",
			"fieldtype": "Data",
			"label": _("FIFO/LIFO Queue"),
		},
		{
			"fieldname": "fifo_queue_qty",
			"fieldtype": "Float",
			"label": _("(C) Total Qty in Queue"),
		},
		{
			"fieldname": "fifo_qty_diff",
			"fieldtype": "Float",
			"label": _("A - C"),
		},
		{
			"fieldname": "stock_value",
			"fieldtype": "Float",
			"label": _("(D) Balance Stock Value"),
		},
		{
			"fieldname": "fifo_stock_value",
			"fieldtype": "Float",
			"label": _("(E) Balance Stock Value in Queue"),
		},
		{
			"fieldname": "fifo_value_diff",
			"fieldtype": "Float",
			"label": _("D - E"),
		},
		{
			"fieldname": "stock_value_difference",
			"fieldtype": "Float",
			"label": _("(F) Change in Stock Value"),
		},
		{
			"fieldname": "stock_value_from_diff",
			"fieldtype": "Float",
			"label": _("(G) Sum of Change in Stock Value"),
		},
		{
			"fieldname": "diff_value_diff",
			"fieldtype": "Float",
			"label": _("G - D"),
		},
		{
			"fieldname": "fifo_stock_diff",
			"fieldtype": "Float",
			"label": _("(H) Change in Stock Value (FIFO Queue)"),
		},
		{
			"fieldname": "fifo_difference_diff",
			"fieldtype": "Float",
			"label": _("H - F"),
		},
		{
			"fieldname": "valuation_rate",
			"fieldtype": "Float",
			"label": _("(I) Valuation Rate"),
		},
		{
			"fieldname": "fifo_valuation_rate",
			"fieldtype": "Float",
			"label": _("(J) Valuation Rate as per FIFO"),
		},
		{
			"fieldname": "fifo_valuation_diff",
			"fieldtype": "Float",
			"label": _("I - J"),
		},
		{
			"fieldname": "balance_value_by_qty",
			"fieldtype": "Float",
			"label": _("(K) Valuation = Value (D) ÷ Qty (A)"),
		},
		{
			"fieldname": "valuation_diff",
			"fieldtype": "Float",
			"label": _("I - K"),
		},
	]


def get_data(filters=None):
	filters = frappe._dict(filters or {})
	item_warehouse_map = get_item_warehouse_combinations(filters)
	valuation_method = frappe.db.get_single_value("Stock Settings", "valuation_method")

	data = []
	if item_warehouse_map:
		precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))

		for item_warehouse in item_warehouse_map:
			report_data = stock_ledger_invariant_check(item_warehouse)

			if not report_data:
				continue

			for row in report_data:
				if has_difference(
					row, precision, filters.difference_in, item_warehouse.valuation_method or valuation_method
				):
					row.update(
						{
							"item_code": item_warehouse.item_code,
							"warehouse": item_warehouse.warehouse,
							"valuation_method": item_warehouse.valuation_method or valuation_method,
						}
					)
					data.append(row)
					break

	return data


def get_item_warehouse_combinations(filters: dict = None) -> dict:
	filters = frappe._dict(filters or {})

	bin = frappe.qb.DocType("Bin")
	item = frappe.qb.DocType("Item")
	warehouse = frappe.qb.DocType("Warehouse")

	query = (
		frappe.qb.from_(bin)
		.inner_join(item)
		.on(bin.item_code == item.name)
		.inner_join(warehouse)
		.on(bin.warehouse == warehouse.name)
		.select(
			bin.item_code,
			bin.warehouse,
			item.valuation_method,
		)
		.where(
			(item.is_stock_item == 1)
			& (item.has_serial_no == 0)
			& (warehouse.is_group == 0)
			& (warehouse.company == filters.company)
		)
	)

	if filters.item_code:
		query = query.where(item.name == filters.item_code)
	if filters.warehouse:
		query = query.where(warehouse.name == filters.warehouse)
	if not filters.include_disabled:
		query = query.where((item.disabled == 0) & (warehouse.disabled == 0))

	return query.run(as_dict=1)


def has_difference(row, precision, difference_in, valuation_method):
	if valuation_method == "Moving Average":
		qty_diff = flt(row.difference_in_qty, precision)
		value_diff = flt(row.diff_value_diff, precision)
		valuation_diff = flt(row.valuation_diff, precision)
	else:
		qty_diff = flt(row.difference_in_qty, precision) or flt(row.fifo_qty_diff, precision)
		value_diff = (
			flt(row.diff_value_diff, precision)
			or flt(row.fifo_value_diff, precision)
			or flt(row.fifo_difference_diff, precision)
		)
		valuation_diff = flt(row.valuation_diff, precision) or flt(row.fifo_valuation_diff, precision)

	if difference_in == "Qty" and qty_diff:
		return True
	elif difference_in == "Value" and value_diff:
		return True
	elif difference_in == "Valuation" and valuation_diff:
		return True
	elif difference_in not in ["Qty", "Value", "Valuation"] and (
		qty_diff or value_diff or valuation_diff
	):
		return True
