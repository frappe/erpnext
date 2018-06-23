# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	warehouse = frappe.db.sql("""select name, email_id, phone_no, mobile_no, address_line_1,
		address_line_2, city, state, pin from `tabWarehouse` where ifnull(address_line_1, '') != '' 
		or ifnull(mobile_no, '') != '' 
		or ifnull(email_id, '') != '' """, as_dict=1)

	for d in warehouse:
		try:
			address = frappe.new_doc('Address')
			address.name = d.name
			address.address_title = d.name
			address.address_line1 = d.address_line_1
			address.city = d.city
			address.state = d.state
			address.pincode = d.pin
			address.db_insert()
			address.append('links',{'link_doctype':'Warehouse','link_name':d.name})
			address.links[0].db_insert()
			if d.name and (d.email_id or d.mobile_no or d.phone_no):
				contact = frappe.new_doc('Contact')
				contact.name = d.name
				contact.first_name = d.name
				contact.mobile_no = d.mobile_no
				contact.email_id = d.email_id
				contact.phone = d.phone_no
				contact.db_insert()
				contact.append('links',{'link_doctype':'Warehouse','link_name':d.name})
				contact.links[0].db_insert()
		except frappe.DuplicateEntryError:
			pass
	