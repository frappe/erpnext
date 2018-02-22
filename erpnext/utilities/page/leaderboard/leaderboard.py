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
def get_leaderboard(doctype, timespan, company, field, start=0):
	"""return top 10 items for that doctype based on conditions"""
	filters = get_date_from_string(timespan)
	items = []
	if doctype == "Customer":
		items = get_all_customers(filters, company, [], field)
	elif  doctype == "Item":
		items = get_all_items(filters, [], field)
	elif  doctype == "Supplier":
		items = get_all_suppliers(filters, company, [], field)
	elif  doctype == "Sales Partner":
		items = get_all_sales_partner(filters, [], field)
	elif doctype == "Sales Person":
		items = get_all_sales_person(filters,  [], field)

	if len(items) > 0:
		return items
	return []

def get_all_customers(filters, company, items,  field, start=0, limit=20):
	"""return all customers"""
	if field == "total_sales_amount":
		select_field = "sum(sales_order_item.base_net_amount)"
	elif field == "total_item_purchased_qty":
		select_field = "count(sales_order_item.name)"
	elif field == "receivable_amount_outstanding_amount":
		return frappe.db.sql("""
			select sales_invoice.customer as name, sum(sales_invoice.outstanding_amount) as value
	        FROM `tabSales Invoice` as sales_invoice
	        where sales_invoice.docstatus = 1 and sales_invoice.modified >= "{0}" and sales_invoice.company = "{1}"
	        group by sales_invoice.customer
	        order by value DESC
	        limit {2}""".format(filters, company, limit), as_dict=1)

	return frappe.db.sql("""
		select sales_order.customer as name, {0} as value
        FROM `tabSales Order` as sales_order LEFT JOIN `tabSales Order Item`
        	as sales_order_item ON sales_order.name = sales_order_item.parent
        where sales_order.docstatus = 1  and sales_order.modified >= "{1}" and sales_order.company = "{2}"
        group by sales_order.customer
        order by value DESC
        limit {3}""".format(select_field, filters, company, limit), as_dict=1)




def get_all_items(filters, items, field, start=0, limit=20):
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
			item.name as name , {0} as value
		from `tabItem` as item  join {1} as B on item.name = B.item_code and item.modified >= "{2}"
		group by item.name""".format(select_field, select_doctype, filters), as_dict=1)

def get_all_suppliers(filters, company, items, field, start=0, limit=20):
	"""return all suppliers"""

	if field == "total_purchase_amount":
		select_field = "sum(purchase_order_item.base_net_amount)"
	elif field == "total_item_sold_qty":
		select_field = "count(purchase_order_item.name)"
	elif field == "payable_amount_outstanding_amount":
		return frappe.db.sql("""
			select purchase_invoice.supplier as name, sum(purchase_invoice.outstanding_amount) as value
	        FROM `tabPurchase Invoice` as purchase_invoice
	        where purchase_invoice.docstatus = 1 and purchase_invoice.modified >= "{0}" and purchase_invoice.company = "{1}"
	        group by purchase_invoice.supplier
	        order by value DESC
	        limit {2}""".format(filters, company, limit), as_dict=1)

	return frappe.db.sql("""
		select purchase_order.supplier as name, {0} as value
        FROM `tabPurchase Order` as purchase_order LEFT JOIN `tabPurchase Order Item`
        	as purchase_order_item ON purchase_order.name = purchase_order_item.parent
        where purchase_order.docstatus = 1 and  purchase_order.modified >= "{1}" and  purchase_order.company =  "{2}"
        group by purchase_order.supplier
        order by value DESC
        limit {3}""".format(select_field, filters, company, limit), as_dict=1)



def get_all_sales_partner(filters, items, field, start=0, limit=20):
	"""return all sales partner"""

	if field == "commission_rate":
		select_field = "sales_partner.commission_rate"
	elif field == "target_qty":
		select_field = "target_detail.target_qty"
	elif field == "target_amount":
		select_field = "target_detail.target_amount"
	elif field == "total_sales_amount":
		select_field = "sum(sales_order.total_commission)"

	return frappe.db.sql("""select sales_partner.partner_name as name, {0} as value
		from 
			`tabSales Partner` as sales_partner inner join `tabTarget Detail` as target_detail ON sales_partner.name = target_detail.parent 
		inner join 
			`tabSales Order` as sales_order ON sales_order.sales_partner = sales_partner.name
	 	where 
	 		sales_order.docstatus = 1 and  sales_order.modified >= "{1}"
	 	group by 
	 		sales_partner.partner_name
	 	order by value DESC
	 	limit {2}""".format(select_field, filters, limit), as_dict=1)


def get_all_sales_person(filters, items, field, start=0, limit=20):
	"""return all sales partner"""
	if field == "target_qty":
		select_field = "target_detail.target_qty"
	elif field == "target_amount":
		select_field = "target_detail.target_amount"
	elif field == "total_sales_amount":
		select_field = "sum(sales_team.allocated_amount)"

	return frappe.db.sql("""select sales_person.name as name, {0} as value
		from 
			`tabSales Person` as sales_person
		inner join 
			`tabTarget Detail` as target_detail ON sales_person.name = target_detail.parent 
		inner join 
			`tabSales Team` as sales_team ON sales_team.sales_person = sales_person.name 
		where sales_person.is_group = 0 and sales_team.modified >= "{1}"
		group by sales_person.name
	 	order by value DESC
	 	limit {2}""".format(select_field,filters,limit), as_dict=1)


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


