# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import IfNull, Sum


def execute(filters=None):
	data = get_data(filters) or []
	columns = get_columns()

	return columns, data


def get_data(report_filters):
	as_on_date = report_filters.get("posting_date")
	invoice = frappe.qb.DocType("Purchase Invoice")
	invoice_item = frappe.qb.DocType("Purchase Invoice Item")
	received = get_received_as_on(as_on_date)
	received_qty = IfNull(received.qty, 0)

	query = (
		frappe.qb.from_(invoice)
		.join(invoice_item)
		.on(invoice_item.parent == invoice.name)
		.left_join(received)
		.on(received.detail == invoice_item.name)
		.select(
			invoice.name,
			invoice.supplier,
			invoice.company,
			invoice.posting_date,
			invoice.currency,
			invoice_item.item_code,
			invoice_item.item_name,
			invoice_item.uom,
			invoice_item.qty,
			received_qty.as_("received_qty"),
			invoice_item.rate,
			invoice_item.amount,
		)
		.where(
			(invoice.company == report_filters.get("company"))
			& (invoice.posting_date <= as_on_date)
			& (invoice.docstatus == 1)
			& (invoice.update_stock == 0)
			& (invoice.is_opening != "Yes")
			& (invoice_item.qty > received_qty)
		)
		.orderby(invoice.posting_date)
		.orderby(invoice_item.idx)
	)

	if report_filters.get("purchase_invoice"):
		query = query.where(invoice.name == report_filters.get("purchase_invoice"))

	return query.run(as_dict=True)


def get_received_as_on(as_on_date):
	"""Qty received per invoice row by receipts posted on or before the date."""
	receipt = frappe.qb.DocType("Purchase Receipt")
	receipt_item = frappe.qb.DocType("Purchase Receipt Item")
	return (
		frappe.qb.from_(receipt_item)
		.join(receipt)
		.on(receipt.name == receipt_item.parent)
		.select(receipt_item.purchase_invoice_item.as_("detail"), Sum(receipt_item.received_qty).as_("qty"))
		.where((receipt.docstatus == 1) & (receipt.posting_date <= as_on_date))
		.where(receipt_item.purchase_invoice_item.isnotnull())
		.groupby(receipt_item.purchase_invoice_item)
	).as_("received")


def get_columns():
	return [
		{
			"label": _("Purchase Invoice"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Purchase Invoice",
			"width": 170,
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 120,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 100,
		},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 100},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 100},
		{"label": _("Invoiced Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 100},
		{"label": _("Received Qty"), "fieldname": "received_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 100},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 100},
	]
