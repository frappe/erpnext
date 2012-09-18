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
sql = webnotes.conn.sql

test=1

# Update SO and DN Detail 
#--------------------------
def update_delivered_billed_qty():
	# update billed amt in item table in so and dn
	sql("""	update `tabSales Order Item` so
		set billed_amt = (select sum(amount) from `tabSales Invoice Item` where `so_detail`= so.name and docstatus=1 and parent not like 'old%%'),
		delivered_qty = (select sum(qty) from `tabDelivery Note Item` where `prevdoc_detail_docname`= so.name and docstatus=1 and parent not like 'old%%'), 
		modified = now()
		where docstatus = 1
	""")

	sql(""" update `tabDelivery Note Item` dn
		set billed_amt = (select sum(amount) from `tabSales Invoice Item` where `dn_detail`= dn.name and docstatus=1 and parent not like 'old%%'), 
		modified = now()
		where docstatus = 1
	""")

# update SO
#---------------
def update_percent():
	# calculate % billed based on item table
	sql("""	update `tabSales Order` so
		set per_delivered = (select sum(if(qty > ifnull(delivered_qty, 0), delivered_qty, qty))/sum(qty)*100 from `tabSales Order Item` where parent=so.name), 
		per_billed = (select sum(if(amount > ifnull(billed_amt, 0), billed_amt, amount))/sum(amount)*100 from `tabSales Order Item` where parent = so.name), 
		modified = now()
		where docstatus = 1
	""")
		
	# update DN	
	# ---------	
	sql("""	update `tabDelivery Note` dn
		set per_billed = (select sum(if(amount > ifnull(billed_amt, 0), billed_amt, amount))/sum(amount)*100 from `tabDelivery Note Item` where parent = dn.name), 
		modified = now()
		where docstatus=1
	""")

# update delivery/billing status 
#-------------------------------
def update_status():
	sql("""update `tabSales Order` set delivery_status = if(ifnull(per_delivered,0) < 0.001, 'Not Delivered', 
			if(per_delivered >= 99.99, 'Fully Delivered', 'Partly Delivered'))""")
	sql("""update `tabSales Order` set billing_status = if(ifnull(per_billed,0) < 0.001, 'Not Billed', 
			if(per_billed >= 99.99, 'Fully Billed', 'Partly Billed'))""")
	sql("""update `tabDelivery Note` set billing_status = if(ifnull(per_billed,0) < 0.001, 'Not Billed', 
			if(per_billed >= 99.99, 'Fully Billed', 'Partly Billed'))""")
			
def execute():
	update_delivered_billed_qty()
	update_percent()
	update_status()
