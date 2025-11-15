# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.core.doctype.user_permission.test_user_permission import create_user
from frappe.tests import IntegrationTestCase

from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry


class TestPOSOpeningEntry(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		frappe.db.sql("delete from `tabPOS Opening Entry`")
		cls.enterClassContext(cls.change_settings("POS Settings", {"invoice_type": "POS Invoice"}))

	@classmethod
	def tearDownClass(cls):
		frappe.db.sql("delete from `tabPOS Opening Entry`")

	def setUp(self):
		# Make stock available for POS Sales
		frappe.db.sql("delete from `tabPOS Opening Entry`")
		make_stock_entry(target="_Test Warehouse - _TC", qty=2, basic_rate=100)
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile

		self.init_user_and_profile = init_user_and_profile

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.sql("delete from `tabPOS Profile`")

	def test_pos_opening_entry(self):
		test_user, pos_profile = self.init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		self.assertEqual(opening_entry.status, "Open")
		self.assertNotEqual(opening_entry.docstatus, 0)

	def test_pos_opening_entry_on_disabled_pos(self):
		test_user, pos_profile = self.init_user_and_profile(disabled=1)

		with self.assertRaises(frappe.ValidationError):
			create_opening_entry(pos_profile, test_user.name)

	def test_multiple_pos_opening_entries_for_same_pos_profile(self):
		test_user, pos_profile = self.init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		self.assertEqual(opening_entry.status, "Open")
		with self.assertRaises(frappe.ValidationError):
			create_opening_entry(pos_profile, test_user.name)

	def test_multiple_pos_opening_entry_for_multiple_pos_profiles(self):
		test_user, pos_profile = self.init_user_and_profile()
		opening_entry_1 = create_opening_entry(pos_profile, test_user.name)

		self.assertEqual(opening_entry_1.status, "Open")
		self.assertEqual(opening_entry_1.user, test_user.name)

		cashier_user = create_user("test_cashier@example.com", "Accounts Manager", "Sales Manager")
		frappe.set_user(cashier_user.name)

		pos_profile2 = make_pos_profile(name="_Test POS Profile 2")
		opening_entry_2 = create_opening_entry(pos_profile2, cashier_user.name)

		self.assertEqual(opening_entry_2.status, "Open")
		self.assertEqual(opening_entry_2.user, cashier_user.name)

	def test_multiple_pos_opening_entry_for_same_pos_profile_by_multiple_user(self):
		test_user, pos_profile = self.init_user_and_profile()
		cashier_user = create_user("test_cashier@example.com", "Accounts Manager", "Sales Manager")

		opening_entry = create_opening_entry(pos_profile, test_user.name)
		self.assertEqual(opening_entry.status, "Open")

		with self.assertRaises(frappe.ValidationError):
			create_opening_entry(pos_profile, cashier_user.name)

	def test_user_assignment_to_multiple_pos_profile(self):
		test_user, pos_profile = self.init_user_and_profile()
		opening_entry_1 = create_opening_entry(pos_profile, test_user.name)
		self.assertEqual(opening_entry_1.user, test_user.name)

		pos_profile2 = make_pos_profile(name="_Test POS Profile 2")
		with self.assertRaises(frappe.ValidationError):
			create_opening_entry(pos_profile2, test_user.name)

	def test_cancel_pos_opening_entry_without_invoices(self):
		test_user, pos_profile = self.init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name, get_obj=True)

		opening_entry.cancel()
		self.assertEqual(opening_entry.status, "Cancelled")
		self.assertNotEqual(opening_entry.docstatus, 1)

	def test_cancel_pos_opening_entry_with_invoice(self):
		test_user, pos_profile = self.init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name, get_obj=True)

		pos_inv1 = create_pos_invoice(pos_profile=pos_profile.name, rate=100, do_not_save=1)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 100})
		pos_inv1.save()
		pos_inv1.submit()

		self.assertRaises(frappe.ValidationError, opening_entry.cancel)


def create_opening_entry(pos_profile, user, get_obj=False):
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

	if get_obj:
		return entry

	return entry.as_dict()
