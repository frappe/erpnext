# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import copy

import frappe
from frappe import _
from frappe.utils import getdate
from pypika import Criterion

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from erpnext.stock.report.utils import prepare_serial_batch_report


def execute(filters=None):
	columns, data = prepare_serial_batch_report(get_columns(), get_data(filters))
	for row in data:
		if row.total_label:
			row.serial_no_number = row.total_label
	return columns, data


def get_data(filters):
	data = get_stock_ledger_entries(filters)
	bundles = get_bundles(data)
	serial_nos_data = prepare_serial_nos(data, bundles)
	if filters.get("from_date") and serial_nos_data:
		serial_nos = list(serial_nos_data)
		opening_data = get_stock_ledger_entries(filters, serial_nos=serial_nos)
		opening_bundles = get_bundles(opening_data, serial_nos=serial_nos)
		opening_serials = prepare_serial_nos(opening_data, opening_bundles, serial_nos=serial_nos)
		for serial_no, rows in opening_serials.items():
			serial_nos_data[serial_no] = rows + serial_nos_data[serial_no]
	data = get_incorrect_serial_nos(serial_nos_data, filters.get("from_date"))

	return data


def get_bundles(data, serial_nos=None):
	bundles = [d.serial_and_batch_bundle for d in data if d.serial_and_batch_bundle]
	bundle_dict = frappe._dict()
	if not bundles:
		return bundle_dict

	filters = {"parent": ("in", bundles), "serial_no": ("is", "set")}
	if serial_nos is not None:
		filters["serial_no"] = ("in", serial_nos)
	serial_nos_data = frappe.get_all(
		"Serial and Batch Entry",
		fields=["parent", "serial_no", "incoming_rate", "qty"],
		filters=filters,
	)

	for entry in serial_nos_data:
		bundle_dict.setdefault(entry.parent, []).append(entry)

	return bundle_dict


def prepare_serial_nos(data, bundles, serial_nos=None):
	serial_no_wise_data = {}
	serial_nos = set(serial_nos) if serial_nos is not None else None
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
			if serial_nos is not None and serial_no not in serial_nos:
				continue
			sle = copy.deepcopy(row)
			sle.serial_no = serial_no
			sle.qty = 1 if sle.actual_qty > 0 else -1
			sle.valuation_rate = sle.valuation_rate if sle.actual_qty > 0 else sle.valuation_rate * -1
			serial_no_wise_data.setdefault(serial_no, []).append(sle)

	return serial_no_wise_data


def get_incorrect_serial_nos(serial_nos_data, from_date=None):
	result = []
	from_date = getdate(from_date) if from_date else None

	total_value = frappe._dict({"qty": 0, "valuation_rate": 0, "total_label": _("Balance")})

	for _serial_no, data in serial_nos_data.items():
		total_dict = frappe._dict({"qty": 0, "valuation_rate": 0, "total_label": _("Total")})

		if check_incorrect_serial_data(data, total_dict, from_date):
			result.extend(row for row in data if not from_date or getdate(row.posting_date) >= from_date)

			total_value.qty += total_dict.qty
			total_value.valuation_rate += total_dict.valuation_rate

			if total_dict.qty == 0 and abs(total_dict.valuation_rate) == 0:
				continue

			result.append(total_dict)
			result.append({})

	result.append(total_value)

	return result


def check_incorrect_serial_data(data, total_dict, from_date=None):
	incorrect_data = False
	for row in data:
		total_dict.qty += row.qty
		total_dict.valuation_rate += row.valuation_rate

		if from_date and getdate(row.posting_date) < from_date:
			continue

		if (total_dict.qty == 0 and abs(total_dict.valuation_rate) > 0) or total_dict.qty < 0:
			incorrect_data = True

	return incorrect_data


def get_stock_ledger_entries(report_filters, serial_nos=None):
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
		{"DIV": ["stock_value_difference", {"NULLIF": ["actual_qty", 0]}], "as": "valuation_rate"},
	]

	filters = {"is_cancelled": 0}
	or_filters = {"serial_no": ("is", "set"), "serial_and_batch_bundle": ("is", "set")}

	if report_filters.get("item_code"):
		filters["item_code"] = report_filters.get("item_code")

	if serial_nos is not None:
		if not serial_nos:
			return []
		filters["posting_date"] = ("<", report_filters.get("from_date"))
	elif report_filters.get("from_date") and report_filters.get("to_date"):
		filters["posting_date"] = ("between", [report_filters["from_date"], report_filters["to_date"]])
	elif report_filters.get("to_date"):
		filters["posting_date"] = ("<=", report_filters.get("to_date"))
	elif report_filters.get("from_date"):
		filters["posting_date"] = (">=", report_filters.get("from_date"))

	query = frappe.qb.get_query(
		"Stock Ledger Entry",
		fields=fields,
		filters=filters,
		or_filters=or_filters,
		order_by="posting_date asc, posting_time asc, creation asc",
	)
	if serial_nos is not None:
		sle = frappe.qb.DocType("Stock Ledger Entry")
		entry = frappe.qb.DocType("Serial and Batch Entry")
		bundles = frappe.qb.from_(entry).select(entry.parent).where(entry.serial_no.isin(serial_nos))
		conditions = [sle.serial_and_batch_bundle.isin(bundles)]
		for serial_no in serial_nos:
			serial_no = serial_no.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
			conditions.append(sle.serial_no.like(f"%{serial_no}%"))
		query = query.where(Criterion.any(conditions))

	return query.run(as_dict=True)


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
