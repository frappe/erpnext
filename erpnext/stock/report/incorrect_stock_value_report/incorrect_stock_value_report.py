# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Field
from frappe.query_builder.functions import CombineDatetime, Min
from frappe.utils import add_days, getdate, today

import erpnext
from erpnext.accounts.utils import get_stock_and_account_balance
from erpnext.stock.utils import get_stock_value_on


def execute(filters=None):
	if not erpnext.is_perpetual_inventory_enabled(filters.company):
		frappe.throw(
			_("Perpetual inventory required for the company {0} to view this report.").format(
				filters.company
			)
		)

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

	while getdate(date) < getdate(today()):
		account_bal, stock_bal, warehouse_list = get_stock_and_account_balance(
			posting_date=date, company=filters.company, account=filters.account
		)

		if abs(account_bal - stock_bal) > 0.1:
			return date

		date = add_days(date, 1)


def get_data(report_filters):
	from_date = get_unsync_date(report_filters)

	if not from_date:
		return []

	result = []

	voucher_wise_dict = {}
	sle = frappe.qb.DocType("Stock Ledger Entry")
	data = (
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
		.where(
			(sle.posting_date == from_date)
			& (sle.company == report_filters.company)
			& (sle.is_cancelled == 0)
		)
		.orderby(CombineDatetime(sle.posting_date, sle.posting_time), sle.creation)
	).run(as_dict=True)

	for d in data:
		voucher_wise_dict.setdefault((d.item_code, d.warehouse), []).append(d)

	closing_date = add_days(from_date, -1)
	for key, stock_data in voucher_wise_dict.items():
		prev_stock_value = get_stock_value_on(
			posting_date=closing_date, item_code=key[0], warehouses=key[1]
		)
		for data in stock_data:
			expected_stock_value = prev_stock_value + data.stock_value_difference
			if abs(data.stock_value - expected_stock_value) > 0.1:
				data.difference_value = abs(data.stock_value - expected_stock_value)
				data.expected_stock_value = expected_stock_value
				result.append(data)

	return result


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
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": "110"},
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
