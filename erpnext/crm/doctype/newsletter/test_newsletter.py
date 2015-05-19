# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
from __future__ import unicode_literals

import frappe, unittest

from erpnext.crm.doctype.newsletter.newsletter import unsubscribe
from urllib import unquote

class TestNewsletter(unittest.TestCase):
	def setUp(self):
		frappe.db.sql("update `tabNewsletter List Subscriber` set unsubscribed = 0")

	def test_send(self):
		self.send_newsletter()
		self.assertEquals(len(frappe.get_all("Bulk Email")), 3)

	def test_unsubscribe(self):
		# test unsubscribe
		self.send_newsletter()

		email = unquote(frappe.local.flags.signed_query_string.split("email=")[1].split("&")[0])

		unsubscribe(email, "_Test Newsletter List")

		self.send_newsletter()
		self.assertEquals(len(frappe.get_all("Bulk Email")), 2)

	def send_newsletter(self):
		frappe.db.sql("delete from `tabBulk Email`")
		frappe.delete_doc("Newsletter", "_Test Newsletting")
		newsletter = frappe.get_doc({
			"doctype": "Newsletter",
			"subject": "_Test Newsletting",
			"newsletter_list": "_Test Newsletter List",
			"send_from": "Test Sender <test_sender@example.com>",
			"message": "Testing my news."
		}).insert(ignore_permissions=True)

		newsletter.send_emails()



test_dependencies = ["Newsletter List"]
