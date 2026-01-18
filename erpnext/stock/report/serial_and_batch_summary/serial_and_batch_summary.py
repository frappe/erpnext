# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	data = get_data(filters)
	columns = get_columns(filters, data)

	return columns, data


def get_data(filters):
	filter_conditions = get_filter_conditions(filters)

	return frappe.get_all(
		"Serial and Batch Bundle",
		fields=[
			"`tabSerial and Batch Bundle`.`voucher_type`",
			"`tabSerial and Batch Bundle`.`posting_datetime` as posting_date",
			"`tabSerial and Batch Bundle`.`name`",
			"`tabSerial and Batch Bundle`.`company`",
			"`tabSerial and Batch Bundle`.`voucher_no`",
			"`tabSerial and Batch Bundle`.`item_code`",
			"`tabSerial and Batch Bundle`.`item_name`",
			"`tabSerial and Batch Entry`.`serial_no`",
			"`tabSerial and Batch Entry`.`batch_no`",
			"`tabSerial and Batch Entry`.`warehouse`",
			"`tabSerial and Batch Entry`.`incoming_rate`",
			"`tabSerial and Batch Entry`.`stock_value_difference`",
			"`tabSerial and Batch Entry`.`qty`",
		],
		filters=filter_conditions,
		order_by="posting_datetime",
	)


def get_filter_conditions(filters):
	filter_conditions = [
		["Serial and Batch Bundle", "docstatus", "=", 1],
		["Serial and Batch Bundle", "is_cancelled", "=", 0],
	]

	for field in ["voucher_type", "voucher_no", "item_code", "warehouse", "company"]:
		if filters.get(field):
			if field == "voucher_no":
				filter_conditions.append(["Serial and Batch Bundle", field, "in", filters.get(field)])
			else:
				filter_conditions.append(["Serial and Batch Bundle", field, "=", filters.get(field)])

	if filters.get("from_date") and filters.get("to_date"):
		filter_conditions.append(
			[
				"Serial and Batch Bundle",
				"posting_datetime",
				"between",
				[filters.get("from_date"), filters.get("to_date")],
			]
		)

	for field in ["serial_no", "batch_no"]:
		if filters.get(field):
			filter_conditions.append(["Serial and Batch Entry", field, "=", filters.get(field)])

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
			"label": _("Serial and Batch Bundle"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Serial and Batch Bundle",
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
def get_voucher_type(doctype, txt, searchfield, start, page_len, filters):
	child_doctypes = frappe.get_all(
		"DocField",
		filters={"fieldname": "serial_and_batch_bundle"},
		fields=["parent"],
		distinct=True,
	)

	query_filters = {"options": ["in", [d.parent for d in child_doctypes]]}
	if txt:
		query_filters["parent"] = ["like", f"%{txt}%"]

	return frappe.get_all("DocField", filters=query_filters, fields=["parent"], as_list=True, distinct=True)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_serial_nos(doctype, txt, searchfield, start, page_len, filters):
	query_filters = {}

	if txt:
		query_filters["serial_no"] = ["like", f"%{txt}%"]

	if filters.get("voucher_no"):
		serial_batch_bundle = frappe.get_cached_value(
			"Serial and Batch Bundle",
			{"voucher_no": ("in", filters.get("voucher_no")), "docstatus": 1, "is_cancelled": 0},
			"name",
		)

		query_filters["parent"] = serial_batch_bundle
		if not txt:
			query_filters["serial_no"] = ("is", "set")

		return frappe.get_all(
			"Serial and Batch Entry", filters=query_filters, fields=["serial_no"], as_list=True
		)

	else:
		query_filters["item_code"] = filters.get("item_code")
		return frappe.get_all("Serial No", filters=query_filters, as_list=True)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_batch_nos(doctype, txt, searchfield, start, page_len, filters):
	query_filters = {}

	if filters.get("voucher_no") and txt:
		query_filters["batch_no"] = ["like", f"%{txt}%"]

	if filters.get("voucher_no"):
		serial_batch_bundle = frappe.get_cached_value(
			"Serial and Batch Bundle",
			{"voucher_no": ("in", filters.get("voucher_no")), "docstatus": 1, "is_cancelled": 0},
			"name",
		)

		query_filters["parent"] = serial_batch_bundle
		if not txt:
			query_filters["batch_no"] = ("is", "set")

		return frappe.get_all(
			"Serial and Batch Entry", filters=query_filters, fields=["batch_no"], as_list=True
		)

	else:
		if txt:
			query_filters["name"] = ["like", f"%{txt}%"]

		query_filters["item"] = filters.get("item_code")
		return frappe.get_all("Batch", filters=query_filters, as_list=True)
