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
	if field == "total_sales_amount":
		select_field = "sum(sales_order_item.base_net_amount)"
	elif field == "total_item_purchased_qty":
		select_field = "count(sales_order_item.name)"
	elif field == "receivable_amount_outstanding_amount":
		return frappe.db.sql("""
			select sales_invoice.customer as name, sum(sales_invoice.outstanding_amount) as value
	        FROM `tabSales Invoice` as sales_invoice
	        where sales_invoice.docstatus = 1
	        group by sales_invoice.customer
	        order by value DESC
	        limit 20""", as_dict=1)

	return frappe.db.sql("""
		select sales_order.customer as name, {0} as value
        FROM `tabSales Order` as sales_order LEFT JOIN `tabSales Order Item`
        	as sales_order_item ON sales_order.name = sales_order_item.parent
        where sales_order.docstatus = 1
        group by sales_order.customer
        order by value DESC
        limit 20""".format(select_field), as_dict=1)




def get_all_items(doctype, filters, items, field, start=0, limit=20):
	"""return all items"""
	if field == "total_sales_amount":
		select_field = "sum(B.amount)"
		select_doctype = "`tabSales Order Item`"
	if field == "total_purchase_amount":
		select_field = "sum(B.amount)"
		select_doctype = "`tabPurchase Order Item`"
	if field == "total_sold_qty":
		select_field = "sum(B.qty)"
		select_doctype = "`tabSales Order Item`"
	if field == "total_purchased_qty":
		select_field = "sum(B.qty)"
		select_doctype = "`tabPurchase Order Item`"
	if field == "available_stock_qty":
		select_field = "sum(B.actual_qty)"
		select_doctype = "`tabBin`"
	return frappe.db.sql("""select
			A.name as name , {0} as value
		from `tabItem` as A  join {1} as B on A.name = B.item_code
		group by A.name""".format(select_field, select_doctype), as_dict=1)
	
def get_all_suppliers(filters, items, field, start=0, limit=20):
	"""return all suppliers"""

	if field == "total_purchase_amount":
		select_field = "sum(purchase_order_item.base_net_amount)"
	elif field == "total_item_sold_qty":
		select_field = "count(purchase_order_item.name)"
	elif field == "payable_amount_outstanding_amount":
		return frappe.db.sql("""
			select purchase_invoice.supplier as name, sum(purchase_invoice.outstanding_amount) as value
	        FROM `tabPurchase Invoice` as purchase_invoice
	        where purchase_invoice.docstatus = 1
	        group by purchase_invoice.supplier
	        order by value DESC
	        limit 20""", as_dict=1)

	return frappe.db.sql("""
		select purchase_order.supplier as name, {0} as value
        FROM `tabPurchase Order` as purchase_order LEFT JOIN `tabPurchase Order Item`
        	as purchase_order_item ON purchase_order.name = purchase_order_item.parent
        where purchase_order.docstatus = 1
        group by purchase_order.supplier
        order by value DESC
        limit 20""".format(select_field), as_dict=1)



def get_all_sales_partner(filters, items, field, start=0, limit=20):
	"""return all sales partner"""

	if field == "commission_rate":
		select_field = "A.commission_rate"
	elif field == "target_qty":
		select_field = "B.target_qty"
	elif field == "target_amount":
		select_field = "B.target_amount"
	elif field == "total_sales_amount":
		select_field = "sum(C.total_commission)"

	return frappe.db.sql("""select A.partner_name as name, {0} as value
		from 
			`tabSales Partner` as A inner join `tabTarget Detail` as B ON A.name = B.parent 
		inner join 
			`tabSales Invoice` as C ON C.sales_partner = A.name
	 	where 
	 		C.docstatus = 1 
	 	group by 
	 		A.partner_name
	 	order by value DESC
	 	limit 20""".format(select_field), as_dict=1)


def get_all_sales_person(filters, items, field, start=0, limit=20):
	"""return all sales partner"""


	
	if field == "target_qty":
		select_field = "B.target_qty"
	elif field == "target_amount":
		select_field = "B.target_amount"
	elif field == "total_sales_amount":
		select_field = "sum(C.allocated_amount)"

	return frappe.db.sql("""select A.name as name, {0} as value
		from 
			`tabSales Person` as A 
		inner join 
			`tabTarget Detail` as B ON A.name = B.parent 
		inner join 
			`tabSales Team` as C ON C.sales_person = A.name 
		where A.is_group = 0
		group by A.name
	 	order by value DESC
	 	limit 20""".format(select_field), as_dict=1)


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
