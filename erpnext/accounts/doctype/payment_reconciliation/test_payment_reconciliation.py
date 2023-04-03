# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, getdate

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice


class TestPaymentReconciliation(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		make_customer()
		make_invoice_and_payment()

	def test_payment_reconciliation(self):
		payment_reco = frappe.get_doc("Payment Reconciliation")
		payment_reco.company = "_Test Company"
		payment_reco.party_type = "Customer"
		payment_reco.party = "_Test Payment Reco Customer"
		payment_reco.receivable_payable_account = "Debtors - _TC"
		payment_reco.from_invoice_date = add_days(getdate(), -1)
		payment_reco.to_invoice_date = getdate()
		payment_reco.from_payment_date = add_days(getdate(), -1)
		payment_reco.to_payment_date = getdate()
		payment_reco.maximum_invoice_amount = 1000
		payment_reco.maximum_payment_amount = 1000
		payment_reco.invoice_limit = 10
		payment_reco.payment_limit = 10
		payment_reco.bank_cash_account = "_Test Bank - _TC"
		payment_reco.cost_center = "_Test Cost Center - _TC"
		payment_reco.get_unreconciled_entries()

		self.assertEqual(len(payment_reco.get("invoices")), 1)
		self.assertEqual(len(payment_reco.get("payments")), 1)

		payment_entry = payment_reco.get("payments")[0].reference_name
		invoice = payment_reco.get("invoices")[0].invoice_number

		payment_reco.allocate_entries(
			{
				"payments": [payment_reco.get("payments")[0].as_dict()],
				"invoices": [payment_reco.get("invoices")[0].as_dict()],
			}
		)
		payment_reco.reconcile()

		payment_entry_doc = frappe.get_doc("Payment Entry", payment_entry)
		self.assertEqual(payment_entry_doc.get("references")[0].reference_name, invoice)


def make_customer():
	if not frappe.db.get_value("Customer", "_Test Payment Reco Customer"):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test Payment Reco Customer",
				"customer_type": "Individual",
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
			}
		).insert()


def make_invoice_and_payment():
	si = create_sales_invoice(
		customer="_Test Payment Reco Customer", qty=1, rate=690, do_not_save=True
	)
	si.cost_center = "_Test Cost Center - _TC"
	si.save()
	si.submit()

	pe = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"party_type": "Customer",
			"party": "_Test Payment Reco Customer",
			"company": "_Test Company",
			"paid_from_account_currency": "INR",
			"paid_to_account_currency": "INR",
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"reference_no": "1",
			"reference_date": getdate(),
			"received_amount": 690,
			"paid_amount": 690,
			"paid_from": "Debtors - _TC",
			"paid_to": "_Test Bank - _TC",
			"cost_center": "_Test Cost Center - _TC",
		}
	)
	pe.insert()
	pe.submit()
