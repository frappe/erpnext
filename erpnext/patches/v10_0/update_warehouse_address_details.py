# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	warehouse = frappe.db.sql("""select name, email_id, phone_no, mobile_no, address_line_1,
		address_line_2, city, state, pin from `tabWarehouse` where ifnull(address_line_1, '') != '' """,as_dict=1)

	for d in warehouse:
		address = frappe.new_doc('Address')
		address.address_title = d.name
		address.address_line1 = d.address_line_1
		address.city = d.city
		address.state = d.state
		address.pincode = d.pin
		address.db_insert()
		address.append('links',{'link_doctype':'Warehouse','link_name':d.name})
		address.links[0].db_insert()