# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals, print_function
import frappe
import os
import json
from operator import itemgetter
import ast
from frappe.utils import add_to_date
from erpnext.accounts.party import get_dashboard_info

@frappe.whitelist()
def get_leaderboard(obj):
	"""return top 10 items for that doctype based on conditions"""
	obj = frappe._dict(json.loads(obj))

	doctype = obj.selected_doctype
	timeline = obj.selected_timeline
	
	filters = {"modified":(">=", get_date_from_string(timeline))}
	items = []
	
	if doctype == "Customer":		
		items = get_all_customers(doctype, filters, [])
	elif  doctype == "Item":		
		items = get_all_items(doctype, filters, [])
	elif  doctype == "Supplier":		
		items = get_all_suppliers(doctype, filters, [])
	elif  doctype == "Sales Partner":		
		items = get_all_sales_partner(doctype, filters, [])
	
	if len(items) > 0:
		return filter_leaderboard_items(obj, items)
	return []


#filters start
def filter_leaderboard_items(obj, items):
	"""return items based on seleted filters"""

	print(obj)
	reverse = False if obj.selected_filter_item and obj.selected_filter_item["value"] == "ASC" else True

	# key : (x[field1], x[field2]) while sorting on 2 values
	filtered_list = []

	if obj.selected_filter_item and obj.selected_filter_item["field"]:
		filtered_list  = filtered_list + sorted(items, key=itemgetter(obj.selected_filter_item["field"]), reverse=reverse)
	else:
		key = get_filter_list(obj.selected_filter)
		filtered_list  = filtered_list + sorted(items, key=itemgetter(*key), reverse=reverse)

	# return only 10 items'
	return filtered_list[:10]
#filters end


#utils start
def destructure_tuple_of_tuples(tup_of_tup):
	"""return tuple(tuples) as list"""
	return [y for x in tup_of_tup for y in x]

def get_date_from_string(seleted_timeline):
	"""return string for ex:this week as date:string"""
	days = months = years = 0 
	if "month" == seleted_timeline.lower():
		months = -1
	elif "quarter" == seleted_timeline.lower():
		months = -3
	elif "year" == seleted_timeline.lower():
		years = -1
	else:
		days = -7

	return add_to_date(None, years=years, months=months, days=days, as_string=True, as_datetime=True)

def get_filter_list(selected_filter):
	"""return list of keys"""
	return map((lambda y : y["field"]), filter(lambda x : not (x["field"] == "title" or x["field"] == "modified"), selected_filter))

def get_avg(items):
	"""return avg of list items"""
	length = len(items)
	if length > 0:
		return sum(items) / length
	return 0
#utils end


# get data
def get_all_customers(doctype, filters, items, start=0, limit=100):
	"""return all customers based on seleted doctype"""

	x = frappe.get_list(doctype, fields=["name", "modified"], filters=filters, limit_start=start, limit_page_length=limit)
	
	for val in x:
		y = dict(frappe.db.sql('''select name, grand_total from `tabSales Invoice` where customer = %s''', (val.name)))
		invoice_list = y.keys()

		if len(invoice_list) > 0:
			item_count = frappe.db.sql('''select count(name) from `tabSales Invoice Item` where parent in (%s)''' % ", ".join(
				['%s'] * len(invoice_list)), tuple(invoice_list))
			items.append({"title": val.name, "total_amount": sum(y.values()), 
				"href":"#Form/Customer/" + val.name, 
				"total_item_purchased": sum(destructure_tuple_of_tuples(item_count)), 
				"modified": str(val.modified)})
	if len(x) > 99:
		start = start + 1
		return get_all_customers(doctype, filters, items, start=start)
	else:
		print([x["title"] for x in items])
		return items 

def get_all_items(doctype, filters, items, start=0, limit=100):
	"""return all items based on seleted doctype"""

	x = frappe.get_list(doctype, fields=["name", "modified"], filters=filters, limit_start=start, limit_page_length=limit)
	for val in x:
		y = frappe.db.sql('''select item_code from `tabMaterial Request Item` where item_code = %s''', (val.name), as_list=1)
		requests = destructure_tuple_of_tuples(y)
		y = frappe.db.sql('''select price_list_rate from `tabItem Price` where item_code = %s''', (val.name), as_list=1)
		avg_price = get_avg(destructure_tuple_of_tuples(y))
		y = frappe.db.sql('''select item_code from `tabPurchase Invoice Item` where item_code = %s''', (val.name), as_list=1)
		purchases = destructure_tuple_of_tuples(y)
		items.append({"title": val.name, "total_request":len(requests), 
			"total_purchase": len(purchases), "href":"#Form/Item/" + val.name,  
			"avg_price": avg_price, "modified": val.modified})
	if len(x) > 99:
		return get_all_items(doctype, filters, items, start=start)
	else:
		return items

def get_all_suppliers(doctype, filters, items, start=0, limit=100):
	"""return all items based on seleted doctype"""

	x = frappe.get_list(doctype, fields=["name", "modified"], filters=filters, limit_start=start, limit_page_length=limit)
	
	for val in x:
		info = get_dashboard_info(doctype, val.name)
		items.append({"title": val.name, "annual_billing": info["billing_this_year"], 
		"total_unpaid": info["total_unpaid"], 
		"href":"#Form/Supplier/" + val.name, "modified": val.modified})

	if len(x) > 99:
		return get_all_suppliers(doctype, filters, items, start=start)
	else:
		return items

def get_all_sales_partner(doctype, filters, items, start=0, limit=100):
	"""return all items based on seleted doctype"""
	
	x = frappe.get_list(doctype, fields=["name", "commission_rate", "modified"], filters=filters, limit_start=start, limit_page_length=limit)
	for val in x:
		y = frappe.db.sql('''select target_qty, target_amount from `tabTarget Detail` where parent = %s''', (val.name), as_dict=1)
		target_qty = sum([f["target_qty"] for f in y])
		target_amount = sum([f["target_amount"] for f in y])
		items.append({"title": val.name, "commission_rate":val.commission_rate,
			"target_qty": target_qty, "target_amount":target_amount, 
			"href":"#Form/Sales Partner/" + val.name, "modified": val.modified})
	if len(x) > 99:
		return get_all_sales_partner(doctype, filters, items, start=start)
	else:
		return items