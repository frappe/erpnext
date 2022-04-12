# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
	data = get_stock_ledger_entries(filters)
	itewise_balance_qty = {}

	for row in data:
		key = (row.item_code, row.warehouse)
		itewise_balance_qty.setdefault(key, []).append(row)

	res = validate_data(itewise_balance_qty)
	return res


def validate_data(itewise_balance_qty):
	res = []
	for key, data in itewise_balance_qty.items():
		row = get_incorrect_data(data)
		if row:
			res.append(row)
			res.append({})

	return res


def get_incorrect_data(data):
	balance_qty = 0.0
	for row in data:
		balance_qty += row.actual_qty
		if row.voucher_type == "Stock Reconciliation" and not row.batch_no:
			balance_qty = flt(row.qty_after_transaction)

		row.expected_balance_qty = balance_qty
		if abs(flt(row.expected_balance_qty) - flt(row.qty_after_transaction)) > 0.5:
			row.differnce = abs(flt(row.expected_balance_qty) - flt(row.qty_after_transaction))
			return row


def get_stock_ledger_entries(report_filters):
	filters = {"is_cancelled": 0}
	fields = [
		"name",
		"voucher_type",
		"voucher_no",
		"item_code",
		"actual_qty",
		"posting_date",
		"posting_time",
		"company",
		"warehouse",
		"qty_after_transaction",
		"batch_no",
	]

	for field in ["warehouse", "item_code", "company"]:
		if report_filters.get(field):
			filters[field] = report_filters.get(field)

	return frappe.get_all(
		"Stock Ledger Entry",
		fields=fields,
		filters=filters,
		order_by="timestamp(posting_date, posting_time) asc, creation asc",
	)


def get_columns():
	return [
		{
			"label": _("Id"),
			"fieldtype": "Link",
			"fieldname": "name",
			"options": "Stock Ledger Entry",
			"width": 120,
		},
		{"label": _("Posting Date"), "fieldtype": "Date", "fieldname": "posting_date", "width": 110},
		{
			"label": _("Voucher Type"),
			"fieldtype": "Link",
			"fieldname": "voucher_type",
			"options": "DocType",
			"width": 120,
		},
		{
			"label": _("Voucher No"),
			"fieldtype": "Dynamic Link",
			"fieldname": "voucher_no",
			"options": "voucher_type",
			"width": 120,
		},
		{
			"label": _("Item Code"),
			"fieldtype": "Link",
			"fieldname": "item_code",
			"options": "Item",
			"width": 120,
		},
		{
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"fieldname": "warehouse",
			"options": "Warehouse",
			"width": 120,
		},
		{
			"label": _("Expected Balance Qty"),
			"fieldtype": "Float",
			"fieldname": "expected_balance_qty",
			"width": 170,
		},
		{
			"label": _("Actual Balance Qty"),
			"fieldtype": "Float",
			"fieldname": "qty_after_transaction",
			"width": 150,
		},
		{"label": _("Difference"), "fieldtype": "Float", "fieldname": "differnce", "width": 110},
	]
