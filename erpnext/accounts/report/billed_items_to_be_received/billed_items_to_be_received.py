# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder import Case
from frappe.query_builder.functions import IfNull, Sum
from pypika import analytics


def execute(filters=None):
	data = get_data(filters) or []
	columns = get_columns()

	return columns, data


def get_data(report_filters):
	as_on_date = report_filters.get("posting_date")
	invoice = frappe.qb.DocType("Purchase Invoice")
	invoice_item = frappe.qb.DocType("Purchase Invoice Item")
	item = frappe.qb.DocType("Item")
	received = get_received_as_on(as_on_date)
	returned = get_returned_as_on(as_on_date)
	invoice_first_returns = get_receipt_returns_as_on(
		as_on_date, "purchase_invoice_item", "invoice_first_returns"
	)
	receipt_first = get_receipt_first_received_as_on(as_on_date)
	received_qty = (
		IfNull(received.qty, 0)
		- IfNull(invoice_first_returns.qty, 0)
		+ IfNull(receipt_first.qty, 0)
		- IfNull(returned.stock_qty, 0)
	)
	returned_qty = IfNull(returned.qty, 0)

	query = (
		frappe.qb.from_(invoice)
		.join(invoice_item)
		.on(invoice_item.parent == invoice.name)
		.join(item)
		.on(item.name == invoice_item.item_code)
		.left_join(received)
		.on(received.detail == invoice_item.name)
		.left_join(returned)
		.on(returned.detail == invoice_item.name)
		.left_join(invoice_first_returns)
		.on(invoice_first_returns.detail == invoice_item.name)
		.left_join(receipt_first)
		.on(receipt_first.detail == invoice_item.name)
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
			returned_qty.as_("returned_qty"),
			invoice_item.rate,
			invoice_item.amount,
		)
		.where(
			(invoice.company == report_filters.get("company"))
			& (invoice.posting_date <= as_on_date)
			& (invoice.docstatus == 1)
			& (invoice.update_stock == 0)
			& (invoice.is_opening != "Yes")
			& (invoice.is_return == 0)
			& ((item.is_stock_item == 1) | (item.is_fixed_asset == 1))
			& (invoice_item.qty > received_qty + returned_qty)
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


def get_returned_as_on(as_on_date):
	"""Qty cancelled and stock sent back per invoice row by debit notes posted on or before the date."""
	debit_note = frappe.qb.DocType("Purchase Invoice")
	debit_note_item = frappe.qb.DocType("Purchase Invoice Item")
	stock_returned_qty = Case().when(debit_note.update_stock == 1, -debit_note_item.received_qty).else_(0)
	return (
		frappe.qb.from_(debit_note_item)
		.join(debit_note)
		.on(debit_note.name == debit_note_item.parent)
		.select(
			debit_note_item.purchase_invoice_item.as_("detail"),
			Sum(-debit_note_item.qty).as_("qty"),
			Sum(stock_returned_qty).as_("stock_qty"),
		)
		.where(
			(debit_note.docstatus == 1)
			& (debit_note.is_return == 1)
			& (debit_note.posting_date <= as_on_date)
		)
		.where(debit_note_item.purchase_invoice_item.isnotnull())
		.groupby(debit_note_item.purchase_invoice_item)
	).as_("returned")


def get_receipt_first_received_as_on(as_on_date):
	"""Qty received per invoice row made from a receipt, as on the date.

	A receipt row billed by several invoices has its net received qty (after returns) handed out
	to those invoice rows in posting order, so a return is counted only once across them.
	"""
	invoice = frappe.qb.DocType("Purchase Invoice")
	invoice_item = frappe.qb.DocType("Purchase Invoice Item")
	receipt = frappe.qb.DocType("Purchase Receipt")
	receipt_item = frappe.qb.DocType("Purchase Receipt Item")
	receipt_returns = get_receipt_returns_as_on(as_on_date, "name", "receipt_returns")
	billed_before = get_billed_through(invoice, invoice_item) - invoice_item.qty
	unallocated = receipt_item.received_qty - IfNull(receipt_returns.qty, 0) - billed_before
	allocated = (
		Case()
		.when(unallocated >= invoice_item.qty, invoice_item.qty)
		.when(unallocated > 0, unallocated)
		.else_(0)
	)
	return (
		frappe.qb.from_(invoice_item)
		.join(invoice)
		.on(invoice.name == invoice_item.parent)
		.join(receipt_item)
		.on(receipt_item.name == invoice_item.pr_detail)
		.join(receipt)
		.on(receipt.name == receipt_item.parent)
		.left_join(receipt_returns)
		.on(receipt_returns.detail == receipt_item.name)
		.select(invoice_item.name.as_("detail"), allocated.as_("qty"))
		.where((invoice.docstatus == 1) & (invoice.is_return == 0) & (invoice.posting_date <= as_on_date))
		.where((receipt.docstatus == 1) & (receipt.posting_date <= as_on_date))
	).as_("receipt_first")


def get_billed_through(invoice, invoice_item):
	"""Running total of qty billed against the receipt row, up to and including this invoice row."""
	return (
		analytics.Sum(invoice_item.qty)
		.over(invoice_item.pr_detail)
		.orderby(invoice.posting_date, invoice.name, invoice_item.idx)
		.rows(analytics.Preceding(), analytics.CURRENT_ROW)
	)


def get_receipt_returns_as_on(as_on_date, linked_by: str, alias: str):
	"""Qty sent back by receipt returns posted on or before the date.

	Return receipts link only to the original receipt row, so `linked_by` picks the invoice row
	(`purchase_invoice_item`) for receipts made from an invoice, or the receipt row itself (`name`)
	for invoices made from a receipt.
	"""
	return_receipt = frappe.qb.DocType("Purchase Receipt")
	return_item = frappe.qb.DocType("Purchase Receipt Item")
	original_item = frappe.qb.DocType("Purchase Receipt Item").as_("original_item")
	link_field = getattr(original_item, linked_by)
	return (
		frappe.qb.from_(return_item)
		.join(return_receipt)
		.on(return_receipt.name == return_item.parent)
		.join(original_item)
		.on(original_item.name == return_item.purchase_receipt_item)
		.select(link_field.as_("detail"), Sum(-return_item.received_qty).as_("qty"))
		.where(
			(return_receipt.docstatus == 1)
			& (return_receipt.is_return == 1)
			& (return_receipt.posting_date <= as_on_date)
		)
		.where(link_field.isnotnull())
		.groupby(link_field)
	).as_(alias)


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
		{"label": _("Returned Qty"), "fieldname": "returned_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 100},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 100},
	]
