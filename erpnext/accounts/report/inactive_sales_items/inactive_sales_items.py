# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import cint


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	columns = [
		{
			"fieldname": "territory",
			"fieldtype": "Link",
			"label": _("Territory"),
			"options": "Territory",
			"width": 100,
		},
		{
			"fieldname": "item_group",
			"fieldtype": "Link",
			"label": _("Item Group"),
			"options": "Item Group",
			"width": 150,
		},
		{"fieldname": "item", "fieldtype": "Link", "options": "Item", "label": _("Item"), "width": 150},
		{"fieldname": "item_name", "fieldtype": "Data", "label": _("Item Name"), "width": 150},
		{
			"fieldname": "customer",
			"fieldtype": "Link",
			"label": _("Customer"),
			"options": "Customer",
			"width": 100,
		},
		{
			"fieldname": "last_order_date",
			"fieldtype": "Date",
			"label": _("Last Order Date"),
			"width": 100,
		},
		{"fieldname": "qty", "fieldtype": "Float", "label": _("Quantity"), "width": 100},
		{
			"fieldname": "days_since_last_order",
			"fieldtype": "Int",
			"label": _("Days Since Last Order"),
			"width": 100,
		},
	]

	return columns


def get_data(filters):
	data = []
	items = get_items(filters)
	territories = get_territories(filters)
	sales_invoice_data = get_sales_details(filters)

	for territory in territories:
		for item in items:
			row = {
				"territory": territory.name,
				"item_group": item.item_group,
				"item": item.item_code,
				"item_name": item.item_name,
			}

			if sales_invoice_data.get((territory.name, item.item_code)):
				item_obj = sales_invoice_data[(territory.name, item.item_code)]
				if item_obj.days_since_last_order > cint(filters["days"]):
					row.update(
						{
							"territory": item_obj.territory,
							"customer": item_obj.customer,
							"last_order_date": item_obj.last_order_date,
							"qty": item_obj.qty,
							"days_since_last_order": item_obj.days_since_last_order,
						}
					)
				else:
					continue

			data.append(row)

	return data


def get_sales_details(filters):
	data = []
	item_details_map = {}

	date_field = "s.transaction_date" if filters["based_on"] == "Sales Order" else "s.posting_date"

	sales_data = frappe.db.sql(
		"""
		select s.territory, s.customer, si.item_group, si.item_code, si.qty, {date_field} as last_order_date,
		DATEDIFF(CURDATE(), {date_field}) as days_since_last_order
		from `tab{doctype}` s, `tab{doctype} Item` si
		where s.name = si.parent and s.docstatus = 1
		order by days_since_last_order """.format(  # nosec
			date_field=date_field, doctype=filters["based_on"]
		),
		as_dict=1,
	)

	for d in sales_data:
		item_details_map.setdefault((d.territory, d.item_code), d)

	return item_details_map


def get_territories(filters):

	filter_dict = {}
	if filters.get("territory"):
		filter_dict.update({"name": filters["territory"]})

	territories = frappe.get_all("Territory", fields=["name"], filters=filter_dict)

	return territories


def get_items(filters):
	filters_dict = {"disabled": 0, "is_stock_item": 1}

	if filters.get("item_group"):
		filters_dict.update({"item_group": filters["item_group"]})

	if filters.get("item"):
		filters_dict.update({"name": filters["item"]})

	items = frappe.get_all(
		"Item",
		fields=["name", "item_group", "item_name", "item_code"],
		filters=filters_dict,
		order_by="name",
	)

	return items
