# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.tests.utils import ERPNextTestSuite


class TestCRMSettings(ERPNextTestSuite):
	"""CRM Settings guards its Frappe-CRM sync and Contact-Us opportunity toggles."""

	def make_settings(self, **fields):
		doc = frappe.new_doc("CRM Settings")
		doc.update(fields)
		return doc

	def test_data_sync_requires_at_least_one_allowed_user(self):
		doc = self.make_settings(enable_frappe_crm_data_synchronization=1)
		self.assertRaises(frappe.ValidationError, doc.validate_allowed_users)
		# adding a user satisfies the check
		doc.append("allowed_users", {"user": "Administrator"})
		doc.validate_allowed_users()

	def test_disabling_sync_clears_allowed_users(self):
		doc = self.make_settings(enable_frappe_crm_data_synchronization=0)
		doc.append("allowed_users", {"user": "Administrator"})
		doc.clear_allowed_users()
		self.assertEqual(doc.allowed_users, [])

		# while sync is on, the rows are kept
		enabled = self.make_settings(enable_frappe_crm_data_synchronization=1)
		enabled.append("allowed_users", {"user": "Administrator"})
		enabled.clear_allowed_users()
		self.assertEqual(len(enabled.allowed_users), 1)

	@ERPNextTestSuite.change_settings("Contact Us Settings", {"is_disabled": 1})
	def test_opportunity_from_contact_us_needs_the_form_enabled(self):
		doc = self.make_settings(enable_opportunity_creation_from_contact_us=1)
		self.assertRaises(frappe.ValidationError, doc.validate_enable_opportunity_creation_from_contact_us)
