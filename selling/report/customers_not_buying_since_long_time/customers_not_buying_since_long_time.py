# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import getdate, cint

def execute(filters=None):
	if not filters: filters ={}

	days_since_last_order = filters.get("days_since_last_order")
	if cint(days_since_last_order) <= 0:
		webnotes.msgprint("Please mention positive value in 'Days Since Last Order' field",raise_exception=1)

	columns = get_columns() 
	customers = get_so_details()

	data = []
	for cust in customers:
		if cust[8] >= days_since_last_order:
			cust.insert(7,get_last_so_amt(cust[0]))
			data.append(cust)
	return columns, data 

def get_so_details():
	return webnotes.conn.sql("""select 
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
	res =  webnotes.conn.sql("""select net_total from `tabSales Order`
		where customer ='%(customer)s' and docstatus = 1 order by transaction_date desc 
		limit 1""" % {'customer':customer})

	return res and res[0][0] or 0

def get_columns():
	return [
		"Customer:Link/Customer:120", 
		"Customer Name:Data:120", 
		"Territory::120", 
		"Customer Group::120",
		"Number of Order::120", 
		"Total Order Value:Currency:120", 
		"Total Order Considered:Currency:160", 
		"Last Order Amount:Currency:160",
		"Last Sales Order Date:Date:160", 
		"Days Since Last Order::160"
	]