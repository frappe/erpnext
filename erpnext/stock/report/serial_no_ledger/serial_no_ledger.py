# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import copy

import frappe
from frappe import _

from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos as get_serial_nos_from_sle
from erpnext.stock.stock_ledger import get_stock_ledger_entries

BUYING_VOUCHER_TYPES = ["Purchase Invoice", "Purchase Receipt", "Subcontracting Receipt"]
SELLING_VOUCHER_TYPES = ["Sales Invoice", "Delivery Note"]


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{"label": _("Posting Date"), "fieldtype": "Date", "fieldname": "posting_date", "width": 120},
		{"label": _("Posting Time"), "fieldtype": "Time", "fieldname": "posting_time", "width": 90},
		{
			"label": _("Voucher Type"),
			"fieldtype": "Data",
			"fieldname": "voucher_type",
			"width": 160,
		},
		{
			"label": _("Voucher No"),
			"fieldtype": "Dynamic Link",
			"fieldname": "voucher_no",
			"options": "voucher_type",
			"width": 230,
		},
		{
			"label": _("Company"),
			"fieldtype": "Link",
			"fieldname": "company",
			"options": "Company",
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
			"label": _("Status"),
			"fieldtype": "Data",
			"fieldname": "status",
			"width": 90,
		},
		{
			"label": _("Serial No"),
			"fieldtype": "Link",
			"fieldname": "serial_no",
			"options": "Serial No",
			"width": 130,
		},
		{
			"label": _("Valuation Rate"),
			"fieldtype": "Float",
			"fieldname": "valuation_rate",
			"width": 130,
		},
		{
			"label": _("Qty"),
			"fieldtype": "Float",
			"fieldname": "qty",
			"width": 150,
		},
		{
			"label": _("Party Type"),
			"fieldtype": "Data",
			"fieldname": "party_type",
			"width": 90,
		},
		{
			"label": _("Party"),
			"fieldtype": "Dynamic Link",
			"fieldname": "party",
			"options": "party_type",
			"width": 120,
		},
	]

	return columns


def get_data(filters):
	stock_ledgers = get_stock_ledger_entries(filters, "<=", order="asc", check_serial_no=False)

	if not stock_ledgers:
		return []

	data = []
	serial_bundle_ids = [d.serial_and_batch_bundle for d in stock_ledgers if d.serial_and_batch_bundle]

	bundle_wise_serial_nos = get_serial_nos(filters, serial_bundle_ids)

	for row in stock_ledgers:
		args = frappe._dict(
			{
				"posting_date": row.posting_date,
				"posting_time": row.posting_time,
				"voucher_type": row.voucher_type,
				"voucher_no": row.voucher_no,
				"status": "Active" if row.actual_qty > 0 else "Delivered",
				"company": row.company,
				"warehouse": row.warehouse,
				"qty": 1 if row.actual_qty > 0 else -1,
			}
		)

		# get party details depending on the voucher type
		party_field = (
			"supplier"
			if row.voucher_type in BUYING_VOUCHER_TYPES
			else ("customer" if row.voucher_type in SELLING_VOUCHER_TYPES else None)
		)
		args.party_type = party_field.title() if party_field else None
		args.party = (
			frappe.db.get_value(row.voucher_type, row.voucher_no, party_field) if party_field else None
		)

		serial_nos = []
		if row.serial_no:
			parsed_serial_nos = get_serial_nos_from_sle(row.serial_no)
			for serial_no in parsed_serial_nos:
				if filters.get("serial_no") and filters.get("serial_no") != serial_no:
					continue

				serial_nos.append(
					{
						"serial_no": serial_no,
						"valuation_rate": abs(row.stock_value_difference / row.actual_qty),
					}
				)

		if row.serial_and_batch_bundle:
			serial_nos.extend(bundle_wise_serial_nos.get(row.serial_and_batch_bundle, []))

		for index, bundle_data in enumerate(serial_nos):
			if index == 0:
				new_args = copy.deepcopy(args)
				new_args.serial_no = bundle_data.get("serial_no")
				new_args.valuation_rate = bundle_data.get("valuation_rate")
				data.append(new_args)
			else:
				data.append(
					{
						"serial_no": bundle_data.get("serial_no"),
						"valuation_rate": bundle_data.get("valuation_rate"),
					}
				)

	return data


def get_serial_nos(filters, serial_bundle_ids):
	bundle_wise_serial_nos = {}
	bundle_filters = {"parent": ["in", serial_bundle_ids]}
	if filters.get("serial_no"):
		bundle_filters["serial_no"] = filters.get("serial_no")

	for d in frappe.get_all(
		"Serial and Batch Entry",
		fields=["serial_no", "parent", "stock_value_difference as valuation_rate"],
		filters=bundle_filters,
		order_by="idx asc",
	):
		bundle_wise_serial_nos.setdefault(d.parent, []).append(
			{
				"serial_no": d.serial_no,
				"valuation_rate": abs(d.valuation_rate),
			}
		)

	return bundle_wise_serial_nos
