# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def execute(filters=None):
	columns, data = [], []

	if not filters:
		return columns, data

	columns = get_columns()
	data = get_data(filters.get("link_doctype"), filters.get("link_name"))

	return columns, data


def get_data(link_doctype, link_name, data=None, unique_items=None):
	if not unique_items:
		unique_items = []

	if not data:
		data = []

	source_doctype = source_docname = None

	if link_doctype == "Serial No":
		source_doctype, source_docname = frappe.db.get_value(
			link_doctype, link_name, ["purchase_document_type", "purchase_document_no"])
	elif link_doctype == "Batch":
		source_doctype, source_docname = frappe.db.get_value(
			link_doctype, link_name, ["reference_doctype", "reference_name"])

	if not source_doctype and not source_docname:
		return data

	source_doc = frappe.get_doc(source_doctype, source_docname)
	supplier = source_doc.supplier if source_doc.doctype == "Purchase Receipt" else ""

	for item in source_doc.get("items", []):
		if source_doc.doctype == "Purchase Receipt":
			warehouse = item.warehouse
		elif source_doc.doctype == "Stock Entry":
			warehouse = item.t_warehouse

		if item.get("t_warehouse") or item.get("warehouse"):
			unique_items.append(link_name)
			data.append({
				"item_code": item.item_code,
				"serial_no": link_name if item.serial_no else "",
				"batch_no": link_name if item.batch_no else "",
				"qty": item.qty,
				"stock_uom": item.stock_uom,
				"warehouse": warehouse,
				"date": source_doc.posting_date,
				"supplier": supplier,
				"activity_doctype": source_doc.doctype,
				"activity_document": source_doc.name
			})
		elif item.get("s_warehouse"):
			# Recursively loop through input items to find serial nos / batches
			# and track them back to their source
			if item.serial_no and item.serial_no not in unique_items:
				data = get_data("Serial No", item.serial_no, data, unique_items)
			elif item.batch_no and item.batch_no not in unique_items:
				data = get_data("Batch", item.batch_no, data, unique_items)

	return data


def get_columns():
	return [
		{
			"fieldname": "item_code",
			"label": _("Item Code"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 90
		},
		{
			"fieldname": "batch_no",
			"label": _("Batch No"),
			"fieldtype": "Link",
			"options": "Batch",
			"width": 100
		},
		{
			"fieldname": "serial_no",
			"label": _("Serial No"),
			"fieldtype": "Serial",
			"options": "Data",
			"width": 110
		},
		{
			"fieldname": "qty",
			"label": _("Quantity"),
			"fieldtype": "Float",
			"width": 90
		},
		{
			"fieldname": "stock_uom",
			"label": _("Unit"),
			"fieldtype": "Link",
			"options": "UOM",
			"width": 90
		},
		{
			"fieldname": "warehouse",
			"label": _("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 150
		},
		{
			"fieldname": "date",
			"label": _("Posting Date"),
			"fieldtype": "Date",
			"width": 90
		},
		{
			"fieldname": "activity_doctype",
			"label": _("Activity Type"),
			"fieldtype": "Link",
			"options": "DocType",
			"width": 90
		},
		{
			"fieldname": "activity_document",
			"label": _("Activity Document"),
			"fieldtype": "Dynamic Link",
			"options": "activity_doctype",
			"width": 150
		},
		{
			"fieldname": "supplier",
			"label": _("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 100
		}
	]
