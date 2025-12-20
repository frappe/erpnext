# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _

from erpnext import get_default_currency


def execute(filters=None):
	filters = frappe._dict(filters)
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	currency = get_default_currency()
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

	opportunities = get_opportunities(filters)
	quotations = get_quotations(opportunities)
	sales_orders = get_sales_orders(quotations)
	sales_invoices = get_sales_invoice(sales_orders)

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
			"opportunity_amount": _get_total(territory_opportunities, "opportunity_amount"),
			"quotation_amount": _get_total(territory_quotations),
			"order_amount": _get_total(territory_orders),
			"billing_amount": _get_total(territory_invoices),
		}
		data.append(territory_data)

	return data


def get_opportunities(filters):
	conditions = ""

	if filters.get("transaction_date"):
		conditions = " WHERE transaction_date between {} and {}".format(
			frappe.db.escape(filters["transaction_date"][0]),
			frappe.db.escape(filters["transaction_date"][1]),
		)

	if filters.company:
		if conditions:
			conditions += " AND"
		else:
			conditions += " WHERE"
		conditions += " company = %(company)s"

	return frappe.db.sql(
		f"""
		SELECT name, territory, opportunity_amount
		FROM `tabOpportunity` {conditions}
	""",
		filters,
		as_dict=1,
	)  # nosec


def get_quotations(opportunities):
	if not opportunities:
		return []

	opportunity_names = [o.name for o in opportunities]

	return frappe.db.sql(
		"""
		SELECT `name`,`base_grand_total`, `opportunity`
		FROM `tabQuotation`
		WHERE docstatus=1 AND opportunity in ({})
	""".format(", ".join(["%s"] * len(opportunity_names))),
		tuple(opportunity_names),
		as_dict=1,
	)  # nosec


def get_sales_orders(quotations):
	if not quotations:
		return []

	quotation_names = [q.name for q in quotations]

	return frappe.db.sql(
		"""
	SELECT so.`name`, so.`base_grand_total`, soi.prevdoc_docname as quotation
	FROM `tabSales Order` so, `tabSales Order Item` soi
	WHERE so.docstatus=1 AND so.name = soi.parent AND soi.prevdoc_docname in ({})
	""".format(", ".join(["%s"] * len(quotation_names))),
		tuple(quotation_names),
		as_dict=1,
	)  # nosec


def get_sales_invoice(sales_orders):
	if not sales_orders:
		return []

	so_names = [so.name for so in sales_orders]

	return frappe.db.sql(
		"""
	SELECT si.name, si.base_grand_total, sii.sales_order
	FROM `tabSales Invoice` si, `tabSales Invoice Item` sii
	WHERE si.docstatus=1 AND si.name = sii.parent AND sii.sales_order in ({})
	""".format(", ".join(["%s"] * len(so_names))),
		tuple(so_names),
		as_dict=1,
	)  # nosec


def _get_total(doclist, amount_field="base_grand_total"):
	if not doclist:
		return 0

	total = 0
	for doc in doclist:
		total += doc.get(amount_field, 0)

	return total
