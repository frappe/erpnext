# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_customer
from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import make_closing_entry_from_opening


class TestPOSOpeningEntry(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_pos_opening_to_pos_closing_TC_S_099(self):
		create_customer("_Test Customer", currency="INR")
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile
		from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice

		test_user, pos_profile = init_user_and_profile()

		opening_entry = create_opening_entry(pos_profile=pos_profile, user=test_user.name)
		self.assertEqual(opening_entry.status, "Open")

		pos_inv1 = create_pos_invoice(rate=3500, do_not_submit=1)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv1.paid_amount = pos_inv1.grand_total
		pos_inv1.outstanding_amount = 0
		pos_inv1.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv2.paid_amount = pos_inv2.grand_total
		pos_inv2.outstanding_amount = 0
		pos_inv2.submit()

		closing_enrty = make_closing_entry_from_opening(opening_entry)
		closing_enrty.submit()
		opening_entry.reload()
		self.assertEqual(opening_entry.status, "Closed")

	def test_pos_opening_to_closing_enrty_check_cashire_and_posprofile_TC_S_100(self):
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile
		from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice

		test_user, pos_profile = init_user_and_profile()

		opening_entry = create_opening_entry(pos_profile=pos_profile, user=test_user.name)
		self.assertEqual(opening_entry.status, "Open")
		self.assertEqual(opening_entry.pos_profile, pos_profile.name)
		self.assertEqual(opening_entry.user, test_user.name)

		pos_inv1 = create_pos_invoice(rate=3500, do_not_submit=1)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv1.paid_amount = pos_inv1.grand_total
		pos_inv1.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv2.paid_amount = pos_inv2.grand_total
		pos_inv2.outstanding_amount = 0
		pos_inv2.submit()

		closing_enrty = make_closing_entry_from_opening(opening_entry)
		closing_enrty.submit()
		opening_entry.reload()
		self.assertEqual(opening_entry.status, "Closed")

	def test_pos_opening_to_closing_enrty_with_opening_balance_TC_S_101(self):
		from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile
		from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice

		test_user, pos_profile = init_user_and_profile()

		opening_entry = frappe.new_doc("POS Opening Entry")
		opening_entry.pos_profile = pos_profile.name
		opening_entry.user = test_user.name
		opening_entry.company = pos_profile.company
		opening_entry.period_start_date = frappe.utils.get_datetime()

		# Add opening balance details
		balance_details = []
		for d in pos_profile.payments:
			balance_details.append({"mode_of_payment": d.mode_of_payment, "opening_amount": 1000})

		opening_entry.set("balance_details", balance_details)
		opening_entry.save()
		opening_entry.submit()
		self.assertEqual(opening_entry.status, "Open")

		pos_inv1 = create_pos_invoice(rate=3500, do_not_submit=1)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv1.paid_amount = pos_inv1.grand_total
		pos_inv1.outstanding_amount = 0
		pos_inv1.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv2.paid_amount = pos_inv2.grand_total
		pos_inv2.outstanding_amount = 0
		pos_inv2.submit()

		closing_enrty = make_closing_entry_from_opening(opening_entry)
		closing_enrty.submit()
		opening_entry.reload()
		self.assertEqual(opening_entry.status, "Closed")

	def test_validate_pos_profile_and_cashier_TC_ACC_318(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": frappe.generate_hash(length=10) + "@gmail.com",
				"first_name": frappe.generate_hash(length=5),
				"send_welcome_email": 0,
				"enabled": 0,
			}
		)
		user.insert(ignore_permissions=True)
		pos_profile = frappe.get_doc(
			{
				"doctype": "POS Profile",
				"__newname": frappe.generate_hash(length=5),
				"company": "_Test Company",
				"warehouse": "Stores - _TC",
				"write_off_account": "Sales - _TC",
				"write_off_cost_center": "Main - _TC",
				"write_off_limit": 1,
				"payments": [{"default": 1, "mode_of_payment": "Cash"}],
			}
		)
		pos_profile.insert()

		poe = frappe.get_doc(
			{
				"doctype": "POS Opening Entry",
				"company": "_Test Company 1",
				"period_start_date": frappe.utils.now_datetime,
				"posting_date": frappe.utils.today(),
				"pos_profile": pos_profile.name,
				"balance_details": [{"mode_of_payment": "Cash", "opening_amount": 100}],
			}
		)
		with self.assertRaises(frappe.ValidationError) as cm:
			poe.insert(ignore_mandatory=True, ignore_permissions=True)
		self.assertIn(
			f"POS Profile {pos_profile.name} does not belongs to company {poe.company}", str(cm.exception)
		)

		poe.company = pos_profile.company
		poe.user = user.name
		with self.assertRaises(frappe.ValidationError) as cm:
			poe.insert()
		self.assertIn(f"User {user.name} is disabled. Please select valid user/cashier", str(cm.exception))

		user.enabled = 1
		user.save()

		poe_1 = frappe.get_doc(
			{
				"doctype": "POS Opening Entry",
				"company": "_Test Company",
				"period_start_date": frappe.utils.now_datetime,
				"posting_date": frappe.utils.today(),
				"pos_profile": pos_profile.name,
				"user": user.name,
				"balance_details": [{"mode_of_payment": get_mode_of_payment(), "opening_amount": 100}],
			}
		)
		with self.assertRaises(frappe.ValidationError) as cm:
			poe_1.insert()
		self.assertIn(
			"Please set default Cash or Bank account in Mode of Payments __Test Mode Payment",
			str(cm.exception),
		)


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

	return entry


def get_mode_of_payment():
	mode = "__Test Mode Payment"
	if not frappe.db.exists("Mode of Payment", mode):
		frappe.get_doc({"doctype": "Mode of Payment", "mode_of_payment": mode}).insert(
			ignore_permissions=True
		)
	return mode
