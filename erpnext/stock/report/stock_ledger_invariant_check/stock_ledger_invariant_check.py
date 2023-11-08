# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# License: GNU GPL v3. See LICENSE

import json

import frappe
from frappe import _
from frappe.utils import get_link_to_form, parse_json

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
	"serial_and_batch_bundle",
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
		if (
			sle.voucher_type == "Stock Reconciliation"
			and not sle.batch_no
			and not sle.serial_and_batch_bundle
		):
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

		if sle.batch_no:
			sle.use_batchwise_valuation = frappe.db.get_value(
				"Batch", sle.batch_no, "use_batchwise_valuation", cache=True
			)

	return sles


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
			"fieldname": "serial_and_batch_bundle",
			"fieldtype": "Link",
			"label": _("Serial and Batch Bundle"),
			"options": "Serial and Batch Bundle",
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


@frappe.whitelist()
def create_reposting_entries(rows, item_code=None, warehouse=None):
	if isinstance(rows, str):
		rows = parse_json(rows)

	entries = []
	for row in rows:
		row = frappe._dict(row)

		try:
			doc = frappe.get_doc(
				{
					"doctype": "Repost Item Valuation",
					"based_on": "Item and Warehouse",
					"status": "Queued",
					"item_code": item_code or row.item_code,
					"warehouse": warehouse or row.warehouse,
					"posting_date": row.posting_date,
					"posting_time": row.posting_time,
					"allow_nagative_stock": 1,
				}
			).submit()

			entries.append(get_link_to_form("Repost Item Valuation", doc.name))
		except frappe.DuplicateEntryError:
			continue

	if entries:
		entries = ", ".join(entries)
		frappe.msgprint(_("Reposting entries created: {0}").format(entries))
