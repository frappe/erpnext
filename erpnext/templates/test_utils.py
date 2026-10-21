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
