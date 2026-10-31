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

	def test_end_date_before_start_date_is_refused(self):
		doc = self.make_bg(start_date="2026-06-30", end_date="2026-06-01")
		self.assertRaisesRegex(frappe.ValidationError, "cannot be before Start Date", doc.insert)

	def test_end_date_is_computed_from_validity(self):
		doc = self.make_bg(start_date="2026-03-01")
		doc.validity = 30
		doc.insert()
		self.assertEqual(str(doc.end_date), "2026-03-30")

	def test_negative_amount_is_refused(self):
		doc = self.make_bg(amount=-1000)
		self.assertRaises(frappe.NonNegativeError, doc.insert)

	def test_party_and_project_come_from_the_reference(self):
		so = make_sales_order()
		doc = self.make_bg(customer="_Test Customer 1", supplier="_Test Supplier")
		doc.reference_doctype = "Sales Order"
		doc.reference_docname = so.name
		doc.insert()

		self.assertEqual(doc.reference_doctype, "Sales Order")
		self.assertEqual(doc.customer, so.customer)
		self.assertFalse(doc.supplier)

	def test_reference_must_be_a_submitted_order_of_the_type(self):
		doc = self.make_bg()
		doc.reference_doctype = "User"
		doc.reference_docname = "Administrator"
		self.assertRaisesRegex(frappe.ValidationError, "must be a Sales Order", doc.insert)

		draft = make_sales_order(do_not_submit=True)
		doc = self.make_bg()
		doc.reference_doctype = "Sales Order"
		doc.reference_docname = draft.name
		self.assertRaisesRegex(frappe.ValidationError, "must be submitted", doc.insert)

	def test_reference_of_another_company_is_refused(self):
		so = make_sales_order()
		user = "test_bg_company_restriction@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "BG", "roles": [{"role": "Accounts User"}]}
			).insert()
		frappe.permissions.add_user_permission("Company", "_Test Company 1", user)

		doc = self.make_bg()
		doc.reference_doctype = "Sales Order"
		doc.reference_docname = so.name
		with self.set_user(user):
			self.assertRaisesRegex(
				frappe.PermissionError, "Not permitted for _Test Company", doc.insert, ignore_permissions=True
			)
