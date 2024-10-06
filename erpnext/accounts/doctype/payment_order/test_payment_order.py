# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import getdate

from erpnext.accounts.doctype.bank_transaction.test_bank_transaction import (
	create_bank_account,
	create_gl_account,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_payment_entry,
	make_payment_order,
)
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice


class UnitTestPaymentOrder(UnitTestCase):
	"""
	Unit tests for PaymentOrder.
	Use this class for testing individual functions and methods.
	"""

	pass


class TestPaymentOrder(IntegrationTestCase):
	def setUp(self):
		# generate and use a uniq hash identifier for 'Bank Account' and it's linked GL 'Account' to avoid validation error
		uniq_identifier = frappe.generate_hash(length=10)
		self.gl_account = create_gl_account("_Test Bank " + uniq_identifier)
		self.bank_account = create_bank_account(
			gl_account=self.gl_account, bank_account_name="Checking Account " + uniq_identifier
		)

	def tearDown(self):
		frappe.db.rollback()

	def test_payment_order_creation_against_payment_entry(self):
		purchase_invoice = make_purchase_invoice()
		payment_entry = get_payment_entry(
			"Purchase Invoice", purchase_invoice.name, bank_account=self.gl_account
		)
		payment_entry.reference_no = "_Test_Payment_Order"
		payment_entry.reference_date = getdate()
		payment_entry.party_bank_account = self.bank_account
		payment_entry.insert()
		payment_entry.submit()

		doc = create_payment_order_against_payment_entry(payment_entry, "Payment Entry", self.bank_account)
		reference_doc = doc.get("references")[0]
		self.assertEqual(reference_doc.reference_name, payment_entry.name)
		self.assertEqual(reference_doc.reference_doctype, "Payment Entry")
		self.assertEqual(reference_doc.supplier, "_Test Supplier")
		self.assertEqual(reference_doc.amount, 250)


def create_payment_order_against_payment_entry(ref_doc, order_type, bank_account):
	payment_order = frappe.get_doc(
		dict(
			doctype="Payment Order",
			company="_Test Company",
			payment_order_type=order_type,
			company_bank_account=bank_account,
		)
	)
	doc = make_payment_order(ref_doc.name, payment_order)
	doc.save()
	doc.submit()
	return doc
