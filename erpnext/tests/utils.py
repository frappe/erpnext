# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def create_test_contact_and_address():
	frappe.db.sql('delete from tabContact')
	frappe.db.sql('delete from `tabContact Email`')
	frappe.db.sql('delete from `tabContact Phone`')
	frappe.db.sql('delete from tabAddress')
	frappe.db.sql('delete from `tabDynamic Link`')

	frappe.get_doc({
		"doctype": "Address",
		"address_title": "_Test Address for Customer",
		"address_type": "Office",
		"address_line1": "Station Road",
		"city": "_Test City",
		"state": "Test State",
		"country": "India",
		"links": [
			{
				"link_doctype": "Customer",
				"link_name": "_Test Customer"
			}
		]
	}).insert()

	contact = frappe.get_doc({
		"doctype": 'Contact',
		"first_name": "_Test Contact for _Test Customer",
		"links": [
			{
				"link_doctype": "Customer",
				"link_name": "_Test Customer"
			}
		]
	})
	contact.add_email("test_contact_customer@example.com", is_primary=True)
	contact.add_phone("+91 0000000000", is_primary_phone=True)
	contact.insert()
