# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.query_builder.functions import CurDate, DateDiff
from frappe.utils import cint
from frappe.utils.nestedset import get_descendants_of

from erpnext.stock.doctype.company_restriction.company_restriction import (
	get_allowed_companies_condition,
	get_allowed_masters_condition,
)


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
	sales_by_item = get_sales_details(filters)

	for territory in territories:
		subtree = {territory.name, *get_descendants_of("Territory", territory.name)}
		for item in items:
			row = {
				"territory": territory.name,
				"item_group": item.item_group,
				"item": item.item_code,
				"item_name": item.item_name,
			}

			last_sale = next(
				(d for d in sales_by_item.get(item.item_code, []) if d.territory in subtree), None
			)
			if last_sale:
				if last_sale.days_since_last_order <= cint(filters["days"]):
					continue

				row.update(
					{
						"customer": last_sale.customer,
						"last_order_date": last_sale.last_order_date,
						"qty": last_sale.qty,
						"days_since_last_order": last_sale.days_since_last_order,
					}
				)

			data.append(row)

	return data


def get_sales_details(filters):
	item_details_map = {}

	if filters["based_on"] not in ("Sales Order", "Sales Invoice"):
		frappe.throw(_("Invalid value {0} for 'Based On'").format(filters["based_on"]))

	parent = frappe.qb.DocType(filters["based_on"])
	child_doctype = "Sales Order Item" if filters["based_on"] == "Sales Order" else "Sales Invoice Item"
	child = frappe.qb.DocType(child_doctype)

	date_col = parent.transaction_date if filters["based_on"] == "Sales Order" else parent.posting_date

	# DateDiff is cross-database (DATEDIFF on MariaDB, date subtraction on postgres); CurDate()
	# renders the bare CURRENT_DATE keyword. Yields the integer number of days.
	days_since_last_order = DateDiff(CurDate(), date_col)

	query = (
		frappe.qb.from_(parent)
		.inner_join(child)
		.on(parent.name == child.parent)
		.select(
			parent.territory,
			parent.customer,
			child.item_group,
			child.item_code,
			child.qty,
			date_col.as_("last_order_date"),
			days_since_last_order.as_("days_since_last_order"),
		)
		.where(parent.docstatus == 1)
		.orderby(days_since_last_order)
	)

	if condition := get_allowed_companies_condition(parent.company, filters["based_on"]):
		query = query.where(condition)

	sales_data = query.run(as_dict=True)

	for d in sales_data:
		item_details_map.setdefault(d.item_code, []).append(d)

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

	item_filters = [filters_dict]
	if condition := get_allowed_masters_condition(frappe.qb.DocType("Item").name, "Item"):
		item_filters.append(condition)

	items = frappe.get_all(
		"Item",
		fields=["name", "item_group", "item_name", "item_code"],
		filters=item_filters,
		order_by="name",
	)

	return items
