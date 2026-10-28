# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.accounts.doctype.payment_request.payment_request import get_gateway_details
from erpnext.tests.utils import ERPNextTestSuite

GATEWAY = "_Test PGA Gateway"


class TestPaymentGatewayAccount(ERPNextTestSuite):
	def setUp(self):
		if not frappe.db.table_exists("Payment Gateway"):
			self.skipTest("Payment Gateway is not installed")
		if not frappe.db.exists("Payment Gateway", GATEWAY):
			frappe.get_doc({"doctype": "Payment Gateway", "gateway": GATEWAY}).insert()

	def make_gateway_account(self, payment_account, **kwargs):
		return frappe.get_doc(
			{
				"doctype": "Payment Gateway Account",
				"payment_gateway": GATEWAY,
				"payment_account": payment_account,
				"company": "_Test Company",
				**kwargs,
			}
		).insert()

	def test_currency_set_from_payment_account(self):
		account = self.make_gateway_account("_Test Bank USD - _TC")
		self.assertEqual(account.currency, "USD")
		self.assertEqual(account.name, f"{GATEWAY} - USD - _TC")

	def test_payment_account_must_be_bank_or_cash(self):
		for payment_account in ("Bank Accounts - _TC", "Debtors - _TC", "Sales - _TC"):
			self.assertRaisesRegex(
				frappe.ValidationError,
				"must be a Bank or Cash account",
				self.make_gateway_account,
				payment_account,
			)

	def test_default_for_each_currency(self):
		inr = self.make_gateway_account("_Test Bank - _TC", is_default=1)
		usd = self.make_gateway_account("_Test Bank USD - _TC", is_default=1)
		self.assertEqual(frappe.db.get_value("Payment Gateway Account", inr.name, "is_default"), 1)
		self.assertEqual(frappe.db.get_value("Payment Gateway Account", usd.name, "is_default"), 1)

	def test_gateway_account_in_currency(self):
		self.make_gateway_account("_Test Bank - _TC", is_default=1)
		self.make_gateway_account("_Test Bank USD - _TC")
		args = frappe._dict(company="_Test Company")

		usd = get_gateway_details(args, "USD")
		self.assertEqual(usd.payment_account, "_Test Bank USD - _TC")

		# no gateway account in the currency: the default of the company currency
		eur = get_gateway_details(args, "EUR")
		self.assertEqual(frappe.db.get_value("Payment Gateway Account", eur.name, "currency"), "INR")
