# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.stock.stock_ledger import get_stock_ledger_entries


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	columns = [
		{"label": _("Posting Date"), "fieldtype": "Date", "fieldname": "posting_date"},
		{"label": _("Posting Time"), "fieldtype": "Time", "fieldname": "posting_time"},
		{
			"label": _("Voucher Type"),
			"fieldtype": "Link",
			"fieldname": "voucher_type",
			"options": "DocType",
			"width": 160,
		},
		{
			"label": _("Voucher No"),
			"fieldtype": "Dynamic Link",
			"fieldname": "voucher_no",
			"options": "voucher_type",
			"width": 180,
		},
		{
			"label": _("Company"),
			"fieldtype": "Link",
			"fieldname": "company",
			"options": "Company",
			"width": 150,
		},
		{
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"fieldname": "warehouse",
			"options": "Warehouse",
			"width": 150,
		},
		{
			"label": _("Serial No"),
			"fieldtype": "Link",
			"fieldname": "serial_no",
			"options": "Serial No",
			"width": 150,
		},
		{
			"label": _("Valuation Rate"),
			"fieldtype": "Float",
			"fieldname": "valuation_rate",
			"width": 150,
		},
	]

	return columns


def get_data(filters):
	stock_ledgers = get_stock_ledger_entries(filters, "<=", order="asc", check_serial_no=False)

	if not stock_ledgers:
		return []

	data = []
	serial_bundle_ids = [
		d.serial_and_batch_bundle for d in stock_ledgers if d.serial_and_batch_bundle
	]

	bundle_wise_serial_nos = get_serial_nos(filters, serial_bundle_ids)

	for row in stock_ledgers:
		args = frappe._dict(
			{
				"posting_date": row.posting_date,
				"posting_time": row.posting_time,
				"voucher_type": row.voucher_type,
				"voucher_no": row.voucher_no,
				"company": row.company,
				"warehouse": row.warehouse,
			}
		)

		serial_nos = bundle_wise_serial_nos.get(row.serial_and_batch_bundle, [])

		for index, bundle_data in enumerate(serial_nos):
			if index == 0:
				args.serial_no = bundle_data.get("serial_no")
				args.valuation_rate = bundle_data.get("valuation_rate")
				data.append(args)
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
