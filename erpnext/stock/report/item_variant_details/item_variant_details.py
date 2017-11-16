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

	variant_results = frappe.db.sql("""select name from `tabItem`
		where variant_of = %s""", item, as_dict=1)
	variants = ",".join(['"' + variant['name'] + '"' for variant in variant_results])

	# Open Orders
	open_sales_orders = frappe.db.sql("""
		select
			count(*) as count,
			item_code
		from
			`tabSales Order Item`
		where
			qty > delivered_qty and
			item_code in ({variants})
	""".format(variants=variants), as_dict=1)

	oss = {}
	for d in open_sales_orders:
		oss[d["item_code"]] = d["count"]

	# Stock
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
	""".format(variants=variants), as_dict=1)

	sd = {}
	for d in stock_details:
		name = d["item_code"]
		sd[name] = {
			"Inventory" :d["actual_qty"],
			"In Production" :d["planned_qty"],
			"Available Selling" :d["projected_qty"]
		}

	# Price
	buying = frappe.db.sql("""
		select
			avg(price_list_rate) as avg_rate,
			item_code
		from
			`tabItem Price`
		where
			item_code in ({variants}) and buying=1
		""".format(variants=variants), as_dict=1)

	bu = {}
	for d in buying:
		bu[d["item_code"]] = d["avg_rate"]

	selling = frappe.db.sql("""
		select
			avg(price_list_rate) as avg_rate,
			item_code
		from
			`tabItem Price`
		where
			item_code in ({variants}) and selling=1
		""".format(variants=variants), as_dict=1)

	se = {}
	for d in selling:
		se[d["item_code"]] = d["avg_rate"]


	# Prepare dicts
	variant_dicts = [{"variant_name": d['name']} for d in variant_results]
	for item_dict in variant_dicts:
		name = item_dict["variant_name"]

		# Attributes
		variant_doc = frappe.get_doc("Item", name)
		for d in variant_doc.attributes:
			item_dict[d.attribute] = d.attribute_value

		item_dict["Open Orders"] = oss.get(name) or 0

		if sd.get(name):
			item_dict["Inventory"] = sd.get(name)["Inventory"] or 0
			item_dict["In Production"] = sd.get(name)["In Production"] or 0
			item_dict["Available Selling"] = sd.get(name)["Available Selling"] or 0
		else:
			item_dict["Inventory"] = item_dict["In Production"] = item_dict["Available Selling"] = 0

		item_dict["Avg. Buying Price List Rate"] = bu.get(name) or 0
		item_dict["Avg. Selling Price List Rate"] = se.get(name) or 0

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
