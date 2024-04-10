# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import get_link_to_form, parse_json

import erpnext
from erpnext.accounts.utils import get_currency_precision, get_stock_accounts
from erpnext.stock.doctype.warehouse.warehouse import get_warehouses_based_on_account


def execute(filters=None):
	if not erpnext.is_perpetual_inventory_enabled(filters.company):
		frappe.throw(
			_("Perpetual inventory required for the company {0} to view this report.").format(filters.company)
		)

	data = get_data(filters)
	columns = get_columns(filters)

	return columns, data


def get_data(report_filters):
	data = []

	filters = {
		"is_cancelled": 0,
		"company": report_filters.company,
		"posting_date": ("<=", report_filters.as_on_date),
	}

	get_currency_precision() or 2
	stock_ledger_entries = get_stock_ledger_data(report_filters, filters)
	voucher_wise_gl_data = get_gl_data(report_filters, filters)

	for d in stock_ledger_entries:
		key = (d.voucher_type, d.voucher_no)
		gl_data = voucher_wise_gl_data.get(key) or {}
		d.account_value = gl_data.get("account_value", 0)
		d.difference_value = d.stock_value - d.account_value
		if abs(d.difference_value) > 0.1:
			data.append(d)

	return data


def get_stock_ledger_data(report_filters, filters):
	if report_filters.account:
		warehouses = get_warehouses_based_on_account(report_filters.account, report_filters.company)

		filters["warehouse"] = ("in", warehouses)

	return frappe.get_all(
		"Stock Ledger Entry",
		filters=filters,
		fields=[
			"name",
			"voucher_type",
			"voucher_no",
			"sum(stock_value_difference) as stock_value",
			"posting_date",
			"posting_time",
		],
		group_by="voucher_type, voucher_no",
		order_by="posting_date ASC, posting_time ASC",
	)


def get_gl_data(report_filters, filters):
	if report_filters.account:
		stock_accounts = [report_filters.account]
	else:
		stock_accounts = get_stock_accounts(report_filters.company)

	filters.update({"account": ("in", stock_accounts)})

	if filters.get("warehouse"):
		del filters["warehouse"]

	gl_entries = frappe.get_all(
		"GL Entry",
		filters=filters,
		fields=[
			"name",
			"voucher_type",
			"voucher_no",
			"sum(debit_in_account_currency) - sum(credit_in_account_currency) as account_value",
		],
		group_by="voucher_type, voucher_no",
	)

	voucher_wise_gl_data = {}
	for d in gl_entries:
		key = (d.voucher_type, d.voucher_no)
		voucher_wise_gl_data[key] = d

	return voucher_wise_gl_data


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
		{"label": _("Stock Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": "120"},
		{
			"label": _("Account Value"),
			"fieldname": "account_value",
			"fieldtype": "Currency",
			"width": "120",
		},
		{
			"label": _("Difference Value"),
			"fieldname": "difference_value",
			"fieldtype": "Currency",
			"width": "120",
		},
	]


@frappe.whitelist()
def create_reposting_entries(rows, company):
	if isinstance(rows, str):
		rows = parse_json(rows)

	entries = []
	for row in rows:
		row = frappe._dict(row)

		try:
			doc = frappe.get_doc(
				{
					"doctype": "Repost Item Valuation",
					"based_on": "Transaction",
					"status": "Queued",
					"voucher_type": row.voucher_type,
					"voucher_no": row.voucher_no,
					"posting_date": row.posting_date,
					"company": company,
					"allow_nagative_stock": 1,
				}
			).submit()

			entries.append(get_link_to_form("Repost Item Valuation", doc.name))
		except frappe.DuplicateEntryError:
			pass

	if entries:
		entries = ", ".join(entries)
		frappe.msgprint(_("Reposting entries created: {0}").format(entries))
