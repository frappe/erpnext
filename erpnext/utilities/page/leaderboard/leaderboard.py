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
		items = get_all_customers(filters, [], field)
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

def get_all_customers(filters, items, field, start=0, limit=20):
	"""return all customers"""

	customer_list = frappe.db.sql("""select A.customer, count(B.name) as item_count, sum(A.base_net_total) as base_net_total, sum(A.outstanding_amount) as outstanding_amount from 
            `tabSales Invoice` as A LEFT JOIN `tabSales Invoice Item` as B ON A.name = B.parent where A.docstatus != 2 group by A.customer """, as_dict=1)

	value = 0;
	for cust in customer_list:
		if field == "total_sales_amount":
			value = cust.base_net_total
		elif field == "receivable_amount_outstanding_amount":
			value = cust.outstanding_amount
		elif field == "total_item_purchased_qty":
			value = cust.item_count

		item_obj = {"name": cust.customer,	
			"total_item_purchased_qty": cust.item_count,
			"total_sales_amount": get_formatted_value(cust.base_net_total),
			"receivable_amount_outstanding_amount":get_formatted_value(cust.outstanding_amount),
			"href":"#Form/Customer/" + cust.customer,
			"value": value}
		items.append(item_obj)


	items.sort(key=lambda k: k['value'], reverse=True)
	return items

def get_all_items(doctype, filters, items, field, start=0, limit=20):
	"""return all items"""
	items_list = frappe.get_list(doctype, filters=filters, limit_start=start, limit_page_length=limit)

	for item in items_list:
		s_invoice = frappe.db.sql("""select name, qty, amount\
			from `tabSales Invoice Item`\
			where item_code = %s and docstatus != 2""", {item.name},as_dict=1)
		p_invoice = frappe.db.sql("""select name, qty, amount\
			from `tabPurchase Invoice Item`\
			where item_code = %s and docstatus != 2""", {item.name},as_dict=1)
		data = frappe.db.sql('''select actual_qty from `tabBin` where item_code = %s''', (item.name), as_list=1)
		stock_qty = destructure_tuple_of_tuples(data)


		invoice_list = [x['name'] for x in s_invoice]

		if len(invoice_list) > 0:
			item_count = frappe.db.sql('''select count(name) from `tabSales Invoice Item` where parent in (%s)''' % ", ".join(
				['%s'] * len(invoice_list)), tuple(invoice_list))
			value = 0
			if(field == "total_sales_amount"):
				value = sum([x['amount'] for x in s_invoice])
			elif(field == "total_sold_qty"):
				value = sum([x['qty'] for x in s_invoice])
			elif(field == "total_purchase_amount"):
				value = sum([x['amount'] for x in p_invoice])
			elif(field == "total_purchased_qty"):
				value = sum([x['qty'] for x in p_invoice])
			elif(field == "available_stock_qty"):
				value = stock_qty

			item_obj = {"name": item.name,
				"total_sales_amount": get_formatted_value(sum([x['amount'] for x in s_invoice])),
				"total_sold_qty": sum([x['qty'] for x in s_invoice]),
				"total_purchase_amount": get_formatted_value(sum([x['amount'] for x in p_invoice])),
				"total_purchased_qty": sum([x['qty'] for x in p_invoice]),
				"available_stock_qty": stock_qty,
				"href":"#Form/Customer/" + item.name,
				"value": value}
			items.append(item_obj)

	items.sort(key=lambda k: k['value'], reverse=True)
	return items

def get_all_suppliers(filters, items, field, start=0, limit=20):
	"""return all suppliers"""

	supplier_list = frappe.db.sql("""select A.supplier, count(B.name) as item_count, sum(A.base_net_total) as base_net_total, 
		sum(A.outstanding_amount) as outstanding_amount from `tabPurchase Invoice` as A LEFT JOIN `tabPurchase Invoice Item` as B ON A.name = B.parent where A.docstatus != 2 group by A.supplier """, as_dict=1)

	value = 0;
	for supp in supplier_list:
		if field == "total_purchase_amount":
			value = supp.base_net_total
		elif field == "payable_amount_outstanding_amount":
			value = supp.outstanding_amount
		elif field == "total_item_sold_qty":
			value = supp.item_count

		item_obj = {"name": supp.supplier,	
			"total_purchase_amount": supp.item_count,
			"payable_amount_outstanding_amount": get_formatted_value(supp.base_net_total),
			"total_item_sold_qty":get_formatted_value(supp.outstanding_amount),
			"href":"#Form/Supplier/" + supp.supplier,
			"value": value}
		items.append(item_obj)


	items.sort(key=lambda k: k['value'], reverse=True)
	return items


def get_all_sales_partner(filters, items, field, start=0, limit=20):
	"""return all sales partner"""

	sales_partner_list = frappe.db.sql("""select A.partner_name, A.commission_rate, B.target_qty, B.target_amount, sum(C.total_commission) as total_commission 
		from `tabSales Partner` as A inner join `tabTarget Detail` as B ON A.name = B.parent inner join `tabSales Invoice` as C ON C.sales_partner =
		A.partner_name group by A.partner_name""", as_dict=1)

	value = 0
	for sales_partner in sales_partner_list:
		print("Sales paer", sales_partner)
		if field == "commission_rate":
			value = sales_partner.commission_rate
		elif field == "target_qty":
			value = sales_partner.target_qty
		elif field == "target_amount":
			value = sales_partner.target_amount
		elif field == "total_sales_amount":
			value = sales_partner.total_commission

		item_obj = {"name": sales_partner.partner_name,
			"commission_rate": get_formatted_value(sales_partner.commission_rate),
			"target_qty": sales_partner.target_qty,
			"target_amount": get_formatted_value(sales_partner.target_amount),
			"total_sales_amount": get_formatted_value(sales_partner.total_commission),
			"href":"#Form/Sales Partner/" + sales_partner.partner_name,
			"value": value}
		items.append(item_obj)

	items.sort(key=lambda k: k['value'], reverse=True)
	return items

def get_all_sales_person(filters, items, field, start=0, limit=20):
	"""return all sales partner"""

	sales_person_list = frappe.db.sql('''select A.name, A.is_group, B.target_qty, B.target_amount, sum(C.allocated_amount) as allocated_amount from `tabSales Person` as 
            A inner join `tabTarget Detail` as B ON A.name = B.parent inner join `tabSales Team` as C ON C.sales_person = A.name group by A.name''', as_dict=1)
	value = 0
	for sales_person in sales_person_list:
		if not sales_person.is_group:
			if(field=="target_qty"):
				value=sales_person.target_qty
			elif(field=="target_amount"):
				value=sales_person.target_amount
			elif(field=="total_sales_amount"):
				value=sales_person.allocated_amount

			item_obj = {"name": sales_person.name,
				"target_qty": sales_person.target_qty,
				"target_amount": get_formatted_value(sales_person.target_amount),
				"total_sales_amount": get_formatted_value(sales_person.allocated_amount),
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
