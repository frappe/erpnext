# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	for doctype in ("Sales Order", "Purchase Order"):
		frappe.reload_doctype(doctype)
		
		for order in frappe.db.sql("""select name, {0} as party from `tab{1}` 
			where advance_paid > 0 and docstatus=1"""
			.format(("customer" if doctype=="Sales Order" else "supplier"), doctype), as_dict=1):
			
			party_account_currency = frappe.db.get_value("Journal Entry Account", {
				"reference_type": doctype,
				"reference_name": order.name,
				"party": order.party,
				"docstatus": 1,
				"is_advance": "Yes"
			}, "account_currency")
			
			frappe.db.set_value(doctype, order.name, "party_account_currency", party_account_currency)
		