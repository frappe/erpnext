# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Field
from frappe.query_builder.functions import Min, Sum
from frappe.utils import add_days, flt, getdate, today

import erpnext
from erpnext.accounts.utils import get_stock_and_account_balance


def execute(filters=None):
	if not erpnext.is_perpetual_inventory_enabled(filters.company):
		frappe.throw(
			_("Perpetual inventory required for the company {0} to view this report.").format(filters.company)
		)

	if not filters.get("account"):
		frappe.throw(_("Select the stock Account to compare with the stock value"), frappe.MandatoryError)

	data = get_data(filters)
	columns = get_columns(filters)

	return columns, data


def get_unsync_date(filters):
	date = filters.from_date
	if not date:
		date = (frappe.qb.from_("Stock Ledger Entry").select(Min(Field("posting_date")))).run()
		date = date[0][0]

	if not date:
		return

	while getdate(date) <= getdate(today()):
		account_bal, stock_bal, warehouse_list = get_stock_and_account_balance(
			posting_date=date, company=filters.company, account=filters.account
		)

		if abs(account_bal - stock_bal) > 0.1:
			return date

		date = add_days(date, 1)


def get_data(report_filters):
	from_date = report_filters.from_date or get_unsync_date(report_filters)
	if not from_date:
		return []

	entries = get_entries_from(from_date, report_filters.company)
	running_values = get_stock_values_before(from_date, report_filters.company, entries)

	result = []
	for data in entries:
		key = (data.item_code, data.warehouse)
		expected_stock_value = flt(running_values.get(key)) + flt(data.stock_value_difference)
		if abs(flt(data.stock_value) - expected_stock_value) > 0.1:
			data.difference_value = abs(flt(data.stock_value) - expected_stock_value)
			data.expected_stock_value = expected_stock_value
			result.append(data)

		running_values[key] = expected_stock_value

	return result


def get_entries_from(from_date, company):
	sle = frappe.qb.DocType("Stock Ledger Entry")
	return (
		frappe.qb.from_(sle)
		.select(
			sle.name,
			sle.posting_date,
			sle.posting_time,
			sle.voucher_type,
			sle.voucher_no,
			sle.stock_value_difference,
			sle.stock_value,
			sle.warehouse,
			sle.item_code,
		)
		.where((sle.posting_date >= from_date) & (sle.company == company) & (sle.is_cancelled == 0))
		.orderby(sle.posting_datetime, sle.creation)
	).run(as_dict=True)


def get_stock_values_before(from_date, company, entries):
	if not entries:
		return {}

	sle = frappe.qb.DocType("Stock Ledger Entry")
	rows = (
		frappe.qb.from_(sle)
		.select(sle.item_code, sle.warehouse, Sum(sle.stock_value_difference))
		.where(
			(sle.posting_date < from_date)
			& (sle.company == company)
			& (sle.is_cancelled == 0)
			& (sle.item_code.isin({row.item_code for row in entries}))
		)
		.groupby(sle.item_code, sle.warehouse)
	).run()

	return {(item_code, warehouse): flt(value) for item_code, warehouse, value in rows}


def get_columns(filters):
	return [
		{
			"label": _("Stock Ledger ID"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Stock Ledger Entry",
			"width": "80",
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date"},
		{"label": _("Posting Time"), "fieldname": "posting_time", "fieldtype": "Time"},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Link",
			"options": "DocType",
			"width": "110",
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": "110",
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": "110",
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": "110",
		},
		{
			"label": _("Expected Stock Value"),
			"fieldname": "expected_stock_value",
			"fieldtype": "Currency",
			"width": "150",
		},
		{"label": _("Stock Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": "120"},
		{
			"label": _("Difference Value"),
			"fieldname": "difference_value",
			"fieldtype": "Currency",
			"width": "150",
		},
	]
