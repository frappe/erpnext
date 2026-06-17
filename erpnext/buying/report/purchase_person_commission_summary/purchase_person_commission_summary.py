# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

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
				d.supplier,
				d.territory,
				d.posting_date,
				d.base_net_amount,
				d.purchase_person,
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

	return [
		{
			"label": _(filters["doc_type"]),
			"options": filters["doc_type"],
			"fieldname": filters["doc_type"],
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Supplier"),
			"options": "Supplier",
			"fieldname": "supplier",
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
			"label": _("Purchase Person"),
			"options": "Purchase Person",
			"fieldname": "purchase_person",
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


def get_entries(filters):
	dt = qb.DocType(filters["doc_type"])
	pt = qb.DocType("Purchase Team")
	date_field = dt["transaction_date"] if filters["doc_type"] == "Purchase Order" else dt["posting_date"]

	conditions = get_conditions(dt, pt, filters, date_field)
	return (
		qb.from_(dt)
		.join(pt)
		.on(pt.parent.eq(dt.name) & pt.parenttype.eq(filters["doc_type"]))
		.select(
			dt.name,
			dt.supplier,
			dt.territory,
			date_field.as_("posting_date"),
			dt.base_net_total.as_("base_net_amount"),
			pt.commission_rate,
			pt.purchase_person,
			pt.allocated_percentage,
			pt.allocated_amount,
			pt.incentives,
		)
		.where(Criterion.all(conditions))
		.orderby(dt.name, pt.purchase_person)
		.run(as_dict=True)
	)


def get_conditions(dt, pt, filters, date_field):
	conditions = [dt.docstatus.eq(1)]

	from_dt = filters.get("from_date")
	to_dt = filters.get("to_date")
	if from_dt and to_dt:
		conditions.append(date_field.between(from_dt, to_dt))
	elif from_dt:
		conditions.append(date_field.gte(from_dt))
	elif to_dt:
		conditions.append(date_field.lte(to_dt))

	for field in ["company", "supplier", "territory"]:
		if filters.get(field):
			conditions.append(dt[field].eq(filters.get(field)))

	if filters.get("purchase_person"):
		conditions.append(pt["purchase_person"].eq(filters.get("purchase_person")))

	return conditions
