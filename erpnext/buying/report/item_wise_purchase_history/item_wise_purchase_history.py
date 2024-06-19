# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
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
		{
			"label": _("Item Name"),
			"fieldtype": "Data",
			"fieldname": "item_name",
			"width": 140,
		},
		{
			"label": _("Item Group"),
			"fieldtype": "Link",
			"fieldname": "item_group",
			"options": "Item Group",
			"width": 120,
		},
		{
			"label": _("Description"),
			"fieldtype": "Data",
			"fieldname": "description",
			"width": 140,
		},
		{
			"label": _("Quantity"),
			"fieldtype": "Float",
			"fieldname": "quantity",
			"width": 120,
		},
		{
			"label": _("UOM"),
			"fieldtype": "Link",
			"fieldname": "uom",
			"options": "UOM",
			"width": 90,
		},
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
			"label": _("Purchase Order"),
			"fieldtype": "Link",
			"fieldname": "purchase_order",
			"options": "Purchase Order",
			"width": 160,
		},
		{
			"label": _("Transaction Date"),
			"fieldtype": "Date",
			"fieldname": "transaction_date",
			"width": 110,
		},
		{
			"label": _("Supplier"),
			"fieldtype": "Link",
			"fieldname": "supplier",
			"options": "Supplier",
			"width": 100,
		},
		{
			"label": _("Supplier Name"),
			"fieldtype": "Data",
			"fieldname": "supplier_name",
			"width": 140,
		},
		{
			"label": _("Supplier Group"),
			"fieldtype": "Link",
			"fieldname": "supplier_group",
			"options": "Supplier Group",
			"width": 120,
		},
		{
			"label": _("Project"),
			"fieldtype": "Link",
			"fieldname": "project",
			"options": "Project",
			"width": 100,
		},
		{
			"label": _("Received Quantity"),
			"fieldtype": "Float",
			"fieldname": "received_qty",
			"width": 150,
		},
		{
			"label": _("Billed Amount"),
			"fieldtype": "Currency",
			"fieldname": "billed_amt",
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

	supplier_details = get_supplier_details()
	item_details = get_item_details()
	purchase_order_records = get_purchase_order_details(company_list, filters)

	for record in purchase_order_records:
		supplier_record = supplier_details.get(record.supplier)
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
			"purchase_order": record.get("name"),
			"transaction_date": record.get("transaction_date"),
			"supplier": record.get("supplier"),
			"supplier_name": supplier_record.get("supplier_name"),
			"supplier_group": supplier_record.get("supplier_group"),
			"project": record.get("project"),
			"received_qty": flt(record.get("received_qty")),
			"billed_amt": flt(record.get("billed_amt")),
			"company": record.get("company"),
		}
		row["currency"] = frappe.get_cached_value("Company", row["company"], "default_currency")
		data.append(row)

	return data


def get_supplier_details():
	details = frappe.get_all("Supplier", fields=["name", "supplier_name", "supplier_group"])
	supplier_details = {}
	for d in details:
		supplier_details.setdefault(
			d.name,
			frappe._dict({"supplier_name": d.supplier_name, "supplier_group": d.supplier_group}),
		)
	return supplier_details


def get_item_details():
	details = frappe.db.get_all("Item", fields=["name", "item_name", "item_group"])
	item_details = {}
	for d in details:
		item_details.setdefault(d.name, frappe._dict({"item_name": d.item_name, "item_group": d.item_group}))
	return item_details


def get_purchase_order_details(company_list, filters):
	db_po = frappe.qb.DocType("Purchase Order")
	db_po_item = frappe.qb.DocType("Purchase Order Item")

	query = (
		frappe.qb.from_(db_po)
		.inner_join(db_po_item)
		.on(db_po_item.parent == db_po.name)
		.select(
			db_po.name,
			db_po.supplier,
			db_po.transaction_date,
			db_po.project,
			db_po.company,
			db_po_item.item_code,
			db_po_item.description,
			db_po_item.qty,
			db_po_item.uom,
			db_po_item.base_rate,
			db_po_item.base_amount,
			db_po_item.received_qty,
			(db_po_item.billed_amt * db_po.conversion_rate).as_("billed_amt"),
		)
		.where(db_po.docstatus == 1)
		.where(db_po.company.isin(tuple(company_list)))
	)

	for field in ("item_code", "item_group"):
		if filters.get(field):
			query = query.where(db_po_item[field] == filters[field])

	if filters.get("from_date"):
		query = query.where(db_po.transaction_date >= filters.from_date)

	if filters.get("to_date"):
		query = query.where(db_po.transaction_date <= filters.to_date)

	if filters.get("supplier"):
		query = query.where(db_po.supplier == filters.supplier)

	return query.run(as_dict=1)


def get_chart_data(data):
	item_wise_purchase_map = {}
	labels, datapoints = [], []

	for row in data:
		item_key = row.get("item_code")

		if item_key not in item_wise_purchase_map:
			item_wise_purchase_map[item_key] = 0

		item_wise_purchase_map[item_key] = flt(item_wise_purchase_map[item_key]) + flt(row.get("amount"))

	item_wise_purchase_map = {
		item: value
		for item, value in (sorted(item_wise_purchase_map.items(), key=lambda i: i[1], reverse=True))
	}

	for key in item_wise_purchase_map:
		labels.append(key)
		datapoints.append(item_wise_purchase_map[key])

	return {
		"data": {
			"labels": labels[:30],  # show max of 30 items in chart
			"datasets": [{"name": _("Total Purchase Amount"), "values": datapoints[:30]}],
		},
		"type": "bar",
		"fieldtype": "Currency",
	}
