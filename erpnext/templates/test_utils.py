# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.templates.utils import get_customer_from_contact_email, send_message
from erpnext.tests.utils import ERPNextTestSuite


class TestTemplateUtils(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_single_value("Contact Us Settings", "is_disabled", 0)

	def test_contact_email_lookup_is_case_insensitive(self):
		"""send_message resolves the Opportunity party by matching Contact.email_id with `==`.
		Equality is case-SENSITIVE on Postgres (the query-builder ILIKE patch only rewrites LIKE),
		while MariaDB's default collation is case-insensitive. A Contact email stored as
		'Case.Test@Example.com' with a lowercase sender therefore matches on MariaDB but not on
		Postgres -- so the Contact-Us form links a Lead instead of the Customer. The original raw SQL
		used the same `c.email_id = %s`, so MariaDB output is unchanged: this is a Postgres-only break."""
		customer_name = "_Test Contact Case Customer"
		if not frappe.db.exists("Customer", customer_name):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": customer_name,
					"customer_group": "_Test Customer Group",
					"territory": "_Test Territory",
				}
			).insert(ignore_permissions=True)

		frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Case Test Contact",
				"email_ids": [{"email_id": "Case.Test@Example.com", "is_primary": 1}],
				"links": [{"link_doctype": "Customer", "link_name": customer_name}],
			}
		).insert(ignore_permissions=True)

		# lowercase sender vs the stored mixed-case Contact email
		matched = get_customer_from_contact_email("case.test@example.com")
		self.assertTrue(matched, "Contact email lookup found no Customer for a case-differing sender")
		self.assertEqual(matched[0][0], customer_name)

	def test_contact_us_lead_from_a_named_guest_sender(self):
		frappe.db.set_single_value("CRM Settings", "enable_opportunity_creation_from_contact_us", 1)
		self.addCleanup(frappe.db.set_default, "company", frappe.db.get_default("company"))
		frappe.db.set_default("company", "_Test Company")
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Guest")
		send_message("Ravi Kumar <_test_contact_us_ravi@example.com>", "Need a quote")
		frappe.set_user("Administrator")

		lead = frappe.db.get_value(
			"Lead", {"email_id": "_test_contact_us_ravi@example.com"}, ["name", "lead_owner"], as_dict=True
		)
		self.assertTrue(lead)
		self.assertFalse(lead.lead_owner)

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
