# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce, Sum


def execute(filters=None):
	if not filters:
		filters = {}
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters):
	doc_type = filters.get("doc_type") or "Sales Invoice"
	is_sales = doc_type == "Sales Invoice"
	item_wise = bool(filters.get("item_wise"))

	columns = [
		{
			"label": _("Invoice"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": doc_type,
			"width": 180,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{
			"label": _("Customer") if is_sales else _("Supplier"),
			"fieldname": "party",
			"fieldtype": "Link",
			"options": "Customer" if is_sales else "Supplier",
			"width": 150,
		},
		{
			"label": _("Cost Center"),
			"fieldname": "cost_center",
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 130,
		},
	]
	if is_sales:
		columns.append({"label": _("Emirate"), "fieldname": "emirate", "fieldtype": "Data", "width": 110})
	else:
		columns.append(
			{
				"label": _("Reverse Charge"),
				"fieldname": "reverse_charge",
				"fieldtype": "Data",
				"width": 110,
			}
		)
	if item_wise:
		columns.extend(
			[
				{
					"label": _("Item Code"),
					"fieldname": "item_code",
					"fieldtype": "Link",
					"options": "Item",
					"width": 150,
				},
				{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
				{"label": _("Rate"), "fieldname": "rate", "fieldtype": "Currency", "width": 100},
			]
		)
	else:
		columns.append({"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80})
	columns.extend(
		[
			{"label": _("Net Amount"), "fieldname": "net_amount", "fieldtype": "Currency", "width": 120},
			{"label": _("VAT Amount"), "fieldname": "vat_amount", "fieldtype": "Currency", "width": 120},
			{
				"label": _("Total Amount"),
				"fieldname": "total_amount",
				"fieldtype": "Currency",
				"width": 120,
			},
		]
	)
	return columns


def get_data(filters):
	doc_type = filters.get("doc_type") or "Sales Invoice"
	if doc_type == "Sales Invoice":
		return _fetch_rows(filters, is_sales=True)
	if doc_type == "Purchase Invoice":
		return _fetch_rows(filters, is_sales=False)
	return []


def _fetch_rows(filters, is_sales):
	"""Build the VAT register query for either Sales or Purchase Invoices.

	Item-wise mode returns one row per Sales/Purchase Invoice Item; the
	default mode aggregates back to one row per invoice with summed qty,
	net, VAT, and total. ``COALESCE(i.tax_amount, 0)`` is used everywhere
	so a missing VAT amount surfaces as 0 instead of NULL — matching the
	currency display and avoiding NULLs in client-side totals.
	"""
	parent_doctype = "Sales Invoice" if is_sales else "Purchase Invoice"
	child_doctype = "Sales Invoice Item" if is_sales else "Purchase Invoice Item"
	parent = frappe.qb.DocType(parent_doctype)
	child = frappe.qb.DocType(child_doctype)
	item_wise = bool(filters.get("item_wise"))

	party_field = parent.customer if is_sales else parent.supplier
	party_extra = parent.vat_emirate.as_("emirate") if is_sales else parent.reverse_charge

	tax_amount = Coalesce(child.tax_amount, 0)
	gross = child.base_net_amount + tax_amount

	if item_wise:
		query = (
			frappe.qb.from_(parent)
			.inner_join(child)
			.on(child.parent == parent.name)
			.where(parent.docstatus == 1)
			.select(
				parent.name,
				parent.posting_date,
				party_field.as_("party"),
				Coalesce(child.cost_center, parent.cost_center).as_("cost_center"),
				party_extra,
				child.item_code,
				child.qty,
				child.rate,
				child.base_net_amount.as_("net_amount"),
				tax_amount.as_("vat_amount"),
				gross.as_("total_amount"),
			)
			.orderby(parent.posting_date)
			.orderby(parent.name)
			.orderby(child.idx)
		)
	else:
		cost_center = parent.cost_center
		query = (
			frappe.qb.from_(parent)
			.inner_join(child)
			.on(child.parent == parent.name)
			.where(parent.docstatus == 1)
			.select(
				parent.name,
				parent.posting_date,
				party_field.as_("party"),
				cost_center,
				party_extra,
				Sum(child.qty).as_("qty"),
				Coalesce(Sum(child.base_net_amount), 0).as_("net_amount"),
				Coalesce(Sum(tax_amount), 0).as_("vat_amount"),
				Coalesce(Sum(gross), 0).as_("total_amount"),
			)
			.groupby(parent.name, parent.posting_date, party_field, cost_center, party_extra)
			.orderby(parent.posting_date)
			.orderby(parent.name)
		)

	query = _apply_period_filters(query, parent, filters)

	if is_sales and filters.get("vat"):
		query = query.where(parent.vat_emirate == filters["vat"])
	if not is_sales and filters.get("reverse_charge") in ("Y", "N"):
		query = query.where(parent.reverse_charge == filters["reverse_charge"])
	if is_sales:
		category_criterion = _sales_category_criterion(child, filters.get("category"))
		if category_criterion is not None:
			query = query.where(category_criterion)

	return query.run(as_dict=True)


def _apply_period_filters(query, parent, filters):
	if filters.get("company"):
		query = query.where(parent.company == filters["company"])
	if filters.get("from_date"):
		query = query.where(parent.posting_date >= filters["from_date"])
	if filters.get("to_date"):
		query = query.where(parent.posting_date <= filters["to_date"])
	return query


def _sales_category_criterion(child, category):
	"""Translate the ``category`` filter into a Sales Invoice Item criterion."""
	if category == "Standard":
		return (child.is_zero_rated != 1) & (child.is_exempt != 1)
	if category == "Zero Rated":
		return child.is_zero_rated == 1
	if category == "Exempt Rated":
		return child.is_exempt == 1
	return None
