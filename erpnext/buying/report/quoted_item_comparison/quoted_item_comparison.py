# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import flt, cint
from collections import defaultdict
from erpnext.setup.utils import get_exchange_rate

def execute(filters=None):
	conditions = get_conditions(filters)
	data = get_data(filters, conditions)
	columns = get_columns()
	return columns, data

def get_data(filters, conditions):
	out, suppliers = [], []
	item = filters.get("item")

	if not item:
		return []

	company_currency = frappe.db.get_default("currency")
	float_precision = cint(frappe.db.get_default("float_precision")) or 2

	supplier_quotation_data = frappe.db.sql("""SELECT
		sqi.parent, sqi.qty, sqi.rate, sqi.uom, sqi.request_for_quotation,
		sq.supplier
		FROM
			`tabSupplier Quotation Item` sqi,
			`tabSupplier Quotation` sq
		WHERE
			sqi.item_code = '{0}'
			AND sqi.parent = sq.name
			AND sqi.docstatus < 2
			AND sq.company = '{1}'
			AND sq.status != 'Expired'
			{2}""".format(item, filters.get("company"), conditions), as_dict=1)

	supplier_wise_map = defaultdict(list)

	for data in supplier_quotation_data:
		supplier_currency = frappe.db.get_value("Supplier", data.get("supplier"), "default_currency")
		if supplier_currency:
			exchange_rate = get_exchange_rate(supplier_currency, company_currency)
		else:
			exchange_rate = 1

		row = {
			"quotation": data.get("parent"),
			"qty": data.get("qty"),
			"price": flt(data.get("rate") * exchange_rate, float_precision),
			"request_for_quotation": data.get("request_for_quotation"),
			"supplier": data.get("supplier") # used for chart generation
		}

		supplier_wise_map[data.supplier].append(row)
		suppliers.append(data.supplier)

	suppliers = set(suppliers)

	for supplier in suppliers:
		supplier_wise_map[supplier][0].update({"supplier_name": supplier})
		for entry in supplier_wise_map[supplier]:
			out.append(entry)

	return out

def get_conditions(filters):
	conditions = ""

	if filters.get("request_for_quotation"):
		conditions += " AND sqi.request_for_quotation = '{0}' ".format(filters.get("request_for_quotation"))

	return conditions


def get_columns():
	columns = [{
		"fieldname": "supplier_name",
		"label": "Supplier",
		"fieldtype": "Link",
		"options": "Supplier",
		"width": 200
	},
	{
		"fieldname": "quotation",
		"label": "Supplier Quotation",
		"fieldtype": "Link",
		"options": "Supplier Quotation",
		"width": 200
	},
	{
		"fieldname": "qty",
		"label": "Quantity",
		"fieldtype": "Float",
		"width": 80
	},
	{
		"fieldname": "price",
		"label": "Price",
		"fieldtype": "Currency",
		"options": "Company:company:default_currency",
		"width": 110
	},
	{
		"fieldname": "request_for_quotation",
		"label": "Request for Quotation",
		"fieldtype": "Link",
		"options": "Request for Quotation",
		"width": 200
	}
	]

	return columns