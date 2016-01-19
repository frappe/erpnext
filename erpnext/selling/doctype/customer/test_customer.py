# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
import unittest

from frappe.test_runner import make_test_records
from erpnext.exceptions import CustomerFrozen

test_ignore = ["Price List"]

test_records = frappe.get_test_records('Customer')

class TestCustomer(unittest.TestCase):
	def test_party_details(self):
		from erpnext.accounts.party import get_party_details

		to_check = {
			'selling_price_list': None,
			'customer_group': '_Test Customer Group',
			'contact_designation': None,
			'customer_address': '_Test Address-Office',
			'contact_department': None,
			'contact_email': 'test_contact_customer@example.com',
			'contact_mobile': None,
			'sales_team': [],
			'contact_display': '_Test Contact For _Test Customer',
			'contact_person': '_Test Contact For _Test Customer-_Test Customer',
			'territory': u'_Test Territory',
			'contact_phone': '+91 0000000000',
			'customer_name': '_Test Customer'
		}

		make_test_records("Address")
		make_test_records("Contact")
		frappe.db.set_value("Contact", "_Test Contact For _Test Customer-_Test Customer",
			"is_primary_contact", 1)

		details = get_party_details("_Test Customer")

		for key, value in to_check.iteritems():
			self.assertEquals(value, details.get(key))

	def test_rename(self):
		for name in ("_Test Customer 1", "_Test Customer 1 Renamed"):
			frappe.db.sql("""delete from `tabComment` where comment_doctype=%s and comment_docname=%s""",
				("Customer", name))

		comment = frappe.new_doc("Comment")
		comment.update({
			"comment": "Test Comment for Rename",
			"comment_doctype": "Customer",
			"comment_docname": "_Test Customer 1"
		})
		comment.insert()

		frappe.rename_doc("Customer", "_Test Customer 1", "_Test Customer 1 Renamed")

		self.assertTrue(frappe.db.exists("Customer", "_Test Customer 1 Renamed"))
		self.assertFalse(frappe.db.exists("Customer", "_Test Customer 1"))

		# test that comment gets renamed
		self.assertEquals(frappe.db.get_value("Comment",
			{"comment_doctype": "Customer", "comment_docname": "_Test Customer 1 Renamed"}), comment.name)

		frappe.rename_doc("Customer", "_Test Customer 1 Renamed", "_Test Customer 1")

	def test_freezed_customer(self):
		make_test_records("Customer")
		make_test_records("Item")
		
		frappe.db.set_value("Customer", "_Test Customer", "is_frozen", 1)

		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		so = make_sales_order(do_not_save= True)
		
		self.assertRaises(CustomerFrozen, so.save)

		frappe.db.set_value("Customer", "_Test Customer", "is_frozen", 0)

		so.save()
	
	def test_duplicate_customer(self):
		if not frappe.db.get_value("Customer", "_Test Customer 1"):
			test_customer_1 = frappe.get_doc({
				 "customer_group": "_Test Customer Group",
				 "customer_name": "_Test Customer 1",
				 "customer_type": "Individual",
				 "doctype": "Customer",
				 "territory": "_Test Territory"
			}).insert(ignore_permissions=True)
		else:
			test_customer_1 = frappe.get_doc("Customer", "_Test Customer 1")

		duplicate_customer = frappe.get_doc({
			 "customer_group": "_Test Customer Group",
			 "customer_name": "_Test Customer 1",
			 "customer_type": "Individual",
			 "doctype": "Customer",
			 "territory": "_Test Territory"
		}).insert(ignore_permissions=True)

		self.assertEquals("_Test Customer 1", test_customer_1.name)
		self.assertEquals("_Test Customer 1 - 1", duplicate_customer.name)
		self.assertEquals(test_customer_1.customer_name, duplicate_customer.customer_name)