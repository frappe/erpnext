# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.core.doctype.user.test_user import delete_contact, test_user

from erpnext.portal.utils import create_customer_or_supplier
from erpnext.tests.utils import ERPNextTestSuite, change_settings


class TestPortalUtils(ERPNextTestSuite):
	@change_settings("Portal Settings", default_role="Customer")
	def test_customer_contact_is_created_with_user_email(self):
		with test_user(roles=["Customer"], generated_id=True) as user:
			# the Contact frappe makes for a new user has no party links
			delete_contact(user.email)

			with self.set_user(user.name):
				customer = create_customer_or_supplier()
				self.assertIsNone(create_customer_or_supplier())

			contact = frappe.db.get_value(
				"Dynamic Link",
				{"parenttype": "Contact", "link_doctype": "Customer", "link_name": customer.name},
				"parent",
			)
			self.assertEqual(frappe.db.get_value("Contact", contact, "email_id"), user.email)
