# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals, print_function
import frappe
import json
from operator import itemgetter
from frappe.utils import add_to_date
from erpnext.accounts.party import get_dashboard_info
from erpnext.accounts.utils import get_currency_precision

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


# filters start
def filter_leaderboard_items(obj, items):
	"""return items based on seleted filters"""
	
	reverse = False if obj.selected_filter_item and obj.selected_filter_item["value"] == "ASC" else True
	# key : (x[field1], x[field2]) while sorting on 2 values
	filtered_list = []
	selected_field = obj.selected_filter_item and obj.selected_filter_item["field"]
	if selected_field:
		filtered_list  = sorted(items, key=itemgetter(selected_field), reverse=reverse)
		value = items[0].get(selected_field)

		allowed = isinstance(value, unicode) or isinstance(value, str)
		# now sort by length
		if allowed and '$' in value:
			filtered_list.sort(key= lambda x: len(x[selected_field]), reverse=reverse)
	
	# return only 10 items'
	return filtered_list[:10]

# filters end


# utils start
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

def get_formatted_value(value, add_symbol=True):
	"""return formatted value"""
	currency_precision = get_currency_precision() or 2
	if not add_symbol:
		return '{:.{pre}f}'.format(value, pre=currency_precision)
	
	company = frappe.db.get_default("company") or frappe.get_all("Company")[0].name
	currency = frappe.get_doc("Company", company).default_currency or frappe.boot.sysdefaults.currency;
	currency_symbol = frappe.db.get_value("Currency", currency, "symbol")
	return  currency_symbol + ' ' + '{:.{pre}f}'.format(value, pre=currency_precision)

# utils end


# get data
def get_all_customers(doctype, filters, items, start=0, limit=100):
	"""return all customers"""

	x = frappe.get_list(doctype, fields=["name", "modified"], filters=filters, limit_start=start, limit_page_length=limit)
	
	for val in x:
		y = dict(frappe.db.sql('''select name, grand_total from `tabSales Invoice` where customer = %s''', (val.name)))
		invoice_list = y.keys()
		if len(invoice_list) > 0:
			item_count = frappe.db.sql('''select count(name) from `tabSales Invoice Item` where parent in (%s)''' % ", ".join(
				['%s'] * len(invoice_list)), tuple(invoice_list))
			items.append({"title": val.name,
				"total_amount": get_formatted_value(sum(y.values())),
				"href":"#Form/Customer/" + val.name,
				"total_item_purchased": sum(destructure_tuple_of_tuples(item_count)),
				"modified": str(val.modified)})
	if len(x) > 99:
		start = start + 1
		return get_all_customers(doctype, filters, items, start=start)
	else:
		return items

def get_all_items(doctype, filters, items, start=0, limit=100):
	"""return all items"""

	x = frappe.get_list(doctype, fields=["name", "modified"], filters=filters, limit_start=start, limit_page_length=limit)
	for val in x:
		data = frappe.db.sql('''select item_code from `tabMaterial Request Item` where item_code = %s''', (val.name), as_list=1)
		requests = destructure_tuple_of_tuples(data)
		data = frappe.db.sql('''select price_list_rate from `tabItem Price` where item_code = %s''', (val.name), as_list=1)
		avg_price = get_avg(destructure_tuple_of_tuples(data))
		data = frappe.db.sql('''select item_code from `tabPurchase Invoice Item` where item_code = %s''', (val.name), as_list=1)
		purchases = destructure_tuple_of_tuples(data)
		
		items.append({"title": val.name,
			"total_request":len(requests),
			"total_purchase": len(purchases), "href":"#Form/Item/" + val.name,
			"avg_price": get_formatted_value(avg_price),
			"modified": val.modified})
	if len(x) > 99:
		return get_all_items(doctype, filters, items, start=start)
	else:
		return items

def get_all_suppliers(doctype, filters, items, start=0, limit=100):
	"""return all suppliers"""

	x = frappe.get_list(doctype, fields=["name", "modified"], filters=filters, limit_start=start, limit_page_length=limit)
	
	for val in x:
		info = get_dashboard_info(doctype, val.name)
		items.append({"title": val.name,
		"annual_billing":  get_formatted_value(info["billing_this_year"]),
		"total_unpaid": get_formatted_value(abs(info["total_unpaid"])),
		"href":"#Form/Supplier/" + val.name,
		"modified": val.modified})

	if len(x) > 99:
		return get_all_suppliers(doctype, filters, items, start=start)
	else:
		return items

def get_all_sales_partner(doctype, filters, items, start=0, limit=100):
	"""return all sales partner"""
	
	x = frappe.get_list(doctype, fields=["name", "commission_rate", "modified"], filters=filters, limit_start=start, limit_page_length=limit)
	for val in x:
		y = frappe.db.sql('''select target_qty, target_amount from `tabTarget Detail` where parent = %s''', (val.name), as_dict=1)
		target_qty = sum([f["target_qty"] for f in y])
		target_amount = sum([f["target_amount"] for f in y])
		items.append({"title": val.name,
			"commission_rate": get_formatted_value(val.commission_rate, False),
			"target_qty": target_qty,
			"target_amount": get_formatted_value(target_amount),
			"href":"#Form/Sales Partner/" + val.name,
			"modified": val.modified})
	if len(x) > 99:
		return get_all_sales_partner(doctype, filters, items, start=start)
	else:
		return items