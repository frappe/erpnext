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

	print('doctype', doctype, timespan, field, start)

	filters = {"modified":(">=", get_date_from_string(timespan))}
	items = []
	if doctype == "Customer":
		items = get_all_customers(doctype, filters, [], field)
	elif  doctype == "Item":
		items = get_all_items(doctype, filters, [], field)
	elif  doctype == "Supplier":
		items = get_all_suppliers(doctype, filters, [], field)
	elif  doctype == "Sales Partner":
		items = get_all_sales_partner(doctype, filters, [], field)

	if len(items) > 0:
		return items
	return []

def get_all_customers(doctype, filters, items, field, start=0, limit=20):
	"""return all customers"""

	x = frappe.get_list(doctype, filters=filters, limit_start=start, limit_page_length=limit)

	for val in x:
		y = dict(frappe.db.sql('''select name, grand_total from `tabSales Invoice` where customer = %s''', (val.name)))
		invoice_list = y.keys()
		if len(invoice_list) > 0:
			item_count = frappe.db.sql('''select count(name) from `tabSales Invoice Item` where parent in (%s)''' % ", ".join(
				['%s'] * len(invoice_list)), tuple(invoice_list))

			value = 0
			if(field=="total_amount"):
				value = sum(y.values())
			elif(field=="total_item_purchased"):
				value = sum(destructure_tuple_of_tuples(item_count))

			item_obj = {"name": val.name,
				"total_amount": get_formatted_value(sum(y.values())),
				"total_item_purchased": sum(destructure_tuple_of_tuples(item_count)),
				"href":"#Form/Customer/" + val.name,
				"value": value}
			items.append(item_obj)

	items.sort(key=lambda k: k['value'], reverse=True)
	return items

def get_all_items(doctype, filters, items, field, start=0, limit=20):
	"""return all items"""

	x = frappe.get_list(doctype, filters=filters, limit_start=start, limit_page_length=limit)
	for val in x:
		data = frappe.db.sql('''select item_code from `tabMaterial Request Item` where item_code = %s''', (val.name), as_list=1)
		requests = destructure_tuple_of_tuples(data)
		data = frappe.db.sql('''select price_list_rate from `tabItem Price` where item_code = %s''', (val.name), as_list=1)
		avg_price = get_avg(destructure_tuple_of_tuples(data))
		data = frappe.db.sql('''select item_code from `tabPurchase Invoice Item` where item_code = %s''', (val.name), as_list=1)
		purchases = destructure_tuple_of_tuples(data)

		value = 0
		if(field=="total_request"):
			value = len(requests)
		elif(field=="total_purchase"):
			value = len(purchases)
		elif(field=="avg_price"):
			value=avg_price
		item_obj = {"name": val.name,
			"total_request":len(requests),
			"total_purchase": len(purchases),
			"avg_price": get_formatted_value(avg_price),
			"href":"#Form/Item/" + val.name,
			"value": value}
		items.append(item_obj)

	print(items)

	items.sort(key=lambda k: k['value'], reverse=True)
	return items

def get_all_suppliers(doctype, filters, items, field, start=0, limit=20):
	"""return all suppliers"""

	x = frappe.get_list(doctype, filters=filters, limit_start=start, limit_page_length=limit)

	for val in x:

		info = get_dashboard_info(doctype, val.name)
		value = 0
		if(field=="annual_billing"):
			value = info["billing_this_year"]
		elif(field=="total_unpaid"):
			value = abs(info["total_unpaid"])

		item_obj = {"name": val.name,
			"annual_billing":  get_formatted_value(info["billing_this_year"]),
			"total_unpaid": get_formatted_value(abs(info["total_unpaid"])),
			"href":"#Form/Supplier/" + val.name,
			"value": value}
		items.append(item_obj)

	items.sort(key=lambda k: k['value'], reverse=True)
	return items

def get_all_sales_partner(doctype, filters, items, field, start=0, limit=20):
	"""return all sales partner"""

	x = frappe.get_list(doctype, fields=["name", "commission_rate", "modified"], filters=filters, limit_start=start, limit_page_length=limit)
	for val in x:
		y = frappe.db.sql('''select target_qty, target_amount from `tabTarget Detail` where parent = %s''', (val.name), as_dict=1)
		target_qty = sum([f["target_qty"] for f in y])
		target_amount = sum([f["target_amount"] for f in y])

		value = 0
		if(field=="commission_rate"):
			value = val.commission_rate
		elif(field=="target_qty"):
			value = target_qty
		elif(field=="target_amount"):
			value = target_qty

		item_obj = {"name": val.name,
			"commission_rate": get_formatted_value(val.commission_rate, False),
			"target_qty": target_qty,
			"target_amount": get_formatted_value(target_qty),
			"href":"#Form/Sales Partner/" + val.name,
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
