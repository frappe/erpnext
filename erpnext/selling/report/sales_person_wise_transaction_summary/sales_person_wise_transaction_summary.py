# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint, qb
from frappe.query_builder import Criterion
from frappe.query_builder.utils import DocType

from erpnext import get_company_currency


def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	entries = get_entries(filters)
	item_details = get_item_details()
	data = []

	company_currency = get_company_currency(filters.get("company"))

	for d in entries:
		if d.stock_qty > 0 or filters.get("show_return_entries", 0):
			data.append(
				[
					d.name,
					d.customer,
					d.territory,
					d.warehouse,
					d.posting_date,
					d.item_code,
					item_details.get(d.item_code, {}).get("item_group"),
					item_details.get(d.item_code, {}).get("brand"),
					d.stock_qty,
					d.base_net_amount,
					d.sales_person,
					d.allocated_percentage,
					(d.stock_qty * d.allocated_percentage / 100),
					d.contribution_amt,
					company_currency,
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
			"fieldname": frappe.scrub(filters["doc_type"]),
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
			"width": 140,
		},
		{
			"label": _("Warehouse"),
			"options": "Warehouse",
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"width": 140,
		},
		{"label": _("Posting Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 140},
		{
			"label": _("Item Code"),
			"options": "Item",
			"fieldname": "item_code",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Item Group"),
			"options": "Item Group",
			"fieldname": "item_group",
			"fieldtype": "Link",
			"width": 140,
		},
		{
			"label": _("Brand"),
			"options": "Brand",
			"fieldname": "brand",
			"fieldtype": "Link",
			"width": 140,
		},
		{"label": _("SO Total Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 140},
		{
			"label": _("Amount"),
			"options": "currency",
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Sales Person"),
			"options": "Sales Person",
			"fieldname": "sales_person",
			"fieldtype": "Link",
			"width": 140,
		},
		{"label": _("Contribution %"), "fieldname": "contribution", "fieldtype": "Float", "width": 140},
		{
			"label": _("Contribution Qty"),
			"fieldname": "contribution_qty",
			"fieldtype": "Float",
			"width": 140,
		},
		{
			"label": _("Contribution Amount"),
			"options": "currency",
			"fieldname": "contribution_amt",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Currency"),
			"options": "Currency",
			"fieldname": "currency",
			"fieldtype": "Link",
			"hidden": 1,
		},
	]

	return columns


def get_entries(filters):
	doc_type = filters["doc_type"]
	date_field = "transaction_date" if doc_type == "Sales Order" else "posting_date"
	qty_field = "delivered_qty" if doc_type == "Sales Order" else "qty"

	doctype = DocType(doc_type)
	item_doctype = DocType(doc_type + " Item")
	sales_team = DocType("Sales Team")

	stock_qty = (
		frappe.qb.terms.Case()
		.when(doctype.status == "Closed", item_doctype[qty_field] * item_doctype.conversion_factor)
		.else_(item_doctype.stock_qty)
	)

	base_net_amount = (
		frappe.qb.terms.Case()
		.when(
			doctype.status == "Closed",
			item_doctype[qty_field] * item_doctype.base_net_rate * item_doctype.conversion_factor,
		)
		.else_(item_doctype.base_net_amount)
	)

	contribution_amt = (
		frappe.qb.terms.Case()
		.when(
			doctype.status == "Closed",
			(item_doctype[qty_field] * item_doctype.base_net_rate * item_doctype.conversion_factor)
			* sales_team.allocated_percentage
			/ 100,
		)
		.else_(item_doctype.base_net_amount * sales_team.allocated_percentage / 100)
	)

	qb_filters = {"docstatus": 1}

	for field in ["company", "customer", "territory"]:
		if filters.get(field):
			qb_filters[field] = filters[field]

	if filters.get("from_date"):
		qb_filters[date_field] = [">=", filters["from_date"]]

	if filters.get("to_date"):
		if filters.get("from_date"):
			qb_filters[date_field] = ["between", [filters["from_date"], filters["to_date"]]]
		else:
			qb_filters[date_field] = ["<=", filters["to_date"]]

	query = frappe.qb.get_query(
		doc_type,
		filters=qb_filters,
		fields=[
			doctype.name,
			doctype.customer,
			doctype.territory,
			doctype[date_field].as_("posting_date"),
		],
		ignore_permissions=False,
	)

	query = (
		query.join(item_doctype)
		.on(doctype.name == item_doctype.parent)
		.join(sales_team)
		.on((doctype.name == sales_team.parent) & (sales_team.parenttype == doc_type))
		.select(
			item_doctype.item_code,
			item_doctype.warehouse,
			sales_team.sales_person,
			sales_team.allocated_percentage,
			stock_qty.as_("stock_qty"),
			base_net_amount.as_("base_net_amount"),
			contribution_amt.as_("contribution_amt"),
		)
		.orderby(sales_team.sales_person)
		.orderby(doctype.name, order=frappe.qb.desc)
	)

	if filters.get("sales_person"):
		sp = DocType("Sales Person")
		lft, rgt = frappe.get_value("Sales Person", filters["sales_person"], ["lft", "rgt"])
		sp_subquery = frappe.qb.from_(sp).select(sp.name).where((sp.lft >= lft) & (sp.rgt <= rgt))
		query = query.where(sales_team.sales_person.isin(sp_subquery))

	items = get_items(filters)
	if items:
		query = query.where(item_doctype.item_code.isin(items))
	else:
		# return empty result, if no items are fetched after filtering on 'item group' and 'brand'
		query = query.where(item_doctype.item_code == "##NOMATCH##")

	return query.run(as_dict=True)


def get_items(filters):
	item = DocType("Item")

	item_query_conditions = []
	if filters.get("item_group"):
		item_group = DocType("Item Group")
		lft, rgt = frappe.db.get_all(
			"Item Group",
			filters={"name": filters.get("item_group")},
			fields=["lft", "rgt"],
			as_list=True,
		)[0]
		item_group_query = (
			qb.from_(item_group)
			.select(item_group.name)
			.where((item_group.lft >= lft) & (item_group.rgt <= rgt))
		)
		item_query_conditions.append(item.item_group.isin(item_group_query))

	if filters.get("brand"):
		item_query_conditions.append(item.brand == filters.get("brand"))

	items = qb.from_(item).select(item.name).where(Criterion.all(item_query_conditions)).run()
	return [r[0] for r in items]


def get_item_details():
	item_details = {}
	for d in frappe.db.get_all("Item", fields=["name", "item_group", "brand"]):
		item_details.setdefault(d.name, d)

	return item_details
