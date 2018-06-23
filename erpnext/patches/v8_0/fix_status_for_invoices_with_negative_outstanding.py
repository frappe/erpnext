# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for dt, status in [["Sales Invoice", "Credit Note Issued"], ["Purchase Invoice", "Debit Note Issued"]]:
		invoices = frappe.db.sql("""
			select name 
			from `tab{0}`
			where 
				status = %s
				and outstanding_amount < 0
				and docstatus=1
				and is_return=0
		""".format(dt), status)
		
		for inv in invoices:
			return_inv = frappe.db.sql("""select name from `tab{0}` 
				where is_return=1 and return_against=%s and docstatus=1""".format(dt), inv[0])
			if not return_inv:
				frappe.db.sql("update `tab{0}` set status='Paid' where name = %s".format(dt), inv[0])