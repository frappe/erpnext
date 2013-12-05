# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import webnotes, unittest

class TestNewsletter(unittest.TestCase):
	def test_get_recipients_lead(self):
		w = webnotes.bean(test_records[0])
		w.insert()
		self.assertTrue("test_lead@example.com" in w.controller.get_recipients())
		webnotes.conn.sql("""delete from `tabBulk Email`""")
		w.controller.send_emails()
		self.assertTrue(webnotes.conn.get_value("Bulk Email", {"recipient": "test_lead@example.com"}))

	def test_get_recipients_lead_by_status(self):
		w = webnotes.bean(test_records[0])
		w.doc.lead_status="Converted"
		w.insert()
		self.assertTrue("test_lead3@example.com" in w.controller.get_recipients())

	def test_get_recipients_contact_customer(self):
		w = webnotes.bean(test_records[1])
		w.insert()
		self.assertTrue("test_contact_customer@example.com" in w.controller.get_recipients())

	def test_get_recipients_contact_supplier(self):
		w = webnotes.bean(test_records[1])
		w.doc.contact_type="Supplier"
		w.insert()
		self.assertTrue("test_contact_supplier@example.com" in w.controller.get_recipients())

	def test_get_recipients_custom(self):
		w = webnotes.bean(test_records[2])
		w.insert()
		self.assertTrue("test_custom2@example.com" in w.controller.get_recipients())
		self.assertTrue(webnotes.conn.get("Lead", 
			{"email_id": "test_custom2@example.com"}))


test_dependencies = ["Lead", "Contact"]

test_records =[
	[{
		"doctype": "Newsletter",
		"subject": "_Test Newsletter to Lead",
		"send_to_type": "Lead",
		"lead_source": "All",
		"message": "This is a test newsletter",
		"send_from": "admin@example.com"
	}],
	[{
		"doctype": "Newsletter",
		"subject": "_Test Newsletter to Contact",
		"send_to_type": "Contact",
		"contact_type": "Customer",
		"message": "This is a test newsletter",
		"send_from": "admin@example.com"
	}],
	[{
		"doctype": "Newsletter",
		"subject": "_Test Newsletter to Custom",
		"send_to_type": "Custom",
		"email_list": "test_custom@example.com, test_custom1@example.com, test_custom2@example.com",
		"message": "This is a test newsletter",
		"send_from": "admin@example.com"
	}],
]
