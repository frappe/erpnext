# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

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


def make_user(email: str) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email,
				"send_welcome_email": 0,
				"roles": [{"role": "Sales User"}],
			}
		).insert()
	return email
