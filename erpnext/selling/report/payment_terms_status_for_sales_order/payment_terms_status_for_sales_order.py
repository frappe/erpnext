# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _, qb, query_builder
from frappe.query_builder import Criterion, functions


def get_columns():
	columns = [
		{
			"label": _("Sales Order"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Sales Order",
		},
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
		},
		{
			"label": _("Posting Date"),
			"fieldname": "submitted",
			"fieldtype": "Date",
		},
		{
			"label": _("Payment Term"),
			"fieldname": "payment_term",
			"fieldtype": "Data",
		},
		{
			"label": _("Description"),
			"fieldname": "description",
			"fieldtype": "Data",
		},
		{
			"label": _("Due Date"),
			"fieldname": "due_date",
			"fieldtype": "Date",
		},
		{
			"label": _("Invoice Portion"),
			"fieldname": "invoice_portion",
			"fieldtype": "Percent",
		},
		{
			"label": _("Payment Amount"),
			"fieldname": "base_payment_amount",
			"fieldtype": "Currency",
			"options": "currency",
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"options": "currency",
		},
		{
			"label": _("Invoices"),
			"fieldname": "invoices",
			"fieldtype": "Link",
			"options": "Sales Invoice",
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
		},
		{"label": _("Currency"), "fieldname": "currency", "fieldtype": "Currency", "hidden": 1},
	]
	return columns


def get_descendants_of(doctype, group_name):
	group_doc = qb.DocType(doctype)
	# get lft and rgt of group node
	lft, rgt = (
		qb.from_(group_doc).select(group_doc.lft, group_doc.rgt).where(group_doc.name == group_name)
	).run()[0]

	# get all children of group node
	query = (
		qb.from_(group_doc).select(group_doc.name).where((group_doc.lft >= lft) & (group_doc.rgt <= rgt))
	)

	child_nodes = []
	for x in query.run():
		child_nodes.append(x[0])

	return child_nodes


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_customers_or_items(doctype, txt, searchfield, start, page_len, filters):
	filter_list = []
	if isinstance(filters, list):
		for item in filters:
			if item[0] == doctype:
				filter_list.append(item)
			elif item[0] == "Customer Group":
				if item[3] != "":
					filter_list.append(
						[doctype, "customer_group", "in", get_descendants_of("Customer Group", item[3])]
					)
			elif item[0] == "Item Group":
				if item[3] != "":
					filter_list.append([doctype, "item_group", "in", get_descendants_of("Item Group", item[3])])

	if searchfield and txt:
		filter_list.append([doctype, searchfield, "like", "%%%s%%" % txt])

	return frappe.desk.reportview.execute(
		doctype,
		filters=filter_list,
		fields=["name", "customer_group"] if doctype == "Customer" else ["name", "item_group"],
		limit_start=start,
		limit_page_length=page_len,
		as_list=True,
	)


def get_conditions(filters):
	"""
	Convert filter options to conditions used in query
	"""
	filters = frappe._dict(filters) if filters else frappe._dict({})
	conditions = frappe._dict({})

	conditions.company = filters.company or frappe.defaults.get_user_default("company")
	conditions.end_date = filters.period_end_date or frappe.utils.today()
	conditions.start_date = filters.period_start_date or frappe.utils.add_months(
		conditions.end_date, -1
	)

	return conditions


def build_filter_criterions(filters):
	filters = frappe._dict(filters) if filters else frappe._dict({})
	qb_criterions = []

	if filters.customer_group:
		qb_criterions.append(
			qb.DocType("Sales Order").customer_group.isin(
				get_descendants_of("Customer Group", filters.customer_group)
			)
		)

	if filters.customer:
		qb_criterions.append(qb.DocType("Sales Order").customer == filters.customer)

	if filters.item_group:
		qb_criterions.append(
			qb.DocType("Sales Order Item").item_group.isin(
				get_descendants_of("Item Group", filters.item_group)
			)
		)

	if filters.item:
		qb_criterions.append(qb.DocType("Sales Order Item").item_code == filters.item)

	return qb_criterions


def get_so_with_invoices(filters):
	"""
	Get Sales Order with payment terms template with their associated Invoices
	"""
	sorders = []

	so = qb.DocType("Sales Order")
	ps = qb.DocType("Payment Schedule")
	soi = qb.DocType("Sales Order Item")

	conditions = get_conditions(filters)
	filter_criterions = build_filter_criterions(filters)

	datediff = query_builder.CustomFunction("DATEDIFF", ["cur_date", "due_date"])
	ifelse = query_builder.CustomFunction("IF", ["condition", "then", "else"])

	query_so = (
		qb.from_(so)
		.join(soi)
		.on(soi.parent == so.name)
		.join(ps)
		.on(ps.parent == so.name)
		.select(
			so.name,
			so.customer,
			so.transaction_date.as_("submitted"),
			ifelse(datediff(ps.due_date, functions.CurDate()) < 0, "Overdue", "Unpaid").as_("status"),
			ps.payment_term,
			ps.description,
			ps.due_date,
			ps.invoice_portion,
			ps.base_payment_amount,
			ps.paid_amount,
		)
		.where(
			(so.docstatus == 1)
			& (so.payment_terms_template != "NULL")
			& (so.company == conditions.company)
			& (so.transaction_date[conditions.start_date : conditions.end_date])
		)
		.where(Criterion.all(filter_criterions))
		.orderby(so.name, so.transaction_date, ps.due_date)
	)

	sorders = query_so.run(as_dict=True)

	invoices = []
	if sorders != []:
		soi = qb.DocType("Sales Order Item")
		si = qb.DocType("Sales Invoice")
		sii = qb.DocType("Sales Invoice Item")
		query_inv = (
			qb.from_(sii)
			.right_join(si)
			.on(si.name == sii.parent)
			.inner_join(soi)
			.on(soi.name == sii.so_detail)
			.select(sii.sales_order, sii.parent.as_("invoice"), si.base_grand_total.as_("invoice_amount"))
			.where((sii.sales_order.isin([x.name for x in sorders])) & (si.docstatus == 1))
			.groupby(sii.parent)
		)
		invoices = query_inv.run(as_dict=True)

	return sorders, invoices


def set_payment_terms_statuses(sales_orders, invoices, filters):
	"""
	compute status for payment terms with associated sales invoice using FIFO
	"""

	for so in sales_orders:
		so.currency = frappe.get_cached_value("Company", filters.get("company"), "default_currency")
		so.invoices = ""
		for inv in [x for x in invoices if x.sales_order == so.name and x.invoice_amount > 0]:
			if so.base_payment_amount - so.paid_amount > 0:
				amount = so.base_payment_amount - so.paid_amount
				if inv.invoice_amount >= amount:
					inv.invoice_amount -= amount
					so.paid_amount += amount
					so.invoices += "," + inv.invoice
					so.status = "Completed"
					break
				else:
					so.paid_amount += inv.invoice_amount
					inv.invoice_amount = 0
					so.invoices += "," + inv.invoice
					so.status = "Partly Paid"

	return sales_orders, invoices


def prepare_chart(s_orders):
	if len(set([x.name for x in s_orders])) == 1:
		chart = {
			"data": {
				"labels": [term.payment_term for term in s_orders],
				"datasets": [
					{
						"name": "Payment Amount",
						"values": [x.base_payment_amount for x in s_orders],
					},
					{
						"name": "Paid Amount",
						"values": [x.paid_amount for x in s_orders],
					},
				],
			},
			"type": "bar",
		}
		return chart


def execute(filters=None):
	columns = get_columns()
	sales_orders, so_invoices = get_so_with_invoices(filters)
	sales_orders, so_invoices = set_payment_terms_statuses(sales_orders, so_invoices, filters)

	prepare_chart(sales_orders)

	data = sales_orders
	message = []
	chart = prepare_chart(sales_orders)

	return columns, data, message, chart
