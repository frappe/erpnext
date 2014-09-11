# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint
from frappe import _

def execute(filters=None):
	if not filters: filters ={}

	days_since_last_order = filters.get("days_since_last_order")
	if cint(days_since_last_order) <= 0:
		frappe.throw(_("'Days Since Last Order' must be greater than or equal to zero"))

	columns = get_columns()
	customers = get_so_details()

	data = []
	for cust in customers:
		if cint(cust[8]) >= cint(days_since_last_order):
			cust.insert(7,get_last_so_amt(cust[0]))
			data.append(cust)
	return columns, data

def get_so_details():
	return frappe.db.sql("""select
			cust.name,
			cust.customer_name,
			cust.territory,
			cust.customer_group,
			count(distinct(so.name)) as 'num_of_order',
			sum(net_total) as 'total_order_value',
			sum(if(so.status = "Stopped",
				so.net_total * so.per_delivered/100,
				so.net_total)) as 'total_order_considered',
			max(so.transaction_date) as 'last_sales_order_date',
			DATEDIFF(CURDATE(), max(so.transaction_date)) as 'days_since_last_order'
		from `tabCustomer` cust, `tabSales Order` so
		where cust.name = so.customer and so.docstatus = 1
		group by cust.name
		order by 'days_since_last_order' desc """,as_list=1)

def get_last_so_amt(customer):
	res =  frappe.db.sql("""select net_total from `tabSales Order`
		where customer ='%(customer)s' and docstatus = 1 order by transaction_date desc
		limit 1""" % {'customer':customer})

	return res and res[0][0] or 0

def get_columns():
	return [
		_("Customer") + ":Link/Customer:120",
		_("Customer Name") + ":Data:120",
		_("Territory") + "::120",
		_("Customer Group") + "::120",
		_("Number of Order") + "::120",
		_("Total Order Value") + ":Currency:120",
		_("Total Order Considered") + ":Currency:160",
		_("Last Order Amount") + ":Currency:160",
		_("Last Sales Order Date") + ":Date:160",
		_("Days Since Last Order") + "::160"
	]
