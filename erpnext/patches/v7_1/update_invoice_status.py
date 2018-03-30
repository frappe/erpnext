# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc('accounts', 'doctype', 'sales_invoice')
	frappe.reload_doc('accounts', 'doctype', 'purchase_invoice')

	frappe.db.sql(""" 
		update 
			`tabPurchase Invoice` 
		set 
			status = (Case When outstanding_amount = 0 and docstatus = 1 and is_return = 0 then 'Paid'
			when due_date < CURDATE() and outstanding_amount > 0 and docstatus =1 then 'Overdue'
			when due_date >= CURDATE() and outstanding_amount > 0 and docstatus =1 then 'Unpaid'
			when outstanding_amount < 0 and docstatus =1 then 'Debit Note Issued'
			when is_return = 1 and docstatus =1 then 'Return'
			when docstatus = 2 then 'Cancelled'
			else 'Draft'
		End)""")

	frappe.db.sql(""" 
		update 
			`tabSales Invoice` 
		set status = (Case When outstanding_amount = 0 and docstatus = 1 and is_return = 0 then 'Paid'
			when due_date < CURDATE() and outstanding_amount > 0 and docstatus =1 then 'Overdue'
			when due_date >= CURDATE() and outstanding_amount > 0 and docstatus =1 then 'Unpaid'
			when outstanding_amount < 0 and docstatus =1 then 'Credit Note Issued'
			when is_return = 1 and docstatus =1 then 'Return'
			when docstatus = 2 then 'Cancelled'
			else 'Draft'
		End)""")