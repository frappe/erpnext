# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import erpnext
from frappe import _
from six import iteritems
from frappe.utils import add_days, today, getdate
from erpnext.stock.utils import get_stock_value_on
from erpnext.accounts.utils import get_stock_and_account_balance

def execute(filters=None):
	if not erpnext.is_perpetual_inventory_enabled(filters.company):
		frappe.throw(_("Perpetual inventory required for the company {0} to view this report.")
			.format(filters.company))

	data = get_data(filters)
	columns = get_columns(filters)

	return columns, data

def get_unsync_date(filters):
	date = filters.from_date
	if not date:
		date = frappe.db.sql(""" SELECT min(posting_date) from `tabStock Ledger Entry`""")
		date = date[0][0]

	if not date:
		return

	while getdate(date) < getdate(today()):
		account_bal, stock_bal, warehouse_list = get_stock_and_account_balance(posting_date=date,
			company=filters.company, account = filters.account)

		if abs(account_bal - stock_bal) > 0.1:
			return date

		date = add_days(date, 1)

def get_data(report_filters):
	from_date = get_unsync_date(report_filters)

	if not from_date:
		return []

	result = []

	voucher_wise_dict = {}
	data = frappe.db.sql('''
			SELECT
				name, posting_date, posting_time, voucher_type, voucher_no,
				stock_value_difference, stock_value, warehouse, item_code
			FROM
				`tabStock Ledger Entry`
			WHERE
				posting_date
				= %s and company = %s
				and is_cancelled = 0
			ORDER BY timestamp(posting_date, posting_time) asc, creation asc
		''', (from_date, report_filters.company), as_dict=1)

	for d in data:
		voucher_wise_dict.setdefault((d.item_code, d.warehouse), []).append(d)

	closing_date = add_days(from_date, -1)
	for key, stock_data in iteritems(voucher_wise_dict):
		prev_stock_value = get_stock_value_on(posting_date = closing_date, item_code=key[0], warehouse =key[1])
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
			"width": "80"
		},
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Date"
		},
		{
			"label": _("Posting Time"),
			"fieldname": "posting_time",
			"fieldtype": "Time"
		},
		{
			"label": _("Voucher Type"),
			"fieldname": "voucher_type",
			"width": "110"
		},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": "110"
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": "110"
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": "110"
		},
		{
			"label": _("Expected Stock Value"),
			"fieldname": "expected_stock_value",
			"fieldtype": "Currency",
			"width": "150"
		},
		{
			"label": _("Stock Value"),
			"fieldname": "stock_value",
			"fieldtype": "Currency",
			"width": "120"
		},
		{
			"label": _("Difference Value"),
			"fieldname": "difference_value",
			"fieldtype": "Currency",
			"width": "150"
		}
	]