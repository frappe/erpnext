# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, flt

def execute():
	update_po_per_received_per_billed()
	update_so_per_delivered_per_billed()
	update_status()

def update_po_per_received_per_billed():
	frappe.db.sql(""" 
		update
			`tabPurchase Order`
		set
			`tabPurchase Order`.per_received = round((select sum(if(qty > ifnull(received_qty, 0),
					ifnull(received_qty, 0), qty)) / sum(qty) *100 from `tabPurchase Order Item`
					where parent = `tabPurchase Order`.name), 2),
			`tabPurchase Order`.per_billed = ifnull(round((select sum( if(amount > ifnull(billed_amt, 0),
					ifnull(billed_amt, 0), amount)) / sum(amount) *100 from `tabPurchase Order Item`
					where parent = `tabPurchase Order`.name), 2), 0)""")

def update_so_per_delivered_per_billed():
	frappe.db.sql(""" 
		update
			`tabSales Order`
		set 
			`tabSales Order`.per_delivered = round((select sum( if(qty > ifnull(delivered_qty, 0),
					ifnull(delivered_qty, 0), qty)) / sum(qty) *100 from `tabSales Order Item` 
					where parent = `tabSales Order`.name), 2), 
			`tabSales Order`.per_billed = ifnull(round((select sum( if(amount > ifnull(billed_amt, 0),
					ifnull(billed_amt, 0), amount)) / sum(amount) *100 from `tabSales Order Item`
					where parent = `tabSales Order`.name), 2), 0)""")

def update_status():
	frappe.db.sql("""
		update
			`tabSales Order`
		set status = (Case when status = 'Closed' then 'Closed'
			When per_delivered < 100 and per_billed < 100 and docstatus = 1 then 'To Deliver and Bill'
			when per_delivered = 100 and per_billed < 100 and docstatus = 1 then 'To Bill'
			when per_delivered < 100 and per_billed = 100 and docstatus = 1 then 'To Deliver'
			when per_delivered = 100 and per_billed = 100 and docstatus = 1 then 'Completed'
			when order_type = 'Maintenance' and per_billed = 100 and docstatus = 1 then 'Completed'
			when docstatus = 2 then 'Cancelled'
			else 'Draft'
		End)""")

	frappe.db.sql("""
		update 
			`tabPurchase Order` 
		set status = (Case when status = 'Closed' then 'Closed'
			when status = 'Delivered' then 'Delivered'
			When per_received < 100 and per_billed < 100 and docstatus = 1 then 'To Receive and Bill'
			when per_received = 100 and per_billed < 100 and docstatus = 1 then 'To Bill'
			when per_received < 100 and per_billed = 100 and docstatus = 1 then 'To Receive'
			when per_received = 100 and per_billed = 100 and docstatus = 1 then 'Completed'
			when docstatus = 2 then 'Cancelled'
			else 'Draft'
		End)""")