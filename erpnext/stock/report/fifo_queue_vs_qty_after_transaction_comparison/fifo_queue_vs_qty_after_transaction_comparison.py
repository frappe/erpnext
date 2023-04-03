# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import get_descendants_of

SLE_FIELDS = (
	"name",
	"item_code",
	"warehouse",
	"posting_date",
	"posting_time",
	"creation",
	"voucher_type",
	"voucher_no",
	"actual_qty",
	"qty_after_transaction",
	"stock_queue",
	"batch_no",
	"stock_value",
	"valuation_rate",
)


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
	if not any([filters.warehouse, filters.item_code, filters.item_group]):
		frappe.throw(_("Any one of following filters required: warehouse, Item Code, Item Group"))
	sles = get_stock_ledger_entries(filters)
	return find_first_bad_queue(sles)


def get_stock_ledger_entries(filters):

	sle_filters = {"is_cancelled": 0}

	if filters.warehouse:
		children = get_descendants_of("Warehouse", filters.warehouse)
		sle_filters["warehouse"] = ("in", children + [filters.warehouse])

	if filters.item_code:
		sle_filters["item_code"] = filters.item_code
	elif filters.get("item_group"):
		item_group = filters.get("item_group")
		children = get_descendants_of("Item Group", item_group)
		item_group_filter = {"item_group": ("in", children + [item_group])}
		sle_filters["item_code"] = (
			"in",
			frappe.get_all("Item", filters=item_group_filter, pluck="name", order_by=None),
		)

	if filters.from_date:
		sle_filters["posting_date"] = (">=", filters.from_date)
	if filters.to_date:
		sle_filters["posting_date"] = ("<=", filters.to_date)

	return frappe.get_all(
		"Stock Ledger Entry",
		fields=SLE_FIELDS,
		filters=sle_filters,
		order_by="timestamp(posting_date, posting_time), creation",
	)


def find_first_bad_queue(sles):
	item_warehouse_sles = {}
	for sle in sles:
		item_warehouse_sles.setdefault((sle.item_code, sle.warehouse), []).append(sle)

	data = []

	for _item_wh, sles in item_warehouse_sles.items():
		for idx, sle in enumerate(sles):
			queue = json.loads(sle.stock_queue or "[]")

			sle.fifo_queue_qty = 0.0
			sle.fifo_stock_value = 0.0
			for qty, rate in queue:
				sle.fifo_queue_qty += flt(qty)
				sle.fifo_stock_value += flt(qty) * flt(rate)

			sle.fifo_qty_diff = sle.qty_after_transaction - sle.fifo_queue_qty
			sle.fifo_value_diff = sle.stock_value - sle.fifo_stock_value

			if abs(sle.fifo_qty_diff) > 0.001 or abs(sle.fifo_value_diff) > 0.1:
				if idx:
					data.append(sles[idx - 1])
				data.append(sle)
				data.append({})
				break

	return data


def get_columns():
	return [
		{
			"fieldname": "name",
			"fieldtype": "Link",
			"label": _("Stock Ledger Entry"),
			"options": "Stock Ledger Entry",
		},
		{
			"fieldname": "item_code",
			"fieldtype": "Link",
			"label": _("Item Code"),
			"options": "Item",
		},
		{
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"label": _("Warehouse"),
			"options": "Warehouse",
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
			"fieldname": "qty_after_transaction",
			"fieldtype": "Float",
			"label": _("(A) Qty After Transaction"),
		},
		{
			"fieldname": "stock_queue",
			"fieldtype": "Data",
			"label": _("FIFO/LIFO Queue"),
		},
		{
			"fieldname": "fifo_queue_qty",
			"fieldtype": "Float",
			"label": _("(C) Total qty in queue"),
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
			"fieldname": "valuation_rate",
			"fieldtype": "Float",
			"label": _("(H) Valuation Rate"),
		},
	]
