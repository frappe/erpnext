# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import filter_strip_join

doctype = "Sales Partner"
condition_field = "show_in_website"

def get_context(context):
	partner_context = context.doc.as_dict()
	
	address = frappe.db.get_value("Address", 
		{"sales_partner": context.doc.name, "is_primary_address": 1}, 
		"*", as_dict=True)
	if address:
		city_state = ", ".join(filter(None, [address.city, address.state]))
		address_rows = [address.address_line1, address.address_line2,
			city_state, address.pincode, address.country]
			
		partner_context.update({
			"email": address.email_id,
			"partner_address": filter_strip_join(address_rows, "\n<br>"),
			"phone": filter_strip_join(cstr(address.phone).split(","), "\n<br>")
		})
	
	return partner_context
