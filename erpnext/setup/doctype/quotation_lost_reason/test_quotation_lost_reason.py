# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestQuotationLostReason(ERPNextTestSuite):
	def test_sales_roles_can_create_lost_reasons(self):
		for role in ("Sales User", "Sales Manager"):
			with self.subTest(role=role):
				user = frappe.get_doc(
					doctype="User",
					email=f"{frappe.generate_hash()}@example.com",
					first_name=role,
					send_welcome_email=0,
					roles=[{"role": role}],
				).insert()
				with self.set_user(user.name):
					reason = frappe.get_doc(
						doctype="Quotation Lost Reason", order_lost_reason=f"_Test Lost Reason {role}"
					).insert()
					self.assertTrue(frappe.db.exists("Quotation Lost Reason", reason.name))
					self.assertFalse(reason.has_permission("write"))
					self.assertFalse(reason.has_permission("delete"))
