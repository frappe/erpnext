# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile


class TestPOSOpeningEntry(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def init_user_and_profile(self, **args):
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile

		return init_user_and_profile(**args)

	def test_user_not_in_pos_profile_cannot_open_session(self):
		other_user = create_user("test_other_cashier@example.com", "Sales User")
		test_user, pos_profile = self.init_user_and_profile()

		with self.assertRaises(frappe.ValidationError) as context:
			create_opening_entry(pos_profile, other_user.name)

		self.assertIn("Applicable for Users", str(context.exception))

	def test_blank_user_row_keeps_pos_profile_open_to_every_user(self):
		test_user = self.init_user_and_profile(do_not_create_pos_profile=1)
		pos_profile = make_pos_profile()
		pos_profile.append("applicable_for_users", {"default": 1})
		pos_profile.save()

		opening_entry = create_opening_entry(pos_profile, test_user.name)

		self.assertEqual(opening_entry.status, "Open")

	def test_blank_user_row_lets_unlisted_user_open_session(self):
		other_user = create_user("test_other_cashier@example.com", "Sales User")
		_, pos_profile = self.init_user_and_profile()
		pos_profile.append("applicable_for_users", {})
		pos_profile.save()

		opening_entry = create_opening_entry(pos_profile, other_user.name)

		self.assertEqual(opening_entry.status, "Open")

	def test_negative_or_duplicate_opening_balance_is_refused(self):
		test_user, pos_profile = self.init_user_and_profile()
		for balance_details, message in (
			([{"mode_of_payment": "Cash", "opening_amount": -500}], "cannot be negative"),
			(
				[
					{"mode_of_payment": "Cash", "opening_amount": 200},
					{"mode_of_payment": "Cash", "opening_amount": 100},
				],
				"added more than once",
			),
		):
			opening_entry = frappe.get_doc(
				{
					"doctype": "POS Opening Entry",
					"pos_profile": pos_profile.name,
					"user": test_user.name,
					"company": pos_profile.company,
					"period_start_date": frappe.utils.get_datetime(),
					"balance_details": balance_details,
				}
			)
			self.assertRaisesRegex(frappe.ValidationError, message, opening_entry.insert)


def create_opening_entry(pos_profile, user):
	entry = frappe.new_doc("POS Opening Entry")
	entry.pos_profile = pos_profile.name
	entry.user = user
	entry.company = pos_profile.company
	entry.period_start_date = frappe.utils.get_datetime()

	balance_details = []
	for d in pos_profile.payments:
		balance_details.append(frappe._dict({"mode_of_payment": d.mode_of_payment}))

	entry.set("balance_details", balance_details)
	entry.submit()

	return entry.as_dict()
