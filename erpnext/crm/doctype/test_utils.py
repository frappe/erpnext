# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.crm.doctype.utils import get_last_interaction
from erpnext.tests.utils import ERPNextTestSuite


class TestCrmDoctypeUtils(ERPNextTestSuite):
	def test_get_last_interaction_for_contact(self):
		"""Covers the converted Communication query (contact path): returns the earliest Received
		communication across the doctypes the contact is linked to. `creation` is unique, so the
		LIMIT-1 pick is deterministic and identical on MariaDB and Postgres."""
		customer = "_Test CRM Util Customer"
		if not frappe.db.exists("Customer", customer):
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": customer,
					"customer_group": "_Test Customer Group",
					"territory": "_Test Territory",
				}
			).insert(ignore_permissions=True)

		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "CRM Util Test",
				"links": [{"link_doctype": "Customer", "link_name": customer}],
			}
		).insert(ignore_permissions=True)

		comm = frappe.get_doc(
			{
				"doctype": "Communication",
				"subject": "hi",
				"content": "first interaction",
				"sent_or_received": "Received",
				"reference_doctype": "Customer",
				"reference_name": customer,
			}
		).insert(ignore_permissions=True)

		result = get_last_interaction(contact=contact.name)
		self.assertIsNotNone(result["last_communication"])
		self.assertEqual(result["last_communication"]["name"], comm.name)
