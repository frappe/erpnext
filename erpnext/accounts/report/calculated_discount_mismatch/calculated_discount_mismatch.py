# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.query_builder import Order, Tuple
from frappe.utils.formatters import format_value

AFFECTED_DOCTYPES = frozenset(
	(
		"POS Invoice",
		"Purchase Invoice",
		"Sales Invoice",
		"Purchase Order",
		"Supplier Quotation",
		"Quotation",
		"Sales Order",
		"Delivery Note",
		"Purchase Receipt",
	)
)
LAST_MODIFIED_DATE_THRESHOLD = "2025-05-30"


def execute(filters=None):
	columns = get_columns()
	data = get_data()

	return columns, data


def get_columns():
	return [
		{
			"fieldname": "doctype",
			"label": _("Transaction Type"),
			"fieldtype": "Link",
			"options": "DocType",
			"width": 120,
		},
		{
			"fieldname": "docname",
			"label": _("Transaction Name"),
			"fieldtype": "Dynamic Link",
			"options": "doctype",
			"width": 150,
		},
		{
			"fieldname": "actual_discount_percentage",
			"label": _("Discount Percentage in Transaction"),
			"fieldtype": "Percent",
			"width": 180,
		},
		{
			"fieldname": "actual_discount_amount",
			"label": _("Discount Amount in Transaction"),
			"fieldtype": "Currency",
			"width": 180,
		},
		{
			"fieldname": "suspected_discount_amount",
			"label": _("Suspected Discount Amount"),
			"fieldtype": "Currency",
			"width": 180,
		},
	]


def get_data():
	transactions_with_discount_percentage = {}

	for doctype in AFFECTED_DOCTYPES:
		transactions = get_transactions_with_discount_percentage(doctype)

		for transaction in transactions:
			transactions_with_discount_percentage[(doctype, transaction.name)] = transaction

	if not transactions_with_discount_percentage:
		return []

	VERSION = frappe.qb.DocType("Version")

	versions = (
		frappe.qb.from_(VERSION)
		.select(VERSION.ref_doctype, VERSION.docname, VERSION.data)
		.where(VERSION.creation > LAST_MODIFIED_DATE_THRESHOLD)
		.where(Tuple(VERSION.ref_doctype, VERSION.docname).isin(list(transactions_with_discount_percentage)))
		.where(
			VERSION.data.like('%"discount\\_amount"%')
			| VERSION.data.like('%"additional\\_discount\\_percentage"%')
		)
		.orderby(VERSION.creation, order=Order.desc)
		.run(as_dict=True)
	)

	if not versions:
		return []

	version_map = {}
	for version in versions:
		key = (version.ref_doctype, version.docname)
		if key not in version_map:
			version_map[key] = []

		version_map[key].append(version.data)

	data = []
	discount_amount_field_map = {
		doctype: frappe.get_meta(doctype).get_field("discount_amount") for doctype in AFFECTED_DOCTYPES
	}
	for doc, versions in version_map.items():
		for version_data in versions:
			if '"additional_discount_percentage"' in version_data:
				# don't consider doc if additional_discount_percentage is changed in newest version
				break

			version_data = json.loads(version_data)
			changed_values = version_data.get("changed")
			if not changed_values:
				continue

			discount_values = next((row for row in changed_values if row[0] == "discount_amount"), None)
			if not discount_values:
				continue

			old = discount_values[1]
			new = discount_values[2]
			doctype = doc[0]
			doc_values = transactions_with_discount_percentage.get(doc)
			formatted_discount_amount = format_value(
				doc_values.discount_amount,
				df=discount_amount_field_map[doctype],
				currency=doc_values.currency,
			)

			if new != formatted_discount_amount:
				# if the discount amount in the version is not equal to the current value, skip
				break

			data.append(
				{
					"doctype": doctype,
					"docname": doc_values.name,
					"actual_discount_percentage": doc_values.additional_discount_percentage,
					"actual_discount_amount": new,
					"suspected_discount_amount": old,
				}
			)
			break

	return data


def get_transactions_with_discount_percentage(doctype):
	transactions = frappe.get_all(
		doctype,
		fields=[
			"name",
			"currency",
			"additional_discount_percentage",
			"discount_amount",
		],
		filters={
			"docstatus": ["<", 2],
			"additional_discount_percentage": [">", 0],
			"discount_amount": ["!=", 0],
			"modified": [">", LAST_MODIFIED_DATE_THRESHOLD],
		},
	)

	return transactions
