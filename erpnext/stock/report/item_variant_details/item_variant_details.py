# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns(filters.item)
	data = get_data(filters.item)
	return columns, data

def get_data(item):
	if not item:
		return []
	item_dicts = []

	item_doc = frappe.get_doc("Item", item)

	for variant in frappe.db.sql("""select name from `tabItem`
		where variant_of = %s""", item, as_dict=1):
		item_dict = frappe._dict({
			"variant_name": variant.name,
		})

		variant_doc = frappe.get_doc("Item", variant.name)

		for d in variant_doc.attributes:
			item_dict[d.attribute] = d.attribute_value

		# Open Orders
		open_sales_orders = frappe.db.sql("""
			select count(*) as count
			from `tabSales Order` so, `tabSales Order Item` so_item
			where so.name=so_item.parent
				and so.status = "To Deliver and Bill" and so_item.item_code = %s
		""", (variant.name), as_dict=1)

		item_dict["Open Orders"] = open_sales_orders[0]["count"]

		# Stock
		stock_details = frappe.db.sql("""
			select
				sum(planned_qty) as planned_qty,
				sum(actual_qty) as actual_qty,
				sum(projected_qty) as projected_qty
			from
				`tabBin`
			where
				item_code = %s
		""", (variant.name), as_dict=1)

		item_dict["Inventory"] = stock_details[0]["actual_qty"] or 0
		item_dict["In Production"] = stock_details[0]["planned_qty"] or 0
		item_dict["Available Selling"] = stock_details[0]["projected_qty"] or 0

		# Price
		buying = frappe.db.sql("""
			select
				avg(price_list_rate) as avg_rate
			from
				`tabItem Price`
			where
				item_code=%s and buying=1
			""", (variant.name), as_dict=1)

		selling = frappe.db.sql("""
			select
				avg(price_list_rate) as avg_rate
			from
				`tabItem Price`
			where
				item_code=%s and selling=1
			""", (variant.name), as_dict=1)

		item_dict["Cost"] = buying[0]["avg_rate"] or 0
		item_dict["Price"] = selling[0]["avg_rate"] or 0

		item_dicts.append(item_dict)
	return item_dicts

def get_columns(item):
	columns = [{
		"fieldname": "variant_name",
		"label": "Variant",
		"fieldtype": "Link",
		"options": "Item",
		"width": 200
	}]

	item_doc = frappe.get_doc("Item", item)

	for d in item_doc.attributes:
		columns.append(d.attribute + ":Data:100")

	columns += [_("Cost") + ":Currency:90", _("Price") + ":Currency:80",
		_("Inventory") + ":Float:100", _("In Production") + ":Float:100",
		_("Open Orders") + ":Float:100", _("Available Selling") + ":Float:100"
	]

	return columns
