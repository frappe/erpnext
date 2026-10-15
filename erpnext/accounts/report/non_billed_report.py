# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.meta import get_field_precision
from frappe.query_builder.functions import IfNull, Round, Sum
from frappe.utils import flt
from pypika.queries import QueryBuilder

from erpnext import get_default_currency
from erpnext.accounts.report.order_billing_as_on import OrderBillingAsOn

BILLING_LINKS = {
	"Delivery Note": frappe._dict(
		invoice="Sales Invoice",
		invoice_link="dn_detail",
		order_link="so_detail",
		invoice_order_link="so_detail",
		invoiced_row_link="si_detail",
		billing_flag="update_billed_amount_in_delivery_note",
		return_link="dn_detail",
		returned_qty="stock_qty",
	),
	"Purchase Receipt": frappe._dict(
		invoice="Purchase Invoice",
		invoice_link="pr_detail",
		order_link="purchase_order_item",
		invoice_order_link="po_detail",
		billing_flag="update_billed_amount_in_purchase_receipt",
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
	order_billed_later = OrderBillingAsOn(doctype, links, as_on_date, precision).get_billed_later()
	returned = get_returned_as_on(doctype, child_tab, links, as_on_date)

	doctype = frappe.qb.DocType(doctype)
	child_doctype = frappe.qb.DocType(child_tab)
	item = frappe.qb.DocType("Item")

	docname = filters.get(args.get("reference_field"), None)
	project_field = get_project_field(doctype, child_doctype, party)
	later_billed_amount = IfNull(later_billed.amount, 0)
	has_order_billed_later = child_doctype.name.isin(list(order_billed_later) or [""])
	billed_amount = (child_doctype.billed_amt - later_billed_amount) * IfNull(doctype.conversion_rate, 1)
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
			child_doctype.name.as_("detail"),
		)
		.where(
			(doctype.docstatus == 1)
			& (doctype.status != "Closed")
			# a completed document was still to bill on the date only if billed after it
			& ((doctype.status != "Completed") | (later_billed_amount != 0) | has_order_billed_later)
			& (doctype.company == filters.get("company"))
			& (doctype.posting_date <= as_on_date)
			& (child_doctype.amount > 0)
			& ((item.is_stock_item == 1) | (item.is_fixed_asset == 1))
			& (
				(child_doctype.base_amount - Round(billed_amount, precision) - returned_amount > 0)
				| has_order_billed_later
			)
		)
		.orderby(doctype[args.get("order")], order=args.get("order_by"))
	)

	if docname:
		query = query.where(doctype.name == docname)

	return deduct_order_billed_later(query.run(as_dict=True), order_billed_later, precision)


def deduct_order_billed_later(data: list, order_billed_later: dict[str, float], precision: int) -> list:
	"""Take order-level billing spread on a row after the date out of it, dropping rows it leaves billed."""
	pending_rows = []
	for row in data:
		detail = row.pop("detail")
		if detail in order_billed_later:
			row.billed_amount = flt(row.billed_amount) - order_billed_later[detail]
			row.pending_amount = flt(row.pending_amount) + order_billed_later[detail]
			if flt(row.amount) - flt(row.billed_amount, precision) - flt(row.returned_amount) <= 0:
				continue
		pending_rows.append(row)
	return pending_rows


def get_billed_after(links, as_on_date):
	"""Amount billed per row by invoices posted after the date, to take out of the stored billed_amt."""
	invoice = frappe.qb.DocType(links.invoice)
	return get_billed_against_rows(links).where(invoice.posting_date > as_on_date).as_("later_billed")


def get_billed_against_rows(links: frappe._dict) -> QueryBuilder:
	"""Amount billed per row by invoices made against it, skipping notes that don't update billing."""
	invoice = frappe.qb.DocType(links.invoice)
	invoice_item = frappe.qb.DocType(links.invoice + " Item")
	return (
		frappe.qb.from_(invoice_item)
		.inner_join(invoice)
		.on(invoice.name == invoice_item.parent)
		.select(invoice_item[links.invoice_link].as_("detail"), Sum(invoice_item.amount).as_("amount"))
		.where(invoice.docstatus == 1)
		.where((invoice.is_return == 0) | (invoice[links.billing_flag] == 1))
		.where(invoice_item[links.invoice_link].isnotnull())
		.groupby(invoice_item[links.invoice_link])
	)


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
