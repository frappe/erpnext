# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from typing import Any

import frappe
from frappe import _


def execute(filters=None):
	data = get_data(filters)
	columns = get_columns(filters, data)

	return columns, data


def get_data(filters):
	filter_conditions = get_filter_conditions(filters)

	data = frappe.get_all(
		"Stock Location Ledger",
		fields=[
			"voucher_type",
			"posting_datetime as posting_date",
			"name",
			"company",
			"voucher_no",
			"item_code",
			"serial_no",
			"batch_no",
			"warehouse",
			"incoming_rate",
			"stock_value_difference",
			"qty",
		],
		filters=filter_conditions,
		order_by="posting_datetime",
	)
	set_item_names(data)
	return data


def set_item_names(data):
	for row in data:
		row.item_name = frappe.get_cached_value("Item", row.item_code, "item_name")


def get_filter_conditions(filters):
	filter_conditions = [
		["Stock Location Ledger", "docstatus", "=", 1],
	]

	for field in ["voucher_type", "voucher_no", "item_code", "warehouse", "company", "serial_no", "batch_no"]:
		if filters.get(field):
			operator = "in" if field == "voucher_no" else "="
			filter_conditions.append(["Stock Location Ledger", field, operator, filters.get(field)])

	if filters.get("from_date") and filters.get("to_date"):
		filter_conditions.append(
			[
				"Stock Location Ledger",
				"posting_datetime",
				"between",
				[filters.get("from_date"), filters.get("to_date")],
			]
		)

	return filter_conditions


def get_columns(filters, data):
	columns = [
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 120,
		},
		{
			"label": _("Stock Location Ledger"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Stock Location Ledger",
			"width": 110,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
	]

	item_details = {}

	item_codes = []
	if filters.get("voucher_type"):
		item_codes = [d.item_code for d in data]

	if filters.get("item_code") or (item_codes and len(list(set(item_codes))) == 1):
		item_details = frappe.get_cached_value(
			"Item",
			filters.get("item_code") or item_codes[0],
			["has_serial_no", "has_batch_no"],
			as_dict=True,
		)

	if not filters.get("voucher_no"):
		columns.extend(
			[
				{
					"label": _("Voucher Type"),
					"fieldname": "voucher_type",
					"width": 120,
				},
				{
					"label": _("Voucher No"),
					"fieldname": "voucher_no",
					"fieldtype": "Dynamic Link",
					"options": "voucher_type",
					"width": 160,
				},
			]
		)

	if not filters.get("item_code"):
		columns.extend(
			[
				{
					"label": _("Item Code"),
					"fieldname": "item_code",
					"fieldtype": "Link",
					"options": "Item",
					"width": 120,
				},
				{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 120},
			]
		)

	if not filters.get("warehouse"):
		columns.append(
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 120,
			}
		)

	if not item_details or item_details.get("has_serial_no"):
		columns.append(
			{
				"label": _("Serial No"),
				"fieldname": "serial_no",
				"fieldtype": "Link",
				"width": 120,
				"options": "Serial No",
			}
		)

	if not item_details or item_details.get("has_batch_no"):
		columns.extend(
			[
				{"label": _("Batch No"), "fieldname": "batch_no", "fieldtype": "Data", "width": 120},
				{"label": _("Batch Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 120},
			]
		)

	columns.extend(
		[
			{"label": _("Incoming Rate"), "fieldname": "incoming_rate", "fieldtype": "Float", "width": 120},
			{
				"label": _("Change in Stock Value"),
				"fieldname": "stock_value_difference",
				"fieldtype": "Float",
				"width": 120,
			},
		]
	)

	return columns


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_voucher_type(doctype: Any, txt: str, searchfield: Any, start: int, page_len: int, filters: dict):
	query_filters = {}
	if txt:
		query_filters["voucher_type"] = ["like", f"%{txt}%"]

	return frappe.get_all(
		"Stock Location Ledger",
		filters=query_filters,
		fields=["voucher_type"],
		as_list=True,
		distinct=True,
	)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_serial_nos(doctype: Any, txt: str, searchfield: Any, start: int, page_len: int, filters: dict):
	query_filters = {}

	if txt:
		query_filters["serial_no"] = ["like", f"%{txt}%"]

	if filters.get("voucher_no"):
		query_filters["voucher_no"] = ("in", filters.get("voucher_no"))
		query_filters["docstatus"] = 1
		if not txt:
			query_filters["serial_no"] = ("is", "set")

		return frappe.get_all(
			"Stock Location Ledger", filters=query_filters, fields=["serial_no"], as_list=True, distinct=True
		)

	else:
		query_filters["item_code"] = filters.get("item_code")
		return frappe.get_all("Serial No", filters=query_filters, as_list=True)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_batch_nos(doctype: Any, txt: str, searchfield: Any, start: int, page_len: int, filters: dict):
	query_filters = {}

	if filters.get("voucher_no") and txt:
		query_filters["batch_no"] = ["like", f"%{txt}%"]

	if filters.get("voucher_no"):
		query_filters["voucher_no"] = ("in", filters.get("voucher_no"))
		query_filters["docstatus"] = 1
		if not txt:
			query_filters["batch_no"] = ("is", "set")

		return frappe.get_all(
			"Stock Location Ledger", filters=query_filters, fields=["batch_no"], as_list=True, distinct=True
		)

	else:
		if txt:
			query_filters["name"] = ["like", f"%{txt}%"]

		query_filters["item"] = filters.get("item_code")
		return frappe.get_all("Batch", filters=query_filters, as_list=True)
