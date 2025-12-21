# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	data = get_data(filters)
	columns = get_columns(filters, data)

	return columns, data


def get_data(filters):
	SerialBatchBundle = frappe.qb.DocType("Serial and Batch Bundle")
	SerialBatchEntry = frappe.qb.DocType("Serial and Batch Entry")
	Batch = frappe.qb.DocType("Batch")
	title_field = frappe.get_meta("Batch", cached=True).get_title_field()

	query = (
		frappe.qb.from_(SerialBatchBundle)
		.join(SerialBatchEntry)
		.on(SerialBatchBundle.name == SerialBatchEntry.parent)
		.left_join(Batch)
		.on(SerialBatchEntry.batch_no == Batch.name)
		.select(
			SerialBatchBundle.voucher_type,
			SerialBatchBundle.posting_datetime.as_("posting_date"),
			SerialBatchBundle.name,
			SerialBatchBundle.company,
			SerialBatchBundle.voucher_no,
			SerialBatchBundle.item_code,
			SerialBatchBundle.item_name,
			SerialBatchEntry.serial_no,
			SerialBatchEntry.batch_no.as_("batch_id"),
			SerialBatchEntry.warehouse,
			SerialBatchEntry.incoming_rate,
			SerialBatchEntry.stock_value_difference,
			SerialBatchEntry.qty,
			Batch[title_field].as_("batch_no"),
		)
	)

	query = apply_filters(query, filters)
	query = query.orderby(SerialBatchBundle.posting_datetime)

	return query.run(as_dict=True)


def apply_filters(query, filters):
	SerialBatchBundle = frappe.qb.DocType("Serial and Batch Bundle")
	SerialBatchEntry = frappe.qb.DocType("Serial and Batch Entry")

	query = query.where((SerialBatchBundle.docstatus == 1) & (SerialBatchBundle.is_cancelled == 0))

	for field in ["voucher_type", "voucher_no", "item_code", "warehouse", "company"]:
		if filters.get(field):
			if field == "voucher_no":
				query = query.where(SerialBatchBundle.voucher_no.isin(filters[field]))
			else:
				query = query.where(SerialBatchBundle[field] == filters[field])

	if filters.get("from_date") and filters.get("to_date"):
		query = query.where(
			SerialBatchBundle.posting_datetime.between(filters["from_date"], filters["to_date"])
		)

	for field in ["serial_no", "batch_no"]:
		if filters.get(field):
			query = query.where(SerialBatchEntry[field] == filters[field])

	return query


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
	Batch = frappe.qb.DocType("Batch")
	SerialBatchEntry = frappe.qb.DocType("Serial and Batch Entry")
	meta = frappe.get_meta(doctype, cached=True)
	title_field = meta.get_title_field()

	conditions = []

	if filters.get("voucher_no"):
		sbb_filters = {"voucher_no": ("in", filters.get("voucher_no")), "docstatus": 1, "is_cancelled": 0}

		if filters.get("item_code"):
			sbb_filters["item_code"] = filters.get("item_code")

		serial_batch_bundles = frappe.get_list("Serial and Batch Bundle", filters=sbb_filters, pluck="name")

		if not serial_batch_bundles:
			return []

		query = (
			frappe.qb.from_(SerialBatchEntry)
			.join(Batch)
			.on(Batch.name == SerialBatchEntry.batch_no)
			.select(SerialBatchEntry.batch_no, Batch[title_field])
			.distinct()
		)

		conditions.append(SerialBatchEntry.parent.isin(serial_batch_bundles))

		if filters.get("item_code"):
			conditions.append(Batch.item == filters.get("item_code"))

		if txt:
			conditions.append(SerialBatchEntry.batch_no.like(f"%{txt}%"))
		else:
			conditions.append(SerialBatchEntry.batch_no.isnotnull())

		for condition in conditions:
			query = query.where(condition)

		return query.run(as_list=True)

	else:
		if not filters.get("item_code"):
			return []

		query = frappe.qb.from_(Batch).select(Batch.name, Batch[title_field])

		conditions.append(Batch.item == filters.get("item_code"))

		if txt:
			conditions.append(Batch.name.like(f"%{txt}%"))

		for condition in conditions:
			query = query.where(condition)

		return query.run(as_list=True)
