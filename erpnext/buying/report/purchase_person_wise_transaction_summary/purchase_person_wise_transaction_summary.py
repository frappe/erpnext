# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _, msgprint, qb
from frappe.query_builder import Case, Criterion

from erpnext import get_company_currency


def execute(filters=None):
	if not filters:
		filters = {}

	validate_filters(filters)

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
					d.supplier,
					d.warehouse,
					d.posting_date,
					d.item_code,
					item_details.get(d.item_code, {}).get("item_group"),
					item_details.get(d.item_code, {}).get("brand"),
					d.stock_qty,
					d.base_net_amount,
					d.purchase_person,
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


def validate_filters(filters):
	ALLOWED_DOCTYPES = ["Purchase Order", "Purchase Invoice", "Purchase Receipt"]

	if not filters.get("doc_type"):
		msgprint(_("Please select the document type first"), raise_exception=1)

	if filters.get("doc_type") not in ALLOWED_DOCTYPES:
		frappe.throw(_("{0}, {1} or {2} are the only allowed options.").format(*ALLOWED_DOCTYPES))


def get_columns(filters):
	return [
		{
			"label": _(filters["doc_type"]),
			"options": filters["doc_type"],
			"fieldname": frappe.scrub(filters["doc_type"]),
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
		{"label": _("Total Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 140},
		{
			"label": _("Amount"),
			"options": "currency",
			"fieldname": "amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Purchase Person"),
			"options": "Purchase Person",
			"fieldname": "purchase_person",
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


def get_entries(filters):
	doc_type = filters["doc_type"]

	date_field = "transaction_date" if doc_type == "Purchase Order" else "posting_date"
	qty_field = "received_qty" if doc_type == "Purchase Order" else "qty"

	dt = frappe.qb.DocType(doc_type)
	dt_item = frappe.qb.DocType(f"{doc_type} Item")
	pt = frappe.qb.DocType("Purchase Team")

	calc_qty = dt_item[qty_field] * dt_item.conversion_factor
	calc_net_amount = dt_item.base_net_rate * calc_qty

	stock_qty_case = Case().when(dt.status == "Closed", calc_qty).else_(dt_item.stock_qty).as_("stock_qty")

	base_net_amount_case = (
		Case()
		.when(dt.status == "Closed", calc_net_amount)
		.else_(dt_item.base_net_amount)
		.as_("base_net_amount")
	)

	contribution_amt_case = (
		Case()
		.when(dt.status == "Closed", (calc_net_amount * pt.allocated_percentage / 100))
		.else_(dt_item.base_net_amount * pt.allocated_percentage / 100)
		.as_("contribution_amt")
	)

	conditions = get_conditions(dt, pt, filters, date_field)

	query = (
		frappe.qb.from_(dt)
		.join(dt_item)
		.on(dt.name == dt_item.parent)
		.join(pt)
		.on(dt.name == pt.parent)
		.select(
			dt.name,
			dt.supplier,
			dt[date_field].as_("posting_date"),
			dt_item.item_code,
			pt.purchase_person,
			pt.allocated_percentage,
			dt_item.warehouse,
			stock_qty_case,
			base_net_amount_case,
			contribution_amt_case,
		)
		.where(pt.parenttype == doc_type)
		.where(dt.docstatus == 1)
		.where(Criterion.all(conditions))
		.orderby(pt.purchase_person)
		.orderby(dt.name, order=frappe.qb.desc)
	)

	return query.run(as_dict=True)


def get_conditions(dt, pt, filters, date_field):
	conditions = []

	for field in ["company", "supplier"]:
		if filters.get(field):
			conditions.append(dt[field].eq(filters[field]))

	if filters.get("purchase_person"):
		lft, rgt = frappe.get_value("Purchase Person", filters.get("purchase_person"), ["lft", "rgt"])
		purchase_person_tbl = frappe.qb.DocType("Purchase Person")
		subquery = (
			frappe.qb.from_(purchase_person_tbl)
			.select(purchase_person_tbl.name)
			.where(purchase_person_tbl.lft >= lft)
			.where(purchase_person_tbl.rgt <= rgt)
		)
		conditions.append(pt.purchase_person.isin(subquery))

	if filters.get("from_date"):
		conditions.append(dt[date_field].gte(filters["from_date"]))

	if filters.get("to_date"):
		conditions.append(dt[date_field].lte(filters["to_date"]))

	items = get_items(filters)
	if items:
		conditions.append(
			frappe.qb.DocType(f"{filters['doc_type']} Item").item_code.isin([i[0] for i in items])
		)
	elif filters.get("item_group") or filters.get("brand"):
		conditions.append(frappe.qb.terms.ValueWrapper(0).eq(1))

	return conditions


def get_items(filters):
	item = qb.DocType("Item")

	item_query_conditions = []
	if filters.get("item_group"):
		item_group = qb.DocType("Item Group")
		lft, rgt = frappe.db.get_all(
			"Item Group", filters={"name": filters.get("item_group")}, fields=["lft", "rgt"], as_list=True
		)[0]
		item_group_query = (
			qb.from_(item_group)
			.select(item_group.name)
			.where((item_group.lft >= lft) & (item_group.rgt <= rgt))
		)
		item_query_conditions.append(item.item_group.isin(item_group_query))
	if filters.get("brand"):
		item_query_conditions.append(item.brand == filters.get("brand"))

	if not item_query_conditions:
		return []

	return qb.from_(item).select(item.name).where(Criterion.all(item_query_conditions)).run()


def get_item_details():
	items = frappe.get_all("Item", fields=["name", "item_group", "brand"])
	return {d.name: d for d in items}
