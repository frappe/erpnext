# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.stock.stock_balance import repost_actual_qty

def execute():
	cancelled_invoices = frappe.db.sql_list("""select name from `tabSales Invoice` 
		where docstatus = 2 and ifnull(update_stock, 0) = 1""")

	if cancelled_invoices:
		repost_for = frappe.db.sql("""select distinct item_code, warehouse from `tabStock Ledger Entry`
			where voucher_type = 'Sales Invoice' and voucher_no in (%s)""" 
			% (', '.join(['%s']*len(cancelled_invoices))), tuple(cancelled_invoices))
			
		frappe.db.sql("""delete from `tabStock Ledger Entry` 
			where voucher_type = 'Sales Invoice' and voucher_no in (%s)""" 
			% (', '.join(['%s']*len(cancelled_invoices))), tuple(cancelled_invoices))
			
		for item_code, warehouse in repost_for:
			repost_actual_qty(item_code, warehouse)