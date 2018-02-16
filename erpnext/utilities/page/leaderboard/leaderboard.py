# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals, print_function
import frappe
import json
from operator import itemgetter
from frappe.utils import add_to_date, fmt_money
from erpnext.accounts.party import get_dashboard_info
from erpnext.accounts.utils import get_currency_precision

@frappe.whitelist()
def get_leaderboard(doctype, timespan, field, start=0):
	"""return top 10 items for that doctype based on conditions"""

	filters = {"modified":(">=", get_date_from_string(timespan))}
	items = []
	if doctype == "Customer":
		items = get_all_customers(timespan, filters, [], field)
	elif  doctype == "Item":
		items = get_all_items(doctype, filters, [], field)
	elif  doctype == "Supplier":
		items = get_all_suppliers(filters, [], field)
	elif  doctype == "Sales Partner":
		items = get_all_sales_partner(filters, [], field)
	elif doctype == "Sales Person":
		items = get_all_sales_person(filters, [], field)

	if len(items) > 0:
		return items
	return []

def get_all_customers(timespan, filters, items,  field, start=0, limit=20):
	"""return all customers"""

	customer_list = frappe.db.sql("""select A.customer, count(B.name) as total_item_purchased_qty, sum(A.base_net_total) as total_sales_amount, sum(A.outstanding_amount) as receivable_amount_outstanding_amount from 
            `tabSales Invoice` as A LEFT JOIN `tabSales Invoice Item` as B ON A.name = B.parent where A.docstatus = 1 group by A.customer  """, as_dict=1)

	value = 0;
	for cust in customer_list:
		if field in ("total_item_purchased_qty","total_sales_amount","receivable_amount_outstanding_amount"):
			value = cust[field]
			item_obj = {"name": cust.customer,	
				field: cust[field],
				"href":"#Form/Customer/" + cust.customer,
				"value": value}
			items.append(item_obj)


	items.sort(key=lambda k: k['value'], reverse=True)
	return items


def get_all_items(doctype, filters, items, field, start=0, limit=20):
	"""return all items"""
	item_sales = frappe.db.sql("""
		select
			A.name, sum(B.qty) as total_sold_qty,
			sum(B.amount) as total_sales_amount
		from `tabItem` as A  join `tabSales Order Item` as B on A.name = B.item_code
		group by
            A.name""", as_dict=1)
	item_purchase = frappe.db.sql("""select A.name, sum(B.qty) as total_purchased_qty, sum(B.amount) as total_purchase_amount from `tabItem` as A  join `tabPurchase Invoice Item` as B on A.name = B.item_code group by
            A.name""", as_dict=1)
	available_stock = frappe.db.sql("""select A.name, sum(B.actual_qty) as available_stock_qty from `tabItem` as A  join `tabBin` as B on A.name = B.item_code group by A.name""", as_dict=1)

	for sales in item_sales:
		if field in ("total_sales_amount", "total_sold_qty"):
			value = sales[field]

			item_obj = {"name": sales.name,
				field: sales[field],
				"href":"#Form/Customer/" + sales.name,
				"value": value}
			items.append(item_obj)

	for purchase in item_purchase:
		if field in ("total_purchase_amount", "total_purchased_qty"):
			value = purchase[field]
			
			item_obj = {"name": purchase.name,
				field: purchase[field],
				"href":"#Form/Customer/" + purchase.name,
				"value": value}
			items.append(item_obj)

	for stock_value in available_stock:
		if field in ("available_stock_qty"):
			value = stock_value[field]
			
			item_obj = {"name": stock_value.name,
				field: stock_value[field],
				"href":"#Form/Customer/" + stock_value.name,
				"value": value}
			items.append(item_obj)

	items.sort(key=lambda k: k['value'], reverse=True)
	return items
def get_all_suppliers(filters, items, field, start=0, limit=20):
	"""return all suppliers"""

	supplier_list = frappe.db.sql("""select A.supplier, count(B.name) as total_item_sold_qty, sum(A.base_net_total) as total_purchase_amount, 
		sum(A.outstanding_amount) as payable_amount_outstanding_amount from `tabPurchase Invoice` as A LEFT JOIN `tabPurchase Invoice Item` as B ON A.name = B.parent where A.docstatus = 1 group by A.supplier """, as_dict=1)

	value = 0;
	for supp in supplier_list:
		if field in ("total_purchase_amount","payable_amount_outstanding_amount","total_item_sold_qty"):
			value = supp[field]

		item_obj = {"name": supp.supplier,	
			field: supp[field],
			"href":"#Form/Supplier/" + supp.supplier,
			"value": value}
		items.append(item_obj)
	items.sort(key=lambda k: k['value'], reverse=True)
	return items


def get_all_sales_partner(filters, items, field, start=0, limit=20):
	"""return all sales partner"""

	sales_partner_list = frappe.db.sql("""select A.partner_name, A.commission_rate, B.target_qty, B.target_amount, sum(C.total_commission) as total_sales_amount 
		from `tabSales Partner` as A inner join `tabTarget Detail` as B ON A.name = B.parent inner join `tabSales Invoice` as C ON C.sales_partner =
		A.partner_name where C.docstatus = 1 group by A.partner_name""", as_dict=1)

	value = 0
	for sales_partner in sales_partner_list:
		if field in ("commission_rate", "target_qty", "target_amount","total_sales_amount"):
			value = sales_partner[field]

		item_obj = {"name": sales_partner.partner_name,
			field: sales_partner[field],
			"href":"#Form/Sales Partner/" + sales_partner.partner_name,
			"value": value}
		items.append(item_obj)

	items.sort(key=lambda k: k['value'], reverse=True)
	return items

def get_all_sales_person(filters, items, field, start=0, limit=20):
	"""return all sales partner"""

	sales_person_list = frappe.db.sql('''select A.name, A.is_group, B.target_qty, B.target_amount, sum(C.allocated_amount) as total_sales_amount from `tabSales Person` as 
            A inner join `tabTarget Detail` as B ON A.name = B.parent inner join `tabSales Team` as C ON C.sales_person = A.name group by A.name''', as_dict=1)
	value = 0
	for sales_person in sales_person_list:
		if not sales_person.is_group:
			if field in ("target_qty", "target_amount", "total_sales_amount"):
				value=sales_person[field]

			item_obj = {"name": sales_person.name,
				field: sales_person[field],
				"href":"#Form/Sales Partner/" + sales_person.name,
				"value": value}
			items.append(item_obj)

	items.sort(key=lambda k: k['value'], reverse=True)
	return items
	
def destructure_tuple_of_tuples(tup_of_tup):
	"""return tuple(tuples) as list"""
	return [y for x in tup_of_tup for y in x]

def get_date_from_string(seleted_timespan):
	"""return string for ex:this week as date:string"""
	days = months = years = 0
	if "month" == seleted_timespan.lower():
		months = -1
	elif "quarter" == seleted_timespan.lower():
		months = -3
	elif "year" == seleted_timespan.lower():
		years = -1
	else:
		days = -7

	return add_to_date(None, years=years, months=months, days=days, as_string=True, as_datetime=True)

def get_filter_list(selected_filter):
	"""return list of keys"""
	return map((lambda y : y["field"]), filter(lambda x : not (x["field"] == "name" or x["field"] == "modified"), selected_filter))

def get_avg(items):
	"""return avg of list items"""
	length = len(items)
	if length > 0:
		return sum(items) / length
	return 0

def get_formatted_value(value, add_symbol=True):
	"""return formatted value"""
	if not add_symbol:
		return '{:.{pre}f}'.format(value, pre=(get_currency_precision() or 2))
	currency_precision = get_currency_precision() or 2
	company = frappe.db.get_default("company")
	currency = frappe.get_doc("Company", company).default_currency or frappe.boot.sysdefaults.currency
	return fmt_money(value, currency_precision, currency)
