# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from erpnext.accounts.doctype.gl_entry.gl_entry import update_outstanding_amt

def execute():
	frappe.reload_doctype("Sales Invoice")
	return_entries = frappe.get_list("Sales Invoice", filters={"is_return": 1, "docstatus": 1}, 
		fields=["debit_to", "customer", "return_against"])
	for d in return_entries:
		update_outstanding_amt(d.debit_to, "Customer", d.customer, "Sales Invoice", d.return_against)
