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
	variants = None

	variant_results = frappe.db.sql("""select name from `tabItem`
		where variant_of = %s""", item, as_dict=1)
	if not variant_results:
		frappe.msgprint(_("There isn't any item variant for the selected item"))
		return []
	else:
		variants = ", ".join([frappe.db.escape(variant['name']) for variant in variant_results])

	order_count_map = get_open_sales_orders_map(variants)
	stock_details_map = get_stock_details_map(variants)
	buying_price_map = get_buying_price_map(variants)
	selling_price_map = get_selling_price_map(variants)
	attr_val_map = get_attribute_values_map(variants)

	attribute_list = [d[0] for d in frappe.db.sql("""select attribute
		from `tabItem Variant Attribute`
		where parent in ({variants}) group by attribute""".format(variants=variants))]

	# Prepare dicts
	variant_dicts = [{"variant_name": d['name']} for d in variant_results]
	for item_dict in variant_dicts:
		name = item_dict["variant_name"]

		for d in attribute_list:
			attr_dict = attr_val_map[name]
			if attr_dict and attr_dict.get(d):
				item_dict[d] = attr_val_map[name][d]

		item_dict["Open Orders"] = order_count_map.get(name) or 0

		if stock_details_map.get(name):
			item_dict["Inventory"] = stock_details_map.get(name)["Inventory"] or 0
			item_dict["In Production"] = stock_details_map.get(name)["In Production"] or 0
			item_dict["Available Selling"] = stock_details_map.get(name)["Available Selling"] or 0
		else:
			item_dict["Inventory"] = item_dict["In Production"] = item_dict["Available Selling"] = 0

		item_dict["Avg. Buying Price List Rate"] = buying_price_map.get(name) or 0
		item_dict["Avg. Selling Price List Rate"] = selling_price_map.get(name) or 0

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

	columns += [_("Avg. Buying Price List Rate") + ":Currency:110", _("Avg. Selling Price List Rate") + ":Currency:110",
		_("Inventory") + ":Float:100", _("In Production") + ":Float:100",
		_("Open Orders") + ":Float:100", _("Available Selling") + ":Float:100"
	]

	return columns

def get_open_sales_orders_map(variants):
	open_sales_orders = frappe.db.sql("""
		select
			count(*) as count,
			item_code
		from
			`tabSales Order Item`
		where
			docstatus = 1 and
			qty > ifnull(delivered_qty, 0) and
			item_code in ({variants})
		group by
			item_code
	""".format(variants=variants), as_dict=1)

	order_count_map = {}
	for d in open_sales_orders:
		order_count_map[d["item_code"]] = d["count"]

	return order_count_map

def get_stock_details_map(variants):
	stock_details = frappe.db.sql("""
		select
			sum(planned_qty) as planned_qty,
			sum(actual_qty) as actual_qty,
			sum(projected_qty) as projected_qty,
			item_code
		from
			`tabBin`
		where
			item_code in ({variants})
		group by
			item_code
	""".format(variants=variants), as_dict=1)

	stock_details_map = {}
	for d in stock_details:
		name = d["item_code"]
		stock_details_map[name] = {
			"Inventory" :d["actual_qty"],
			"In Production" :d["planned_qty"],
			"Available Selling" :d["projected_qty"]
		}

	return stock_details_map

def get_buying_price_map(variants):
	buying = frappe.db.sql("""
		select
			avg(price_list_rate) as avg_rate,
			item_code
		from
			`tabItem Price`
		where
			item_code in ({variants}) and buying=1
		group by
			item_code
		""".format(variants=variants), as_dict=1)

	buying_price_map = {}
	for d in buying:
		buying_price_map[d["item_code"]] = d["avg_rate"]

	return buying_price_map

def get_selling_price_map(variants):
	selling = frappe.db.sql("""
		select
			avg(price_list_rate) as avg_rate,
			item_code
		from
			`tabItem Price`
		where
			item_code in ({variants}) and selling=1
		group by
			item_code
		""".format(variants=variants), as_dict=1)

	selling_price_map = {}
	for d in selling:
		selling_price_map[d["item_code"]] = d["avg_rate"]

	return selling_price_map

def get_attribute_values_map(variants):
	list_attr = frappe.db.sql("""
		select
			attribute, attribute_value, parent
		from
			`tabItem Variant Attribute`
		where
			parent in ({variants})
		""".format(variants=variants), as_dict=1)

	attr_val_map = {}
	for d in list_attr:
		name = d["parent"]
		if not attr_val_map.get(name):
			attr_val_map[name] = {}

		attr_val_map[name][d["attribute"]] = d["attribute_value"]

	return attr_val_map
