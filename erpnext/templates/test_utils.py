# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.templates.utils import get_customer_from_contact_email, send_message
from erpnext.tests.utils import ERPNextTestSuite


class TestTemplateUtils(ERPNextTestSuite):
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
