# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

def create_test_contact_and_address():
	if not frappe.db.exists('Address', '_Test Address for Customer-Office'):
		frappe.get_doc(dict(
			doctype='Address',
			address_title='_Test Address for Customer',
			address_type='Office',
			address_line1='Station Road',
			city='Mumbai',
			country='India',
			links = [dict(
				link_doctype='Customer',
				link_name='_Test Customer'
			)]
		)).insert()

	if not frappe.db.exists('Contact', '_Test Contact for _Test Customer-_Test Customer'):
		frappe.get_doc(dict(
			doctype='Contact',
			email_id='test_contact_customer@example.com',
			phone='+91 0000000000',
			first_name='_Test Contact for _Test Customer',
			links = [dict(
				link_doctype='Customer',
				link_name='_Test Customer'
			)]
		)).insert()
