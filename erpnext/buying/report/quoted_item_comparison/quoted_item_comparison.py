# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cint
from frappe import _
from collections import defaultdict
from erpnext.setup.utils import get_exchange_rate

def execute(filters=None):
	if not filters:
		return [], []

	conditions = get_conditions(filters)
	supplier_quotation_data = get_data(filters, conditions)
	columns = get_columns()

	data, chart_data = prepare_data(supplier_quotation_data)

	return columns, data, None, chart_data

def get_conditions(filters):
	conditions = ""
	if filters.get("supplier_quotation"):
		conditions += " AND sqi.parent = %(supplier_quotation)s"

	if filters.get("request_for_quotation"):
		conditions += " AND sqi.request_for_quotation = %(request_for_quotation)s"

	if filters.get("supplier"):
		conditions += " AND sq.supplier in %(supplier)s"
	return conditions

def get_data(filters, conditions):
	if not filters.get("item_code"):
		return []

	supplier_quotation_data = frappe.db.sql("""SELECT
		sqi.parent, sqi.qty, sqi.rate, sqi.uom, sqi.request_for_quotation,
		sq.supplier
		FROM
			`tabSupplier Quotation Item` sqi,
			`tabSupplier Quotation` sq
		WHERE
			sqi.item_code = %(item_code)s
			AND sqi.parent = sq.name
			AND sqi.docstatus < 2
			AND sq.company = %(company)s
			AND sq.status != 'Expired'
			{0}""".format(conditions), filters, as_dict=1)

	return supplier_quotation_data

def prepare_data(supplier_quotation_data):
	out, suppliers, qty_list = [], [], []
	supplier_wise_map = defaultdict(list)
	supplier_qty_price_map = {}

	company_currency = frappe.db.get_default("currency")
	float_precision = cint(frappe.db.get_default("float_precision")) or 2

	for data in supplier_quotation_data:
		supplier = data.get("supplier")
		supplier_currency = frappe.db.get_value("Supplier", data.get("supplier"), "default_currency")

		if supplier_currency:
			exchange_rate = get_exchange_rate(supplier_currency, company_currency)
		else:
			exchange_rate = 1

		row = {
			"quotation": data.get("parent"),
			"qty": data.get("qty"),
			"price": flt(data.get("rate") * exchange_rate, float_precision),
			"uom": data.get("uom"),
			"request_for_quotation": data.get("request_for_quotation"),
		}

		# map for report view of form {'supplier1':[{},{},...]}
		supplier_wise_map[supplier].append(row)

		# map for chart preparation of the form {'supplier1': {'qty': 'price'}}
		if not supplier in supplier_qty_price_map:
			supplier_qty_price_map[supplier] = {}
		supplier_qty_price_map[supplier][row["qty"]] = row["price"]

		suppliers.append(supplier)
		qty_list.append(data.get("qty"))

	suppliers = list(set(suppliers))
	qty_list = list(set(qty_list))

	# final data format for report view
	for supplier in suppliers:
		supplier_wise_map[supplier][0].update({"supplier_name": supplier})
		for entry in supplier_wise_map[supplier]:
			out.append(entry)

	chart_data = prepare_chart_data(suppliers, qty_list, supplier_qty_price_map)

	return out, chart_data

def prepare_chart_data(suppliers, qty_list, supplier_qty_price_map):
	data_points_map = {}
	qty_list.sort()

	# create qty wise values map of the form {'qty1':[value1, value2]}
	for supplier in suppliers:
		entry = supplier_qty_price_map[supplier]
		for qty in qty_list:
			if not qty in data_points_map:
				data_points_map[qty] = []
			if qty in entry:
				data_points_map[qty].append(entry[qty])
			else:
				data_points_map[qty].append(None)

	dataset = []
	for qty in qty_list:
		datapoints = {
			"name": _("Price for Qty ") + str(qty),
			"values": data_points_map[qty]
		}
		dataset.append(datapoints)

	chart_data = {
		"data": {
			"labels": suppliers,
			"datasets": dataset
		},
		"type": "bar"
	}

	return chart_data

def get_columns():
	columns = [{
		"fieldname": "supplier_name",
		"label": _("Supplier"),
		"fieldtype": "Link",
		"options": "Supplier",
		"width": 200
	},
	{
		"fieldname": "quotation",
		"label": _("Supplier Quotation"),
		"fieldtype": "Link",
		"options": "Supplier Quotation",
		"width": 200
	},
	{
		"fieldname": "qty",
		"label": _("Quantity"),
		"fieldtype": "Float",
		"width": 80
	},
	{
		"fieldname": "price",
		"label": _("Price"),
		"fieldtype": "Currency",
		"options": "Company:company:default_currency",
		"width": 110
	},
	{
		"fieldname": "uom",
		"label": _("UOM"),
		"fieldtype": "Link",
		"options": "UOM",
		"width": 90
	},
	{
		"fieldname": "request_for_quotation",
		"label": _("Request for Quotation"),
		"fieldtype": "Link",
		"options": "Request for Quotation",
		"width": 200
	}
	]

	return columns