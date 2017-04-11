# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt

def execute():
	for dt, party_field, account_field in (("Sales Invoice", "customer", "debit_to"), 
			("Purchase Invoice", "supplier", "credit_to")):
			
		wrong_invoices = frappe.db.sql("""select name, {0} as account from `tab{1}` 
			where docstatus=1 and ifnull({2}, '')=''""".format(account_field, dt, party_field))
			
		for invoice, account in wrong_invoices:
			update_outstanding_amt(account, party_field.title(), None, dt, invoice)