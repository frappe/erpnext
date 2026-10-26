# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.templates.utils import send_message

test_dependencies = ["Company", "Customer"]


class TestTemplateUtils(FrappeTestCase):
	def setUp(self):
		frappe.db.set_single_value("Contact Us Settings", "is_disabled", 0)

	def test_contact_us_guest_is_not_filed_against_a_customer(self):
		frappe.db.set_single_value("CRM Settings", "enable_opportunity_creation_from_contact_us", 1)
		self.addCleanup(frappe.db.set_default, "company", frappe.db.get_default("company"))
		frappe.db.set_default("company", "_Test Company")
		sender = "_test_contact_us_customer@example.com"
		frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Contact Us Customer",
				"email_ids": [{"email_id": sender, "is_primary": 1}],
				"links": [{"link_doctype": "Customer", "link_name": "_Test Customer"}],
			}
		).insert(ignore_permissions=True)

		with self.set_user("Guest"):
			send_message(sender, "Renewal request", "Renewal")
		opportunity = frappe.db.get_value(
			"Opportunity", {"contact_email": sender}, ["opportunity_from", "party_name"], as_dict=True
		)
		self.assertEqual(opportunity.opportunity_from, "Lead")
		self.assertNotEqual(opportunity.party_name, "_Test Customer")

		frappe.db.set_single_value("Contact Us Settings", "is_disabled", 1)
		with self.set_user("Guest"):
			send_message("_test_contact_us_disabled@example.com", "Hello", "Disabled")
		self.assertFalse(frappe.db.exists("Lead", {"email_id": "_test_contact_us_disabled@example.com"}))

	def test_contact_us_signed_in_sender_is_filed_against_own_customer(self):
		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		frappe.db.set_single_value("CRM Settings", "enable_opportunity_creation_from_contact_us", 1)
		self.addCleanup(frappe.db.set_default, "company", frappe.db.get_default("company"))
		frappe.db.set_default("company", "_Test Company")
		user = make_fenced_user("_test_contact_us_signed_in@example.com", ["Customer"])
		other = "_test_contact_us_colleague@example.com"
		for email in (user, other):
			frappe.get_doc(
				{
					"doctype": "Contact",
					"first_name": email,
					"email_ids": [{"email_id": email, "is_primary": 1}],
					"links": [{"link_doctype": "Customer", "link_name": "_Test Customer"}],
				}
			).insert(ignore_permissions=True)

		with as_user(user):
			send_message(user.upper(), "Renewal request", "Own renewal")
			send_message(other, "Renewal request", "Colleague renewal")

		own = frappe.db.get_value("Opportunity", {"title": "Own renewal"}, ["opportunity_from", "party_name"])
		colleague = frappe.db.get_value("Opportunity", {"title": "Colleague renewal"}, "opportunity_from")
		self.assertEqual(own, ("Customer", "_Test Customer"))
		self.assertEqual(colleague, "Lead")

	def test_contact_us_subject_is_stored_as_plain_text(self):
		frappe.db.set_single_value("CRM Settings", "enable_opportunity_creation_from_contact_us", 1)
		self.addCleanup(frappe.db.set_default, "company", frappe.db.get_default("company"))
		frappe.db.set_default("company", "_Test Company")
		sender = "_test_contact_us_subject@example.com"
		with self.set_user("Guest"):
			send_message(sender, "<script>alert(1)</script>", 'Sales & Support<img src=x onerror="alert(1)">')

		opportunity = frappe.db.get_value(
			"Opportunity", {"contact_email": sender}, ["name", "title"], as_dict=True
		)
		communication = frappe.db.get_value(
			"Communication", {"reference_name": opportunity.name}, ["subject", "content"], as_dict=True
		)
		self.assertEqual(opportunity.title, "Sales & Support")
		self.assertEqual(communication.subject, "Sales & Support")
		self.assertNotIn("<script>", communication.content)
		self.assertIn("&lt;script&gt;", communication.content)
