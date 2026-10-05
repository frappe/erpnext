# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.meta import get_field_precision
from frappe.query_builder.functions import IfNull, Round, Sum

from erpnext import get_default_currency

BILLING_LINKS = {
	"Delivery Note": frappe._dict(
		invoice="Sales Invoice", invoice_link="dn_detail", return_link="dn_detail", returned_qty="stock_qty"
	),
	"Purchase Receipt": frappe._dict(
		invoice="Purchase Invoice",
		invoice_link="pr_detail",
		return_link="purchase_receipt_item",
		returned_qty="stock_qty",
		rejected_return_flag="return_qty_from_rejected_warehouse",
	),
}


def get_ordered_to_be_billed_data(args, filters=None):
	doctype, party = args.get("doctype"), args.get("party")
	child_tab = doctype + " Item"
	precision = (
		get_field_precision(
			frappe.get_meta(child_tab).get_field("billed_amt"), currency=get_default_currency()
		)
		or 2
	)

	links = BILLING_LINKS[doctype]
	as_on_date = filters.get("posting_date")
	later_billed = get_billed_after(links, as_on_date)
	returned = get_returned_as_on(doctype, child_tab, links, as_on_date)

	doctype = frappe.qb.DocType(doctype)
	child_doctype = frappe.qb.DocType(child_tab)
	item = frappe.qb.DocType("Item")

	docname = filters.get(args.get("reference_field"), None)
	project_field = get_project_field(doctype, child_doctype, party)
	billed_amount = (child_doctype.billed_amt - IfNull(later_billed.amount, 0)) * IfNull(
		doctype.conversion_rate, 1
	)
	returned_amount = child_doctype.base_rate * IfNull(returned.qty, 0) / child_doctype.conversion_factor

	query = (
		frappe.qb.from_(doctype)
		.inner_join(child_doctype)
		.on(doctype.name == child_doctype.parent)
		.join(item)
		.on(item.name == child_doctype.item_code)
		.left_join(later_billed)
		.on(later_billed.detail == child_doctype.name)
		.left_join(returned)
		.on(returned.detail == child_doctype.name)
		.select(
			doctype.name,
			doctype[args.get("date")].as_("date"),
			doctype[party],
			doctype[party + "_name"],
			child_doctype.item_code,
			child_doctype.base_amount.as_("amount"),
			billed_amount.as_("billed_amount"),
			returned_amount.as_("returned_amount"),
			(child_doctype.base_amount - billed_amount - returned_amount).as_("pending_amount"),
			child_doctype.item_name,
			child_doctype.description,
			project_field,
			doctype.company,
		)
		.where(
			(doctype.docstatus == 1)
			& (doctype.status != "Closed")
			& (doctype.company == filters.get("company"))
			& (doctype.posting_date <= as_on_date)
			& (child_doctype.amount > 0)
			& (item.is_stock_item == 1)
			& (child_doctype.base_amount - Round(billed_amount, precision) - returned_amount > 0)
		)
		.orderby(doctype[args.get("order")], order=args.get("order_by"))
	)

	if docname:
		query = query.where(doctype.name == docname)

	return query.run(as_dict=True)


def get_billed_after(links, as_on_date):
	"""Amount billed per row by invoices posted after the date, to take out of the stored billed_amt."""
	invoice = frappe.qb.DocType(links.invoice)
	invoice_item = frappe.qb.DocType(links.invoice + " Item")
	return (
		frappe.qb.from_(invoice_item)
		.inner_join(invoice)
		.on(invoice.name == invoice_item.parent)
		.select(invoice_item[links.invoice_link].as_("detail"), Sum(invoice_item.amount).as_("amount"))
		.where((invoice.docstatus == 1) & (invoice.posting_date > as_on_date))
		.where(invoice_item[links.invoice_link].isnotnull())
		.groupby(invoice_item[links.invoice_link])
	).as_("later_billed")


def get_returned_as_on(doctype, child_tab, links, as_on_date):
	"""Accepted qty returned per row by returns posted on or before the date."""
	parent = frappe.qb.DocType(doctype)
	child = frappe.qb.DocType(child_tab)
	query = (
		frappe.qb.from_(child)
		.inner_join(parent)
		.on(parent.name == child.parent)
		.select(child[links.return_link].as_("detail"), Sum(-child[links.returned_qty]).as_("qty"))
		.where((parent.docstatus == 1) & (parent.is_return == 1) & (parent.posting_date <= as_on_date))
		.where(child[links.return_link].isnotnull())
		.groupby(child[links.return_link])
	)
	if links.rejected_return_flag:
		query = query.where(child[links.rejected_return_flag] == 0)
	return query.as_("returned")


def get_project_field(doctype, child_doctype, party):
	if party == "supplier":
		return child_doctype.project
	return doctype.project
