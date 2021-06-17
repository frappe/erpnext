# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import copy
from contextlib import contextmanager

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


@contextmanager
def change_settings(doctype, settings_dict):
	""" A context manager to ensure that settings are changed before running
	function and restored after running it regardless of exceptions occured.
	This is useful in tests where you want to make changes in a function but
	don't retain those changes.
	import and use as decorator to cover full function or using `with` statement.

	example:
	@change_settings("Stock Settings", {"item_naming_by": "Naming Series"})
	def test_case(self):
		...
	"""

	try:
		settings = frappe.get_doc(doctype)
		# remember setting
		previous_settings = copy.deepcopy(settings_dict)
		for key in previous_settings:
			previous_settings[key] = getattr(settings, key)

		# change setting
		for key, value in settings_dict.items():
			setattr(settings, key, value)
		settings.save()
		yield # yield control to calling function

	finally:
		# restore settings
		settings = frappe.get_doc(doctype)
		for key, value in previous_settings.items():
			setattr(settings, key, value)
		settings.save()
