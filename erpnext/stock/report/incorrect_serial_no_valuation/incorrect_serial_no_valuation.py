# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import copy

import frappe
from frappe import _

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos


def execute(filters=None):
	columns, data = [], []
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
	data = get_stock_ledger_entries(filters)
	serial_nos_data = prepare_serial_nos(data)
	data = get_incorrect_serial_nos(serial_nos_data)

	return data


def prepare_serial_nos(data):
	serial_no_wise_data = {}
	for row in data:
		if not row.serial_nos:
			continue

		for serial_no in get_serial_nos(row.serial_nos):
			sle = copy.deepcopy(row)
			sle.serial_no = serial_no
			sle.qty = 1 if sle.actual_qty > 0 else -1
			sle.valuation_rate = sle.valuation_rate if sle.actual_qty > 0 else sle.valuation_rate * -1
			serial_no_wise_data.setdefault(serial_no, []).append(sle)

	return serial_no_wise_data


def get_incorrect_serial_nos(serial_nos_data):
	result = []

	total_value = frappe._dict(
		{"qty": 0, "valuation_rate": 0, "serial_no": frappe.bold(_("Balance"))}
	)

	for serial_no, data in serial_nos_data.items():
		total_dict = frappe._dict({"qty": 0, "valuation_rate": 0, "serial_no": frappe.bold(_("Total"))})

		if check_incorrect_serial_data(data, total_dict):
			result.extend(data)

			total_value.qty += total_dict.qty
			total_value.valuation_rate += total_dict.valuation_rate

			result.append(total_dict)
			result.append({})

	result.append(total_value)

	return result


def check_incorrect_serial_data(data, total_dict):
	incorrect_data = False
	for row in data:
		total_dict.qty += row.qty
		total_dict.valuation_rate += row.valuation_rate

		if (total_dict.qty == 0 and abs(total_dict.valuation_rate) > 0) or total_dict.qty < 0:
			incorrect_data = True

	return incorrect_data


def get_stock_ledger_entries(report_filters):
	fields = [
		"name",
		"voucher_type",
		"voucher_no",
		"item_code",
		"serial_no as serial_nos",
		"actual_qty",
		"posting_date",
		"posting_time",
		"company",
		"warehouse",
		"(stock_value_difference / actual_qty) as valuation_rate",
	]

	filters = {"serial_no": ("is", "set"), "is_cancelled": 0}

	if report_filters.get("item_code"):
		filters["item_code"] = report_filters.get("item_code")

	if report_filters.get("from_date") and report_filters.get("to_date"):
		filters["posting_date"] = (
			"between",
			[report_filters.get("from_date"), report_filters.get("to_date")],
		)

	return frappe.get_all(
		"Stock Ledger Entry",
		fields=fields,
		filters=filters,
		order_by="timestamp(posting_date, posting_time) asc, creation asc",
	)


def get_columns():
	return [
		{
			"label": _("Company"),
			"fieldtype": "Link",
			"fieldname": "company",
			"options": "Company",
			"width": 120,
		},
		{
			"label": _("Id"),
			"fieldtype": "Link",
			"fieldname": "name",
			"options": "Stock Ledger Entry",
			"width": 120,
		},
		{"label": _("Posting Date"), "fieldtype": "Date", "fieldname": "posting_date", "width": 90},
		{"label": _("Posting Time"), "fieldtype": "Time", "fieldname": "posting_time", "width": 90},
		{
			"label": _("Voucher Type"),
			"fieldtype": "Link",
			"fieldname": "voucher_type",
			"options": "DocType",
			"width": 100,
		},
		{
			"label": _("Voucher No"),
			"fieldtype": "Dynamic Link",
			"fieldname": "voucher_no",
			"options": "voucher_type",
			"width": 110,
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
			"label": _("Serial No"),
			"fieldtype": "Link",
			"fieldname": "serial_no",
			"options": "Serial No",
			"width": 100,
		},
		{"label": _("Qty"), "fieldtype": "Float", "fieldname": "qty", "width": 80},
		{
			"label": _("Valuation Rate (In / Out)"),
			"fieldtype": "Currency",
			"fieldname": "valuation_rate",
			"width": 110,
		},
	]
