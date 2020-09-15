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

	data, chart_data = prepare_data(supplier_quotation_data, filters)
	message = get_message()

	return columns, data, message, chart_data

def get_conditions(filters):
	conditions = ""
	if filters.get("item_code"):
		conditions += " AND sqi.item_code = %(item_code)s"

	if filters.get("supplier_quotation"):
		conditions += " AND sqi.parent in %(supplier_quotation)s"

	if filters.get("request_for_quotation"):
		conditions += " AND sqi.request_for_quotation = %(request_for_quotation)s"

	if filters.get("supplier"):
		conditions += " AND sq.supplier in %(supplier)s"

	if not filters.get("include_expired"):
		conditions += " AND sq.status != 'Expired'"

	return conditions

def get_data(filters, conditions):
	supplier_quotation_data = frappe.db.sql("""SELECT
		sqi.parent, sqi.item_code, sqi.qty, sqi.rate, sqi.uom, sqi.request_for_quotation,
		sqi.lead_time_days, sq.supplier, sq.valid_till
		FROM
			`tabSupplier Quotation Item` sqi,
			`tabSupplier Quotation` sq
		WHERE
			sqi.parent = sq.name
			AND sqi.docstatus < 2
			AND sq.company = %(company)s
			AND sq.transaction_date between %(from_date)s and %(to_date)s
			{0}
			order by sq.transaction_date, sqi.item_code""".format(conditions), filters, as_dict=1)

	return supplier_quotation_data

def prepare_data(supplier_quotation_data, filters):
	out, suppliers, qty_list, chart_data = [], [], [], []
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
			"item_code": data.get('item_code'),
			"quotation": data.get("parent"),
			"qty": data.get("qty"),
			"price": flt(data.get("rate") * exchange_rate, float_precision),
			"uom": data.get("uom"),
			"request_for_quotation": data.get("request_for_quotation"),
			"valid_till": data.get('valid_till'),
			"lead_time_days": data.get('lead_time_days')
		}

		# map for report view of form {'supplier1':[{},{},...]}
		supplier_wise_map[supplier].append(row)

		# map for chart preparation of the form {'supplier1': {'qty': 'price'}}
		if filters.get("item_code"):
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

	if filters.get("item_code"):
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
	currency_symbol = frappe.db.get_value("Currency", frappe.db.get_default("currency"), "symbol")
	for qty in qty_list:
		datapoints = {
			"name": currency_symbol + " (Qty " + str(qty) + " )",
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
		"width": 150
	},
	{
		"fieldname": "item_code",
		"label": _("Item"),
		"fieldtype": "Link",
		"options": "Item",
		"width": 200
	},
	{
		"fieldname": "uom",
		"label": _("UOM"),
		"fieldtype": "Link",
		"options": "UOM",
		"width": 90
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
		"fieldname": "quotation",
		"label": _("Supplier Quotation"),
		"fieldtype": "Link",
		"options": "Supplier Quotation",
		"width": 200
	},
	{
		"fieldname": "valid_till",
		"label": _("Valid Till"),
		"fieldtype": "Date",
		"width": 100
	},
	{
		"fieldname": "lead_time_days",
		"label": _("Lead Time (Days)"),
		"fieldtype": "Int",
		"width": 100
	},
	{
		"fieldname": "request_for_quotation",
		"label": _("Request for Quotation"),
		"fieldtype": "Link",
		"options": "Request for Quotation",
		"width": 150
	}
	]

	return columns

def get_message():
	return  """<span class="indicator">
		Valid till : &nbsp;&nbsp;
		</span>
		<span class="indicator orange">
		Expires in a week or less
		</span>
		&nbsp;&nbsp;
		<span class="indicator red">
		Expires today / Already Expired
		</span>"""