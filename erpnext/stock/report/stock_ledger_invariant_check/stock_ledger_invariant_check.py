# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU GPL v3. See LICENSE

import json

import frappe

SLE_FIELDS = (
	"name",
	"posting_date",
	"posting_time",
	"creation",
	"voucher_type",
	"voucher_no",
	"actual_qty",
	"qty_after_transaction",
	"incoming_rate",
	"outgoing_rate",
	"stock_queue",
	"batch_no",
	"stock_value",
	"stock_value_difference",
	"valuation_rate",
	"voucher_detail_no",
)


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
	sles = get_stock_ledger_entries(filters)
	return add_invariant_check_fields(sles)


def get_stock_ledger_entries(filters):
	return frappe.get_all(
		"Stock Ledger Entry",
		fields=SLE_FIELDS,
		filters={"item_code": filters.item_code, "warehouse": filters.warehouse, "is_cancelled": 0},
		order_by="timestamp(posting_date, posting_time), creation",
	)


def add_invariant_check_fields(sles):
	balance_qty = 0.0
	balance_stock_value = 0.0
	for idx, sle in enumerate(sles):
		queue = json.loads(sle.stock_queue)

		fifo_qty = 0.0
		fifo_value = 0.0
		for qty, rate in queue:
			fifo_qty += qty
			fifo_value += qty * rate

		if sle.actual_qty < 0:
			sle.consumption_rate = sle.stock_value_difference / sle.actual_qty

		balance_qty += sle.actual_qty
		balance_stock_value += sle.stock_value_difference
		if sle.voucher_type == "Stock Reconciliation" and not sle.batch_no:
			balance_qty = frappe.db.get_value("Stock Reconciliation Item", sle.voucher_detail_no, "qty")
			if balance_qty is None:
				balance_qty = sle.qty_after_transaction

		sle.fifo_queue_qty = fifo_qty
		sle.fifo_stock_value = fifo_value
		sle.fifo_valuation_rate = fifo_value / fifo_qty if fifo_qty else None
		sle.balance_value_by_qty = (
			sle.stock_value / sle.qty_after_transaction if sle.qty_after_transaction else None
		)
		sle.expected_qty_after_transaction = balance_qty
		sle.stock_value_from_diff = balance_stock_value

		# set difference fields
		sle.difference_in_qty = sle.qty_after_transaction - sle.expected_qty_after_transaction
		sle.fifo_qty_diff = sle.qty_after_transaction - fifo_qty
		sle.fifo_value_diff = sle.stock_value - fifo_value
		sle.fifo_valuation_diff = (
			sle.valuation_rate - sle.fifo_valuation_rate if sle.fifo_valuation_rate else None
		)
		sle.valuation_diff = (
			sle.valuation_rate - sle.balance_value_by_qty if sle.balance_value_by_qty else None
		)
		sle.diff_value_diff = sle.stock_value_from_diff - sle.stock_value

		if idx > 0:
			sle.fifo_stock_diff = sle.fifo_stock_value - sles[idx - 1].fifo_stock_value
			sle.fifo_difference_diff = sle.fifo_stock_diff - sle.stock_value_difference

	return sles


def get_columns():
	return [
		{
			"fieldname": "name",
			"fieldtype": "Link",
			"label": "Stock Ledger Entry",
			"options": "Stock Ledger Entry",
		},
		{
			"fieldname": "posting_date",
			"fieldtype": "Data",
			"label": "Posting Date",
		},
		{
			"fieldname": "posting_time",
			"fieldtype": "Data",
			"label": "Posting Time",
		},
		{
			"fieldname": "creation",
			"fieldtype": "Data",
			"label": "Creation",
		},
		{
			"fieldname": "voucher_type",
			"fieldtype": "Link",
			"label": "Voucher Type",
			"options": "DocType",
		},
		{
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"label": "Voucher No",
			"options": "voucher_type",
		},
		{
			"fieldname": "batch_no",
			"fieldtype": "Link",
			"label": "Batch",
			"options": "Batch",
		},
		{
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"label": "Qty Change",
		},
		{
			"fieldname": "incoming_rate",
			"fieldtype": "Float",
			"label": "Incoming Rate",
		},
		{
			"fieldname": "consumption_rate",
			"fieldtype": "Float",
			"label": "Consumption Rate",
		},
		{
			"fieldname": "qty_after_transaction",
			"fieldtype": "Float",
			"label": "(A) Qty After Transaction",
		},
		{
			"fieldname": "expected_qty_after_transaction",
			"fieldtype": "Float",
			"label": "(B) Expected Qty After Transaction",
		},
		{
			"fieldname": "difference_in_qty",
			"fieldtype": "Float",
			"label": "A - B",
		},
		{
			"fieldname": "stock_queue",
			"fieldtype": "Data",
			"label": "FIFO Queue",
		},
		{
			"fieldname": "fifo_queue_qty",
			"fieldtype": "Float",
			"label": "(C) Total qty in queue",
		},
		{
			"fieldname": "fifo_qty_diff",
			"fieldtype": "Float",
			"label": "A - C",
		},
		{
			"fieldname": "stock_value",
			"fieldtype": "Float",
			"label": "(D) Balance Stock Value",
		},
		{
			"fieldname": "fifo_stock_value",
			"fieldtype": "Float",
			"label": "(E) Balance Stock Value in Queue",
		},
		{
			"fieldname": "fifo_value_diff",
			"fieldtype": "Float",
			"label": "D - E",
		},
		{
			"fieldname": "stock_value_difference",
			"fieldtype": "Float",
			"label": "(F) Stock Value Difference",
		},
		{
			"fieldname": "stock_value_from_diff",
			"fieldtype": "Float",
			"label": "Balance Stock Value using (F)",
		},
		{
			"fieldname": "diff_value_diff",
			"fieldtype": "Float",
			"label": "K - D",
		},
		{
			"fieldname": "fifo_stock_diff",
			"fieldtype": "Float",
			"label": "(G) Stock Value difference (FIFO queue)",
		},
		{
			"fieldname": "fifo_difference_diff",
			"fieldtype": "Float",
			"label": "F - G",
		},
		{
			"fieldname": "valuation_rate",
			"fieldtype": "Float",
			"label": "(H) Valuation Rate",
		},
		{
			"fieldname": "fifo_valuation_rate",
			"fieldtype": "Float",
			"label": "(I) Valuation Rate as per FIFO",
		},
		{
			"fieldname": "fifo_valuation_diff",
			"fieldtype": "Float",
			"label": "H - I",
		},
		{
			"fieldname": "balance_value_by_qty",
			"fieldtype": "Float",
			"label": "(J) Valuation = Value (D) ÷ Qty (A)",
		},
		{
			"fieldname": "valuation_diff",
			"fieldtype": "Float",
			"label": "H - J",
		},
	]
