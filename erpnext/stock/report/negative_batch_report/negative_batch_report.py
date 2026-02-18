# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import add_to_date, flt, today

from erpnext.stock.report.stock_ledger.stock_ledger import execute as stock_ledger_execute


def execute(filters: dict | None = None):
	"""Return columns and data for the report.

	This is the main entry point for the report. It accepts the filters as a
	dictionary and should return columns and data. It is called by the framework
	every time the report is refreshed or a filter is updated.
	"""
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns() -> list[dict]:
	return [
		{
			"label": _("Posting Datetime"),
			"fieldname": "posting_date",
			"fieldtype": "Datetime",
			"width": 160,
		},
		{
			"label": _("Batch No"),
			"fieldname": "batch_no",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 120,
		},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150,
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 160,
		},
		{
			"label": _("Previous Qty"),
			"fieldname": "previous_qty",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": _("Transaction Qty"),
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": _("Qty After Transaction"),
			"fieldname": "qty_after_transaction",
			"fieldtype": "Float",
			"width": 180,
		},
		{
			"label": _("Document Type"),
			"fieldname": "voucher_type",
			"fieldtype": "Data",
			"width": 130,
		},
		{
			"label": _("Document No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 130,
		},
	]


def get_data(filters) -> list[dict]:
	batches = get_batches(filters)
	companies = get_companies(filters)
	batch_negative_data = []

	flt_precision = frappe.db.get_default("float_precision") or 2
	for company in companies:
		for batch in batches:
			_c, data = stock_ledger_execute(
				frappe._dict(
					{
						"company": company,
						"batch_no": batch,
						"from_date": add_to_date(today(), years=-12),
						"to_date": today(),
						"segregate_serial_batch_bundle": 1,
						"warehouse": filters.get("warehouse"),
						"valuation_field_type": "Currency",
					}
				)
			)

			previous_qty = 0
			for row in data:
				if flt(row.get("qty_after_transaction"), flt_precision) < 0:
					batch_negative_data.append(
						{
							"posting_date": row.get("date"),
							"batch_no": row.get("batch_no"),
							"item_code": row.get("item_code"),
							"item_name": row.get("item_name"),
							"warehouse": row.get("warehouse"),
							"actual_qty": row.get("actual_qty"),
							"qty_after_transaction": row.get("qty_after_transaction"),
							"previous_qty": previous_qty,
							"voucher_type": row.get("voucher_type"),
							"voucher_no": row.get("voucher_no"),
						}
					)

				previous_qty = row.get("qty_after_transaction")

	return batch_negative_data


def get_batches(filters):
	batch_filters = {}
	if filters.get("item_code"):
		batch_filters["item"] = filters["item_code"]

	return frappe.get_all("Batch", pluck="name", filters=batch_filters)


def get_companies(filters):
	company_filters = {}
	if filters.get("company"):
		company_filters["name"] = filters["company"]

	return frappe.get_all("Company", pluck="name", filters=company_filters)
