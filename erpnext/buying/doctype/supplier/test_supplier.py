# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.test_runner import make_test_records

from erpnext.accounts.party import get_due_date
from erpnext.exceptions import PartyDisabled

test_dependencies = ["Payment Term", "Payment Terms Template"]
test_records = frappe.get_test_records("Supplier")

from frappe.tests.utils import FrappeTestCase


class TestSupplier(FrappeTestCase):
	def test_get_supplier_group_details(self):
		doc = frappe.new_doc("Supplier Group")
		doc.supplier_group_name = "_Testing Supplier Group"
		doc.payment_terms = "_Test Payment Term Template 3"
		doc.accounts = []
		test_account_details = {
			"company": "_Test Company",
			"account": "Creditors - _TC",
		}
		doc.append("accounts", test_account_details)
		doc.save()
		s_doc = frappe.new_doc("Supplier")
		s_doc.supplier_name = "Testing Supplier"
		s_doc.supplier_group = "_Testing Supplier Group"
		s_doc.payment_terms = ""
		s_doc.accounts = []
		s_doc.insert()
		s_doc.get_supplier_group_details()
		self.assertEqual(s_doc.payment_terms, "_Test Payment Term Template 3")
		self.assertEqual(s_doc.accounts[0].company, "_Test Company")
		self.assertEqual(s_doc.accounts[0].account, "Creditors - _TC")
		s_doc.delete()
		doc.delete()

	def test_supplier_default_payment_terms(self):
		# Payment Term based on Days after invoice date
		frappe.db.set_value(
			"Supplier", "_Test Supplier With Template 1", "payment_terms", "_Test Payment Term Template 3"
		)

		due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier With Template 1")
		self.assertEqual(due_date, "2016-02-21")

		due_date = get_due_date("2017-01-22", "Supplier", "_Test Supplier With Template 1")
		self.assertEqual(due_date, "2017-02-21")

		# Payment Term based on last day of month
		frappe.db.set_value(
			"Supplier", "_Test Supplier With Template 1", "payment_terms", "_Test Payment Term Template 1"
		)

		due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier With Template 1")
		self.assertEqual(due_date, "2016-02-29")

		due_date = get_due_date("2017-01-22", "Supplier", "_Test Supplier With Template 1")
		self.assertEqual(due_date, "2017-02-28")

		frappe.db.set_value("Supplier", "_Test Supplier With Template 1", "payment_terms", "")

		# Set credit limit for the supplier group instead of supplier and evaluate the due date
		frappe.db.set_value(
			"Supplier Group", "_Test Supplier Group", "payment_terms", "_Test Payment Term Template 3"
		)

		due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier With Template 1")
		self.assertEqual(due_date, "2016-02-21")

		# Payment terms for Supplier Group instead of supplier and evaluate the due date
		frappe.db.set_value(
			"Supplier Group", "_Test Supplier Group", "payment_terms", "_Test Payment Term Template 1"
		)

		# Leap year
		due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier With Template 1")
		self.assertEqual(due_date, "2016-02-29")
		# # Non Leap year
		due_date = get_due_date("2017-01-22", "Supplier", "_Test Supplier With Template 1")
		self.assertEqual(due_date, "2017-02-28")

		# Supplier with no default Payment Terms Template
		frappe.db.set_value("Supplier Group", "_Test Supplier Group", "payment_terms", "")
		frappe.db.set_value("Supplier", "_Test Supplier", "payment_terms", "")

		due_date = get_due_date("2016-01-22", "Supplier", "_Test Supplier")
		self.assertEqual(due_date, "2016-01-22")
		# # Non Leap year
		due_date = get_due_date("2017-01-22", "Supplier", "_Test Supplier")
		self.assertEqual(due_date, "2017-01-22")

	def test_supplier_disabled(self):
		make_test_records("Item")

		frappe.db.set_value("Supplier", "_Test Supplier", "disabled", 1)

		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		po = create_purchase_order(do_not_save=True)

		self.assertRaises(PartyDisabled, po.save)

		frappe.db.set_value("Supplier", "_Test Supplier", "disabled", 0)

		po.save()

	def test_supplier_country(self):
		# Test that country field exists in Supplier DocType
		supplier = frappe.get_doc("Supplier", "_Test Supplier with Country")
		self.assertTrue("country" in supplier.as_dict())

		# Test if test supplier field record is 'Greece'
		self.assertEqual(supplier.country, "Greece")

		# Test update Supplier instance country value
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.country = "Greece"
		supplier.save()
		self.assertEqual(supplier.country, "Greece")

	def test_party_details_tax_category(self):
		from erpnext.accounts.party import get_party_details

		frappe.delete_doc_if_exists("Address", "_Test Address With Tax Category-Billing")

		# Tax Category without Address
		details = get_party_details("_Test Supplier With Tax Category", party_type="Supplier")
		self.assertEqual(details.tax_category, "_Test Tax Category 1")

		address = frappe.get_doc(
			dict(
				doctype="Address",
				address_title="_Test Address With Tax Category",
				tax_category="_Test Tax Category 2",
				address_type="Billing",
				address_line1="Station Road",
				city="_Test City",
				country="India",
				links=[dict(link_doctype="Supplier", link_name="_Test Supplier With Tax Category")],
			)
		).insert()

		# Tax Category with Address
		details = get_party_details("_Test Supplier With Tax Category", party_type="Supplier")
		self.assertEqual(details.tax_category, "_Test Tax Category 2")

		# Rollback
		address.delete()


def create_supplier(**args):
	args = frappe._dict(args)

	if frappe.db.exists("Supplier", args.supplier_name):
		return frappe.get_doc("Supplier", args.supplier_name)

	doc = frappe.get_doc(
		{
			"doctype": "Supplier",
			"supplier_name": args.supplier_name,
			"supplier_group": args.supplier_group or "Services",
			"supplier_type": args.supplier_type or "Company",
			"tax_withholding_category": args.tax_withholding_category,
		}
	).insert()

	return doc
