# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _, msgprint, qb
from frappe.query_builder import Criterion


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	entries = get_entries(filters)
	data = []

	for d in entries:
		data.append(
			[
				d.name,
				d.customer,
				d.territory,
				d.posting_date,
				d.base_net_amount,
				d.sales_person,
				d.allocated_percentage,
				d.commission_rate,
				d.allocated_amount,
				d.incentives,
			]
		)

	if data:
		total_row = [""] * len(data[0])
		data.append(total_row)

	return columns, data


def get_columns(filters):
	if not filters.get("doc_type"):
		msgprint(_("Please select the document type first"), raise_exception=1)

	columns = [
		{
			"label": _(filters["doc_type"]),
			"options": filters["doc_type"],
			"fieldname": filters["doc_type"],
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Customer"),
			"options": "Customer",
			"fieldname": "customer",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Territory"),
			"options": "Territory",
			"fieldname": "territory",
			"fieldtype": "Link",
			"width": 100,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 120},
		{
			"label": _("Sales Person"),
			"options": "Sales Person",
			"fieldname": "sales_person",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Contribution %"),
			"fieldname": "contribution_percentage",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Commission Rate %"),
			"fieldname": "commission_rate",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Contribution Amount"),
			"fieldname": "contribution_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{"label": _("Incentives"), "fieldname": "incentives", "fieldtype": "Currency", "width": 120},
	]

	return columns


def get_entries(filters):
	dt = qb.DocType(filters["doc_type"])
	st = qb.DocType("Sales Team")
	date_field = dt["transaction_date"] if filters["doc_type"] == "Sales Order" else dt["posting_date"]

	conditions = get_conditions(dt, st, filters, date_field)
	entries = (
		qb.from_(dt)
		.join(st)
		.on(st.parent.eq(dt.name) & st.parenttype.eq(filters["doc_type"]))
		.select(
			dt.name,
			dt.customer,
			dt.territory,
			date_field.as_("posting_date"),
			dt.base_net_total.as_("base_net_amount"),
			st.commission_rate,
			st.sales_person,
			st.allocated_percentage,
			st.allocated_amount,
			st.incentives,
		)
		.where(Criterion.all(conditions))
		.orderby(dt.name, st.sales_person)
		.run(as_dict=True)
	)

	return entries


def get_conditions(dt, st, filters, date_field):
	conditions = []

	conditions.append(dt.docstatus.eq(1))
	from_dt = filters.get("from_date")
	to_dt = filters.get("to_date")
	if from_dt and to_dt:
		conditions.append(date_field.between(from_dt, to_dt))
	elif from_dt and not to_dt:
		conditions.append(date_field.gte(from_dt))
	elif not from_dt and to_dt:
		conditions.append(date_field.lte(to_dt))

	for field in ["company", "customer", "territory"]:
		if filters.get(field):
			conditions.append(dt[field].eq(filters.get(field)))

	if filters.get("sales_person"):
		conditions.append(st["sales_person"].eq(filters.get("sales_person")))

	return conditions
