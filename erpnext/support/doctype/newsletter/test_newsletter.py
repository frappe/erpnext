# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe, unittest

class TestNewsletter(unittest.TestCase):
	def test_get_recipients_lead(self):
		w = frappe.get_doc(test_records[0])
		w.insert()
		self.assertTrue("test_lead@example.com" in w.get_recipients())
		frappe.db.sql("""delete from `tabBulk Email`""")
		w.send_emails()
		self.assertTrue(frappe.db.get_value("Bulk Email", {"recipient": "test_lead@example.com"}))

	def test_get_recipients_lead_by_status(self):
		w = frappe.get_doc(test_records[0])
		w.lead_status="Converted"
		w.insert()
		self.assertTrue("test_lead3@example.com" in w.get_recipients())

	def test_get_recipients_contact_customer(self):
		w = frappe.get_doc(test_records[1])
		w.insert()
		self.assertTrue("test_contact_customer@example.com" in w.get_recipients())

	def test_get_recipients_contact_supplier(self):
		w = frappe.get_doc(test_records[1])
		w.contact_type="Supplier"
		w.insert()
		self.assertTrue("test_contact_supplier@example.com" in w.get_recipients())

	def test_get_recipients_custom(self):
		w = frappe.get_doc(test_records[2])
		w.insert()
		self.assertTrue("test_custom2@example.com" in w.get_recipients())
		self.assertTrue(frappe.db.get("Lead",
			{"email_id": "test_custom2@example.com"}))


test_dependencies = ["Lead", "Contact"]

test_records = frappe.get_test_records('Newsletter')
