# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import flt
from frappe.utils.nestedset import get_descendants_of


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.from_date > filters.to_date:
		frappe.throw(_("From Date cannot be greater than To Date"))

	columns = get_columns(filters)
	data = get_data(filters)

	chart_data = get_chart_data(data)

	return columns, data, None, chart_data


def get_columns(filters):
	return [
		{
			"label": _("Item Code"),
			"fieldtype": "Link",
			"fieldname": "item_code",
			"options": "Item",
			"width": 120,
		},
		{"label": _("Item Name"), "fieldtype": "Data", "fieldname": "item_name", "width": 140},
		{
			"label": _("Item Group"),
			"fieldtype": "Link",
			"fieldname": "item_group",
			"options": "Item Group",
			"width": 120,
		},
		{"label": _("Description"), "fieldtype": "Data", "fieldname": "description", "width": 150},
		{"label": _("Quantity"), "fieldtype": "Float", "fieldname": "quantity", "width": 150},
		{"label": _("UOM"), "fieldtype": "Link", "fieldname": "uom", "options": "UOM", "width": 100},
		{
			"label": _("Rate"),
			"fieldname": "rate",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Sales Order"),
			"fieldtype": "Link",
			"fieldname": "sales_order",
			"options": "Sales Order",
			"width": 100,
		},
		{
			"label": _("Transaction Date"),
			"fieldtype": "Date",
			"fieldname": "transaction_date",
			"width": 90,
		},
		{
			"label": _("Customer"),
			"fieldtype": "Link",
			"fieldname": "customer",
			"options": "Customer",
			"width": 100,
		},
		{"label": _("Customer Name"), "fieldtype": "Data", "fieldname": "customer_name", "width": 140},
		{
			"label": _("Customer Group"),
			"fieldtype": "Link",
			"fieldname": "customer_group",
			"options": "Customer Group",
			"width": 120,
		},
		{
			"label": _("Territory"),
			"fieldtype": "Link",
			"fieldname": "territory",
			"options": "Territory",
			"width": 100,
		},
		{
			"label": _("Project"),
			"fieldtype": "Link",
			"fieldname": "project",
			"options": "Project",
			"width": 100,
		},
		{
			"label": _("Delivered Quantity"),
			"fieldtype": "Float",
			"fieldname": "delivered_quantity",
			"width": 150,
		},
		{
			"label": _("Billed Amount"),
			"fieldtype": "Currency",
			"fieldname": "billed_amount",
			"options": "currency",
			"width": 120,
		},
		{
			"label": _("Company"),
			"fieldtype": "Link",
			"fieldname": "company",
			"options": "Company",
			"width": 100,
		},
		{
			"label": _("Currency"),
			"fieldtype": "Link",
			"fieldname": "currency",
			"options": "Currency",
			"hidden": 1,
		},
	]


def get_data(filters):
	data = []

	company_list = get_descendants_of("Company", filters.get("company"))
	company_list.append(filters.get("company"))

	customer_details = get_customer_details()
	item_details = get_item_details()
	sales_order_records = get_sales_order_details(company_list, filters)

	for record in sales_order_records:
		customer_record = customer_details.get(record.customer)
		item_record = item_details.get(record.item_code)
		row = {
			"item_code": record.get("item_code"),
			"item_name": item_record.get("item_name"),
			"item_group": item_record.get("item_group"),
			"description": record.get("description"),
			"quantity": record.get("qty"),
			"uom": record.get("uom"),
			"rate": record.get("base_rate"),
			"amount": record.get("base_amount"),
			"sales_order": record.get("name"),
			"transaction_date": record.get("transaction_date"),
			"customer": record.get("customer"),
			"customer_name": customer_record.get("customer_name"),
			"customer_group": customer_record.get("customer_group"),
			"territory": record.get("territory"),
			"project": record.get("project"),
			"delivered_quantity": flt(record.get("delivered_qty")),
			"billed_amount": flt(record.get("billed_amt")),
			"company": record.get("company"),
		}
		row["currency"] = frappe.get_cached_value("Company", row["company"], "default_currency")
		data.append(row)

	return data


def get_customer_details():
	details = frappe.get_all("Customer", fields=["name", "customer_name", "customer_group"])
	customer_details = {}
	for d in details:
		customer_details.setdefault(
			d.name, frappe._dict({"customer_name": d.customer_name, "customer_group": d.customer_group})
		)
	return customer_details


def get_item_details():
	details = frappe.db.get_all("Item", fields=["name", "item_name", "item_group"])
	item_details = {}
	for d in details:
		item_details.setdefault(d.name, frappe._dict({"item_name": d.item_name, "item_group": d.item_group}))
	return item_details


def get_sales_order_details(company_list, filters):
	db_so = frappe.qb.DocType("Sales Order")
	db_so_item = frappe.qb.DocType("Sales Order Item")

	query = (
		frappe.qb.from_(db_so)
		.inner_join(db_so_item)
		.on(db_so_item.parent == db_so.name)
		.select(
			db_so.name,
			db_so.customer,
			db_so.transaction_date,
			db_so.territory,
			db_so.project,
			db_so.company,
			db_so_item.item_code,
			db_so_item.description,
			db_so_item.qty,
			db_so_item.uom,
			db_so_item.base_rate,
			db_so_item.base_amount,
			db_so_item.delivered_qty,
			(db_so_item.billed_amt * db_so.conversion_rate).as_("billed_amt"),
		)
		.where(db_so.docstatus == 1)
		.where(db_so.company.isin(tuple(company_list)))
	)

	if filters.get("item_group"):
		query = query.where(db_so_item.item_group == filters.item_group)

	if filters.get("from_date"):
		query = query.where(db_so.transaction_date >= filters.from_date)

	if filters.get("to_date"):
		query = query.where(db_so.transaction_date <= filters.to_date)

	if filters.get("item_code"):
		query = query.where(db_so_item.item_code == filters.item_code)

	if filters.get("customer"):
		query = query.where(db_so.customer == filters.customer)

	return query.run(as_dict=1)


def get_chart_data(data):
	item_wise_sales_map = {}
	labels, datapoints = [], []

	for row in data:
		item_key = row.get("item_code")

		if item_key not in item_wise_sales_map:
			item_wise_sales_map[item_key] = 0

		item_wise_sales_map[item_key] = flt(item_wise_sales_map[item_key]) + flt(row.get("amount"))

	item_wise_sales_map = {
		item: value for item, value in (sorted(item_wise_sales_map.items(), key=lambda i: i[1], reverse=True))
	}

	for key in item_wise_sales_map:
		labels.append(key)
		datapoints.append(item_wise_sales_map[key])

	return {
		"data": {
			"labels": labels[:30],  # show max of 30 items in chart
			"datasets": [{"name": _("Total Sales Amount"), "values": datapoints[:30]}],
		},
		"type": "bar",
		"fieldtype": "Currency",
	}
