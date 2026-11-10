# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import flt

from erpnext.accounts.doctype.bank_guarantee.bank_guarantee import get_voucher_details
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite

BANK = "_Test BG Bank"


class TestBankGuarantee(ERPNextTestSuite):
	"""Bank Guarantee records a guarantee issued/received against a customer or
	supplier. validate() needs a party; on_submit() needs the bank details filled in."""

	def setUp(self):
		frappe.set_user("Administrator")
		if not frappe.db.exists("Bank", BANK):
			frappe.get_doc({"doctype": "Bank", "bank_name": BANK}).insert()

	def make_bg(self, **args):
		args = frappe._dict(args)
		doc = frappe.new_doc("Bank Guarantee")
		doc.bg_type = args.bg_type or "Receiving"
		doc.amount = args.amount if args.amount is not None else 1000
		doc.start_date = args.start_date or "2026-06-01"
		if args.end_date:
			doc.end_date = args.end_date
		doc.customer = args.get("customer", "_Test Customer")
		doc.supplier = args.get("supplier")
		# fields on_submit requires — present by default, cleared per-test to assert the guard
		doc.bank_guarantee_number = args.get("bank_guarantee_number", "BG-001")
		doc.name_of_beneficiary = args.get("name_of_beneficiary", "Test Beneficiary")
		doc.bank = args.get("bank", BANK)
		return doc

	def test_validate_requires_customer_or_supplier(self):
		doc = self.make_bg(customer=None)
		self.assertRaises(frappe.ValidationError, doc.insert)

	def test_submit_requires_guarantee_number(self):
		doc = self.make_bg(bank_guarantee_number="")
		doc.insert()
		self.assertRaises(frappe.ValidationError, doc.submit)

	def test_submit_requires_beneficiary_name(self):
		doc = self.make_bg(name_of_beneficiary="")
		doc.insert()
		self.assertRaises(frappe.ValidationError, doc.submit)

	def test_submit_requires_bank(self):
		doc = self.make_bg(bank="")
		doc.insert()
		self.assertRaises(frappe.ValidationError, doc.submit)

	def test_valid_guarantee_submits(self):
		doc = self.make_bg()
		doc.insert()
		doc.submit()
		self.assertEqual(frappe.db.get_value("Bank Guarantee", doc.name, "docstatus"), 1)

	def test_get_voucher_details_for_receiving(self):
		so = make_sales_order()
		details = get_voucher_details("Receiving", so.name)
		self.assertEqual(details.customer, so.customer)
		self.assertEqual(flt(details.grand_total), flt(so.grand_total))

	def test_end_date_before_start_date_is_not_validated(self):
		# SUSPECTED BUG: validate() never checks that end_date >= start_date, so a
		# guarantee that expires before it starts saves cleanly. Locking the current
		# (wrong) behaviour so a future fix that adds the check trips this test.
		doc = self.make_bg(start_date="2026-06-30", end_date="2026-06-01")
		doc.insert()
		self.assertTrue(frappe.db.exists("Bank Guarantee", doc.name))
