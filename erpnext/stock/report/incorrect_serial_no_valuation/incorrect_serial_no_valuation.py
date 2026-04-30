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
	bundles = get_bundles(data)
	serial_nos_data = prepare_serial_nos(data, bundles)
	data = get_incorrect_serial_nos(serial_nos_data)

	return data


def get_bundles(data):
	bundles = [d.serial_and_batch_bundle for d in data if d.serial_and_batch_bundle]
	bundle_dict = frappe._dict()
	serial_nos_data = frappe.get_all(
		"Serial and Batch Entry",
		fields=["parent", "serial_no", "incoming_rate", "qty"],
		filters={"parent": ("in", bundles), "serial_no": ("is", "set")},
	)

	for entry in serial_nos_data:
		bundle_dict.setdefault(entry.parent, []).append(entry)

	return bundle_dict


def prepare_serial_nos(data, bundles):
	serial_no_wise_data = {}
	for row in data:
		if not row.serial_nos and not row.serial_and_batch_bundle:
			continue

		if row.serial_and_batch_bundle:
			for bundle in bundles.get(row.serial_and_batch_bundle, []):
				sle = copy.deepcopy(row)
				sle.serial_no = bundle.serial_no
				sle.qty = bundle.qty
				sle.valuation_rate = bundle.incoming_rate * (1 if sle.qty > 0 else -1)
				serial_no_wise_data.setdefault(bundle.serial_no, []).append(sle)
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

	total_value = frappe._dict({"qty": 0, "valuation_rate": 0, "serial_no": frappe.bold(_("Balance"))})

	for _serial_no, data in serial_nos_data.items():
		total_dict = frappe._dict({"qty": 0, "valuation_rate": 0, "serial_no": frappe.bold(_("Total"))})

		if check_incorrect_serial_data(data, total_dict):
			result.extend(data)

			total_value.qty += total_dict.qty
			total_value.valuation_rate += total_dict.valuation_rate

			if total_dict.qty == 0 and abs(total_dict.valuation_rate) == 0:
				continue

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
		"serial_and_batch_bundle",
		"actual_qty",
		"posting_date",
		"posting_time",
		"company",
		"warehouse",
		{"DIV": ["stock_value_difference", "actual_qty"], "as": "valuation_rate"},
	]

	filters = {"is_cancelled": 0}
	or_filters = {"serial_no": ("is", "set"), "serial_and_batch_bundle": ("is", "set")}

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
		or_filters=or_filters,
		order_by="posting_date asc, posting_time asc, creation asc",
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
