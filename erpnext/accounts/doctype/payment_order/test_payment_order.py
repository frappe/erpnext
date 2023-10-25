# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import getdate

from erpnext.accounts.doctype.bank_transaction.test_bank_transaction import create_bank_account
from erpnext.accounts.doctype.payment_entry.payment_entry import (
	get_payment_entry,
	make_payment_order,
)
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice


class TestPaymentOrder(unittest.TestCase):
	def setUp(self):
		create_bank_account()

	def tearDown(self):
		for bt in frappe.get_all("Payment Order"):
			doc = frappe.get_doc("Payment Order", bt.name)
			doc.cancel()
			doc.delete()

	def test_payment_order_creation_against_payment_entry(self):
		purchase_invoice = make_purchase_invoice()
		payment_entry = get_payment_entry(
			"Purchase Invoice", purchase_invoice.name, bank_account="_Test Bank - _TC"
		)
		payment_entry.reference_no = "_Test_Payment_Order"
		payment_entry.reference_date = getdate()
		payment_entry.party_bank_account = "Checking Account - Citi Bank"
		payment_entry.insert()
		payment_entry.submit()

		doc = create_payment_order_against_payment_entry(payment_entry, "Payment Entry")
		reference_doc = doc.get("references")[0]
		self.assertEqual(reference_doc.reference_name, payment_entry.name)
		self.assertEqual(reference_doc.reference_doctype, "Payment Entry")
		self.assertEqual(reference_doc.supplier, "_Test Supplier")
		self.assertEqual(reference_doc.amount, 250)


def create_payment_order_against_payment_entry(ref_doc, order_type):
	payment_order = frappe.get_doc(
		dict(
			doctype="Payment Order",
			company="_Test Company",
			payment_order_type=order_type,
			company_bank_account="Checking Account - Citi Bank",
		)
	)
	doc = make_payment_order(ref_doc.name, payment_order)
	doc.save()
	doc.submit()
	return doc
