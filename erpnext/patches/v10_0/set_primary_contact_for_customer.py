# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():	
	frappe.reload_doctype('Customer')

	frappe.db.sql("""
		update 
			`tabCustomer`, (           
				select `tabContact`.name, `tabContact`.mobile_no, `tabContact`.email_id, 
					`tabDynamic Link`.link_name from `tabContact`, `tabDynamic Link`
				where `tabContact`.name = `tabDynamic Link`.parent and 
				`tabDynamic Link`.link_doctype = 'Customer' and `tabContact`.is_primary_contact = 1
			) as contact
		set 
			`tabCustomer`.customer_primary_contact = contact.name,
			`tabCustomer`.mobile_no = contact.mobile_no, `tabCustomer`.email_id = contact.email_id 
		where `tabCustomer`.name = contact.link_name""")