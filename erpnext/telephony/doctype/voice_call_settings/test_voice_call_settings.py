# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
import frappe.client

from erpnext.tests.permission_test_utils import as_user, make_fenced_user
from erpnext.tests.utils import ERPNextTestSuite


class TestVoiceCallSettings(ERPNextTestSuite):
	def test_user_creates_own_settings(self):
		user = make_user("voice-call-owner@example.com")
		other_user = make_user("voice-call-other@example.com")

		with self.set_user(user):
			own = frappe.get_doc({"doctype": "Voice Call Settings", "user": user}).insert()
			self.assertEqual((own.name, own.user), (user, user))

		frappe.delete_doc("Voice Call Settings", own.name)
		with self.set_user(user):
			picked = frappe.get_doc({"doctype": "Voice Call Settings", "user": other_user}).insert()
			self.assertEqual((picked.name, picked.user), (user, user))

	def test_settings_are_limited_to_their_user(self):
		owner = make_user("voice-call-owner@example.com")
		settings = make_settings(owner, greeting_message="Owner greeting")

		other_user = make_user("voice-call-other@example.com")
		website_user = make_fenced_user("voice-call-website@example.com", [])
		with as_user(website_user):
			self.assertRaises(frappe.PermissionError, frappe.get_list, "Voice Call Settings")
		with as_user(other_user):
			self.assertNotIn(owner, frappe.get_list("Voice Call Settings", pluck="name"))

		for outsider in (other_user, website_user):
			with as_user(outsider):
				self.assertRaises(frappe.PermissionError, frappe.client.get, "Voice Call Settings", owner)
				self.assertRaises(
					frappe.PermissionError,
					frappe.client.set_value,
					"Voice Call Settings",
					owner,
					"greeting_message",
					"Changed",
				)
				self.assertRaises(frappe.PermissionError, frappe.delete_doc, "Voice Call Settings", owner)

		with as_user(owner):
			self.assertEqual(frappe.get_list("Voice Call Settings", pluck="name"), [owner])
			frappe.client.set_value("Voice Call Settings", owner, "greeting_message", "Owner changed")

		with as_user(make_fenced_user("voice-call-manager@example.com", ["System Manager"])):
			self.assertIn(owner, frappe.get_list("Voice Call Settings", pluck="name"))
			self.assertEqual(
				frappe.client.get("Voice Call Settings", owner)["greeting_message"], "Owner changed"
			)
		self.assertTrue(frappe.db.exists("Voice Call Settings", settings.name))


def make_user(email: str) -> str:
	return make_fenced_user(email, ["Sales User"])


def make_settings(user: str, **values) -> "frappe.model.document.Document":
	if not frappe.db.exists("Voice Call Settings", user):
		frappe.get_doc({"doctype": "Voice Call Settings", "user": user}).insert(ignore_permissions=True)
	frappe.db.set_value("Voice Call Settings", user, values)
	return frappe.get_doc("Voice Call Settings", user)
