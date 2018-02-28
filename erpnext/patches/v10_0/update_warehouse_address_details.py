# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	warehouse = frappe.db.sql("""select name, email_id, phone_no, mobile_no, address_line_1,
		address_line_2, city, state, pin from `tabWarehouse`""",as_dict=1)

	for d in warehouse:                                                                                                                    
		if not frappe.db.sql("select name from `tabAddress` where address_title=%s", d.name):
			address = frappe.new_doc('Address')
			address.address_title = d.name
			address.address_line1 = d.address_line_1
			address.city = d.city
			address.state = d.state
			address.pincode = d.pin
			address.append('links',{'link_doctype':'Warehouse','link_name':d.name})
			address.flags.ignore_mandatory = True
			address.save()