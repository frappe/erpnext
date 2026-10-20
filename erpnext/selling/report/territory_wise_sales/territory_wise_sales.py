# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.permissions import get_allowed_docs_for_doctype, get_user_permissions

from erpnext import get_default_currency


def execute(filters=None):
	filters = frappe._dict(filters)
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data


def get_columns(filters=None):
	filters = filters or frappe._dict()
	# amounts are stored in each document's company currency; show the selected
	# company's currency, falling back to the default company's
	currency = get_default_currency()
	if filters.get("company"):
		currency = frappe.get_cached_value("Company", filters.get("company"), "default_currency") or currency
	return [
		{
			"label": _("Territory"),
			"fieldname": "territory",
			"fieldtype": "Link",
			"options": "Territory",
			"width": 150,
		},
		{
			"label": _("Opportunity Amount"),
			"fieldname": "opportunity_amount",
			"fieldtype": "Currency",
			"options": currency,
			"width": 150,
		},
		{
			"label": _("Quotation Amount"),
			"fieldname": "quotation_amount",
			"fieldtype": "Currency",
			"options": currency,
			"width": 150,
		},
		{
			"label": _("Order Amount"),
			"fieldname": "order_amount",
			"fieldtype": "Currency",
			"options": currency,
			"width": 150,
		},
		{
			"label": _("Billing Amount"),
			"fieldname": "billing_amount",
			"fieldtype": "Currency",
			"options": currency,
			"width": 150,
		},
	]


def get_data(filters=None):
	data = []

	# The report walks Opportunity -> Quotation -> Sales Order -> Sales Invoice, and its
	# roles cannot read Sales Invoice, so permissions can't be enforced via get_list.
	# Apply the selected company filter and the user's Customer/Company permissions at
	# every stage, reading each permission against the stage's own doctype (user
	# permissions can be scoped to a specific doctype).
	user_permissions = get_user_permissions(frappe.session.user)

	opportunities = restrict(
		get_opportunities(filters), "Opportunity", filters, user_permissions, "party_name", "opportunity_from"
	)
	quotations = restrict(
		get_quotations(opportunities), "Quotation", filters, user_permissions, "party_name", "quotation_to"
	)
	sales_orders = restrict(
		get_sales_orders(quotations), "Sales Order", filters, user_permissions, "customer"
	)
	sales_invoices = restrict(
		get_sales_invoice(sales_orders), "Sales Invoice", filters, user_permissions, "customer"
	)

	for territory in frappe.get_all("Territory"):
		territory_opportunities = []
		if opportunities:
			territory_opportunities = list(filter(lambda x: x.territory == territory.name, opportunities))
		t_opportunity_names = []
		if territory_opportunities:
			t_opportunity_names = [t.name for t in territory_opportunities]
		territory_quotations = []
		if t_opportunity_names and quotations:
			territory_quotations = list(filter(lambda x: x.opportunity in t_opportunity_names, quotations))
		t_quotation_names = []
		if territory_quotations:
			t_quotation_names = [t.name for t in territory_quotations]

		territory_orders = []
		if t_quotation_names and sales_orders:
			territory_orders = list(filter(lambda x: x.quotation in t_quotation_names, sales_orders))
		t_order_names = []
		if territory_orders:
			t_order_names = [t.name for t in territory_orders]

		territory_invoices = (
			list(filter(lambda x: x.sales_order in t_order_names, sales_invoices))
			if t_order_names and sales_invoices
			else []
		)

		territory_data = {
			"territory": territory.name,
			"opportunity_amount": _get_total(territory_opportunities, "base_opportunity_amount"),
			"quotation_amount": _get_total(territory_quotations),
			"order_amount": _get_total(territory_orders),
			"billing_amount": _get_total(territory_invoices),
		}
		data.append(territory_data)

	return data


def restrict(rows, doctype, filters, user_permissions, party_field, party_type_field=None):
	# Drop rows the selected company filter or the user's permissions (scoped to this
	# doctype) forbid. Customer permissions only apply when the party is a Customer, so
	# lead/prospect rows stay visible.
	customers = get_allowed_docs_for_doctype(user_permissions.get("Customer", []), doctype)
	companies = get_allowed_docs_for_doctype(user_permissions.get("Company", []), doctype)
	requested_company = filters.get("company")

	permitted = []
	for row in rows:
		company = row.get("company")
		if requested_company and company != requested_company:
			continue
		if companies and company not in companies:
			continue
		if customers and (party_type_field is None or row.get(party_type_field) == "Customer"):
			if row.get(party_field) not in customers:
				continue
		permitted.append(row)

	return permitted


def get_opportunities(filters):
	orm_filters = {}

	if filters.get("transaction_date"):
		orm_filters["transaction_date"] = [
			"between",
			[filters["transaction_date"][0], filters["transaction_date"][1]],
		]

	return frappe.get_all(
		"Opportunity",
		fields=["name", "territory", "base_opportunity_amount", "company", "opportunity_from", "party_name"],
		filters=orm_filters,
	)


def get_quotations(opportunities):
	if not opportunities:
		return []

	opportunity_names = [o.get("name") for o in opportunities]

	return frappe.get_all(
		"Quotation",
		fields=["name", "base_grand_total", "opportunity", "company", "quotation_to", "party_name"],
		filters={"docstatus": 1, "opportunity": ["in", opportunity_names]},
	)


def get_sales_orders(quotations):
	if not quotations:
		return []

	quotation_names = [q.get("name") for q in quotations]

	SalesOrder = frappe.qb.DocType("Sales Order")
	SalesOrderItem = frappe.qb.DocType("Sales Order Item")

	query = (
		frappe.qb.from_(SalesOrder)
		.join(SalesOrderItem)
		.on(SalesOrder.name == SalesOrderItem.parent)
		.select(
			SalesOrder.name,
			SalesOrder.base_grand_total,
			SalesOrder.company,
			SalesOrder.customer,
			SalesOrderItem.prevdoc_docname.as_("quotation"),
		)
		.where(SalesOrder.docstatus == 1)
		.where(SalesOrderItem.prevdoc_docname.isin(quotation_names))
	)

	return query.run(as_dict=True)


def get_sales_invoice(sales_orders):
	if not sales_orders:
		return []

	so_names = [so.get("name") for so in sales_orders]

	SalesInvoice = frappe.qb.DocType("Sales Invoice")
	SalesInvoiceItem = frappe.qb.DocType("Sales Invoice Item")

	query = (
		frappe.qb.from_(SalesInvoice)
		.join(SalesInvoiceItem)
		.on(SalesInvoice.name == SalesInvoiceItem.parent)
		.select(
			SalesInvoice.name,
			SalesInvoice.base_grand_total,
			SalesInvoice.company,
			SalesInvoice.customer,
			SalesInvoiceItem.sales_order,
		)
		.where(SalesInvoice.docstatus == 1)
		.where(SalesInvoiceItem.sales_order.isin(so_names))
	)

	return query.run(as_dict=True)


def _get_total(doclist, amount_field="base_grand_total"):
	if not doclist:
		return 0

	# a document fans out into one row per item/source, so total each one only once
	seen = set()
	total = 0
	for doc in doclist:
		if doc.get("name") in seen:
			continue
		seen.add(doc.get("name"))
		total += doc.get(amount_field, 0)

	return total
