# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe

from erpnext.accounts.doctype.accounting_dimension.test_accounting_dimension import (
	create_dimension,
	disable_dimension,
)
from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import (
	make_closing_entry_from_opening,
)
from erpnext.accounts.doctype.pos_invoice.pos_invoice import make_sales_return
from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice
from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.selling.page.point_of_sale.point_of_sale import get_items
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry


class TestPOSClosingEntry(unittest.TestCase):
	def setUp(self):
		# Make stock available for POS Sales
		make_stock_entry(target="_Test Warehouse - _TC", qty=2, basic_rate=100)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.sql("delete from `tabPOS Profile`")

	def test_pos_closing_entry(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv1 = create_pos_invoice(rate=3500, do_not_submit=1)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv1.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv2.submit()

		pcv_doc = make_closing_entry_from_opening(opening_entry)
		payment = pcv_doc.payment_reconciliation[0]

		self.assertEqual(payment.mode_of_payment, "Cash")

		for d in pcv_doc.payment_reconciliation:
			if d.mode_of_payment == "Cash":
				d.closing_amount = 6700

		pcv_doc.submit()

		self.assertEqual(pcv_doc.total_quantity, 2)
		self.assertEqual(pcv_doc.net_total, 6700)

	def test_pos_closing_without_item_code(self):
		"""
		Test if POS Closing Entry is created without item code
		"""
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv = create_pos_invoice(rate=3500, do_not_submit=1, item_name="Test Item", without_item_code=1)
		pos_inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv.submit()

		pcv_doc = make_closing_entry_from_opening(opening_entry)
		pcv_doc.submit()

		self.assertTrue(pcv_doc.name)

	def test_pos_qty_for_item(self):
		"""
		Test if quantity is calculated correctly for an item in POS Closing Entry
		"""
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		test_item_qty = get_test_item_qty(pos_profile)

		pos_inv1 = create_pos_invoice(rate=3500, do_not_submit=1)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv1.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv2.submit()

		# make return entry of pos_inv2
		pos_return = make_sales_return(pos_inv2.name)
		pos_return.paid_amount = pos_return.grand_total
		pos_return.save()
		pos_return.submit()

		pcv_doc = make_closing_entry_from_opening(opening_entry)
		pcv_doc.submit()

		opening_entry = create_opening_entry(pos_profile, test_user.name)
		test_item_qty_after_sales = get_test_item_qty(pos_profile)
		self.assertEqual(test_item_qty_after_sales, test_item_qty - 1)

	def test_cancelling_of_pos_closing_entry(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv1 = create_pos_invoice(rate=3500, do_not_submit=1)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv1.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv2.submit()

		pcv_doc = make_closing_entry_from_opening(opening_entry)
		payment = pcv_doc.payment_reconciliation[0]

		self.assertEqual(payment.mode_of_payment, "Cash")

		for d in pcv_doc.payment_reconciliation:
			if d.mode_of_payment == "Cash":
				d.closing_amount = 6700

		pcv_doc.submit()

		pos_inv1.load_from_db()
		self.assertRaises(frappe.ValidationError, pos_inv1.cancel)

		si_doc = frappe.get_doc("Sales Invoice", pos_inv1.consolidated_invoice)
		self.assertRaises(frappe.ValidationError, si_doc.cancel)

		pcv_doc.load_from_db()
		pcv_doc.cancel()

		cancelled_invoice = frappe.db.get_value(
			"POS Invoice Merge Log", {"pos_closing_entry": pcv_doc.name}, "consolidated_invoice"
		)
		docstatus = frappe.db.get_value("Sales Invoice", cancelled_invoice, "docstatus")
		self.assertEqual(docstatus, 2)

		pos_inv1.load_from_db()
		self.assertEqual(pos_inv1.status, "Paid")

	def test_pos_closing_for_required_accounting_dimension_in_pos_profile(self):
		"""
		test case to check whether we can create POS Closing Entry without mandatory accounting dimension
		"""

		create_dimension()
		pos_profile = make_pos_profile(do_not_insert=1, do_not_set_accounting_dimension=1)

		self.assertRaises(frappe.ValidationError, pos_profile.insert)

		pos_profile.location = "Block 1"
		pos_profile.insert()
		self.assertTrue(frappe.db.exists("POS Profile", pos_profile.name))

		test_user = init_user_and_profile(do_not_create_pos_profile=1)

		opening_entry = create_opening_entry(pos_profile, test_user.name)
		pos_inv1 = create_pos_invoice(rate=350, do_not_submit=1, pos_profile=pos_profile.name)
		pos_inv1.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3500})
		pos_inv1.submit()

		# if in between a mandatory accounting dimension is added to the POS Profile then
		accounting_dimension_department = frappe.get_doc("Accounting Dimension", {"name": "Department"})
		accounting_dimension_department.dimension_defaults[0].mandatory_for_bs = 1
		accounting_dimension_department.save()

		pcv_doc = make_closing_entry_from_opening(opening_entry)
		# will assert coz the new mandatory accounting dimension bank is not set in POS Profile
		self.assertRaises(frappe.ValidationError, pcv_doc.submit)

		accounting_dimension_department = frappe.get_doc(
			"Accounting Dimension Detail", {"parent": "Department"}
		)
		accounting_dimension_department.mandatory_for_bs = 0
		accounting_dimension_department.save()
		disable_dimension()


def init_user_and_profile(**args):
	user = "test@example.com"
	test_user = frappe.get_doc("User", user)

	roles = ("Accounts Manager", "Accounts User", "Sales Manager")
	test_user.add_roles(*roles)
	frappe.set_user(user)

	if args.get("do_not_create_pos_profile"):
		return test_user

	pos_profile = make_pos_profile(**args)
	pos_profile.append("applicable_for_users", {"default": 1, "user": user})

	pos_profile.save()

	return test_user, pos_profile


def get_test_item_qty(pos_profile):
	test_item_pos = get_items(
		start=0,
		page_length=5,
		price_list="Standard Selling",
		pos_profile=pos_profile.name,
		search_term="_Test Item",
		item_group="All Item Groups",
	)

	test_item_qty = next(item for item in test_item_pos["items"] if item["item_code"] == "_Test Item").get(
		"actual_qty"
	)
	return test_item_qty
