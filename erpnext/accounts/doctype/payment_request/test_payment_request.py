# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest
from unittest.mock import patch

import frappe

from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.setup.utils import get_exchange_rate

test_dependencies = ["Currency Exchange", "Journal Entry", "Contact", "Address"]

PAYMENT_URL = "https://example.com/payment"

payment_gateways = [
	{"doctype": "Payment Gateway", "gateway": "_Test Gateway"},
	{"doctype": "Payment Gateway", "gateway": "_Test Gateway Phone"},
	{"doctype": "Payment Gateway", "gateway": "_Test Gateway Other"},
]

payment_method = [
	{
		"doctype": "Payment Gateway Account",
		"is_default": 1,
		"payment_gateway": "_Test Gateway",
		"payment_account": "_Test Bank - _TC",
		"currency": "INR",
	},
	{
		"doctype": "Payment Gateway Account",
		"payment_gateway": "_Test Gateway",
		"payment_account": "_Test Bank USD - _TC",
		"currency": "USD",
	},
	{
		"doctype": "Payment Gateway Account",
		"payment_gateway": "_Test Gateway Other",
		"payment_account": "_Test Bank USD - _TC",
		"payment_channel": "Other",
		"currency": "USD",
	},
	{
		"doctype": "Payment Gateway Account",
		"payment_gateway": "_Test Gateway Phone",
		"payment_account": "_Test Bank USD - _TC",
		"payment_channel": "Phone",
		"currency": "USD",
	},
]


class TestPaymentRequest(unittest.TestCase):
	def setUp(self):
		for payment_gateway in payment_gateways:
			if not frappe.db.get_value("Payment Gateway", payment_gateway["gateway"], "name"):
				frappe.get_doc(payment_gateway).insert(ignore_permissions=True)

		for method in payment_method:
			if not frappe.db.get_value(
				"Payment Gateway Account",
				{"payment_gateway": method["payment_gateway"], "currency": method["currency"]},
				"name",
			):
				frappe.get_doc(method).insert(ignore_permissions=True)

		send_email = patch(
			"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.send_email",
			return_value=None,
		)
		self.send_email = send_email.start()
		self.addCleanup(send_email.stop)
		get_payment_url = patch(
			# this also shadows one (1) call to _get_payment_gateway_controller
			"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.get_payment_url",
			return_value=PAYMENT_URL,
		)
		self.get_payment_url = get_payment_url.start()
		self.addCleanup(get_payment_url.stop)
		_get_payment_gateway_controller = patch(
			"erpnext.accounts.doctype.payment_request.payment_request._get_payment_gateway_controller",
		)
		self._get_payment_gateway_controller = _get_payment_gateway_controller.start()
		self.addCleanup(_get_payment_gateway_controller.stop)

	def test_payment_request_linkings(self):
		so_inr = make_sales_order(currency="INR", do_not_save=True)
		so_inr.disable_rounded_total = 1
		so_inr.save()

		pr = make_payment_request(
			dt="Sales Order",
			dn=so_inr.name,
			recipient_id="saurabh@erpnext.com",
			payment_gateway_account="_Test Gateway - INR",
		)

		self.assertEqual(pr.reference_doctype, "Sales Order")
		self.assertEqual(pr.reference_name, so_inr.name)
		self.assertEqual(pr.currency, "INR")

		conversion_rate = get_exchange_rate("USD", "INR")

		si_usd = create_sales_invoice(currency="USD", conversion_rate=conversion_rate)
		pr = make_payment_request(
			dt="Sales Invoice",
			dn=si_usd.name,
			recipient_id="saurabh@erpnext.com",
			payment_gateway_account="_Test Gateway - USD",
		)

		self.assertEqual(pr.reference_doctype, "Sales Invoice")
		self.assertEqual(pr.reference_name, si_usd.name)
		self.assertEqual(pr.currency, "USD")

	def test_payment_channels(self):
		so = make_sales_order(currency="USD")

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			payment_gateway_account="_Test Gateway Other - USD",
			submit_doc=True,
			return_doc=True,
		)
		self.assertEqual(pr.payment_channel, "Other")
		self.assertEqual(pr.mute_email, True)

		self.assertEqual(pr.payment_url, PAYMENT_URL)
		self.assertEqual(self.send_email.call_count, 0)
		self.assertEqual(self._get_payment_gateway_controller.call_count, 1)
		pr.cancel()

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			payment_gateway_account="_Test Gateway - USD",  # email channel
			submit_doc=False,
			return_doc=True,
		)
		pr.flags.mute_email = True  # but temporarily prohibit sending
		pr.submit()
		pr.reload()
		self.assertEqual(pr.payment_channel, "Email")
		self.assertEqual(pr.mute_email, False)

		self.assertEqual(pr.payment_url, PAYMENT_URL)
		self.assertEqual(self.send_email.call_count, 0)  # hence: no increment
		self.assertEqual(self._get_payment_gateway_controller.call_count, 2)
		pr.cancel()

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			payment_gateway_account="_Test Gateway Phone - USD",
			submit_doc=True,
			return_doc=True,
		)
		pr.reload()

		self.assertEqual(pr.payment_channel, "Phone")
		self.assertEqual(pr.mute_email, True)

		self.assertIsNone(pr.payment_url)
		self.assertEqual(self.send_email.call_count, 0)  # no increment on phone channel
		self.assertEqual(self._get_payment_gateway_controller.call_count, 3)
		pr.cancel()

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			payment_gateway_account="_Test Gateway - USD",  # email channel
			submit_doc=True,
			return_doc=True,
		)
		pr.reload()

		self.assertEqual(pr.payment_channel, "Email")
		self.assertEqual(pr.mute_email, False)

		self.assertEqual(pr.payment_url, PAYMENT_URL)
		self.assertEqual(self.send_email.call_count, 1)  # increment on normal email channel
		self.assertEqual(self._get_payment_gateway_controller.call_count, 4)
		pr.cancel()

		so = make_sales_order(currency="USD", do_not_save=True)
		# no-op; for optical consistency with how a webshop SO would look like
		so.order_type = "Shopping Cart"
		so.save()
		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			payment_gateway_account="_Test Gateway - USD",  # email channel
			make_sales_invoice=True,
			mute_email=True,
			submit_doc=True,
			return_doc=True,
		)
		pr.reload()

		self.assertEqual(pr.payment_channel, "Email")
		self.assertEqual(pr.mute_email, True)

		self.assertEqual(pr.payment_url, PAYMENT_URL)
		self.assertEqual(self.send_email.call_count, 1)  # no increment on shopping cart
		self.assertEqual(self._get_payment_gateway_controller.call_count, 5)
		pr.cancel()

	def test_payment_entry_against_purchase_invoice(self):
		si_usd = make_purchase_invoice(
			customer="_Test Supplier USD",
			debit_to="_Test Payable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		pr = make_payment_request(
			dt="Purchase Invoice",
			dn=si_usd.name,
			party_type="Supplier",
			party="_Test Supplier USD",
			recipient_id="user@example.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - USD",
			submit_doc=1,
			return_doc=1,
		)

		pr.create_payment_entry()
		pr.load_from_db()

		self.assertEqual(pr.status, "Paid")

	def test_multiple_payment_entry_against_purchase_invoice(self):
		purchase_invoice = make_purchase_invoice(
			customer="_Test Supplier USD",
			debit_to="_Test Payable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		pr = make_payment_request(
			dt="Purchase Invoice",
			party_type="Supplier",
			party="_Test Supplier USD",
			dn=purchase_invoice.name,
			recipient_id="user@example.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - USD",
			return_doc=1,
		)

		pr.grand_total = pr.grand_total / 2

		pr.submit()
		pr.create_payment_entry()

		purchase_invoice.load_from_db()
		self.assertEqual(purchase_invoice.status, "Partly Paid")

		pr = make_payment_request(
			dt="Purchase Invoice",
			party_type="Supplier",
			party="_Test Supplier USD",
			dn=purchase_invoice.name,
			recipient_id="user@example.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - USD",
			return_doc=1,
		)

		pr.save()
		pr.submit()
		pr.create_payment_entry()

		purchase_invoice.load_from_db()
		self.assertEqual(purchase_invoice.status, "Paid")

	def test_payment_entry(self):
		frappe.db.set_value(
			"Company", "_Test Company", "exchange_gain_loss_account", "_Test Exchange Gain/Loss - _TC"
		)
		frappe.db.set_value("Company", "_Test Company", "write_off_account", "_Test Write Off - _TC")
		frappe.db.set_value("Company", "_Test Company", "cost_center", "_Test Cost Center - _TC")

		so_inr = make_sales_order(currency="INR")
		pr = make_payment_request(
			dt="Sales Order",
			dn=so_inr.name,
			recipient_id="saurabh@erpnext.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - INR",
			submit_doc=1,
			return_doc=1,
		)
		pe = pr.set_as_paid()

		so_inr = frappe.get_doc("Sales Order", so_inr.name)

		self.assertEqual(so_inr.advance_paid, 1000)

		si_usd = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		pr = make_payment_request(
			dt="Sales Invoice",
			dn=si_usd.name,
			recipient_id="saurabh@erpnext.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - USD",
			submit_doc=1,
			return_doc=1,
		)

		pe = pr.set_as_paid()

		expected_gle = dict(
			(d[0], d)
			for d in [
				["_Test Receivable USD - _TC", 0, 5000, si_usd.name],
				[pr.payment_account, 5000.0, 0, None],
			]
		)

		gl_entries = frappe.db.sql(
			"""select account, debit, credit, against_voucher
			from `tabGL Entry` where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""",
			pe.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gle[gle.account][0], gle.account)
			self.assertEqual(expected_gle[gle.account][1], gle.debit)
			self.assertEqual(expected_gle[gle.account][2], gle.credit)
			self.assertEqual(expected_gle[gle.account][3], gle.against_voucher)

	def test_status(self):
		si_usd = create_sales_invoice(
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		pr = make_payment_request(
			dt="Sales Invoice",
			dn=si_usd.name,
			recipient_id="saurabh@erpnext.com",
			mute_email=1,
			payment_gateway_account="_Test Gateway - USD",
			submit_doc=1,
			return_doc=1,
		)

		pe = pr.create_payment_entry()
		pr.load_from_db()

		self.assertEqual(pr.status, "Paid")

		pe.cancel()
		pr.load_from_db()

		self.assertEqual(pr.status, "Requested")

	def test_multiple_payment_entries_against_sales_order(self):
		# Make Sales Order, grand_total = 1000
		so = make_sales_order()

		# Payment Request amount = 200
		pr1 = make_payment_request(
			dt="Sales Order", dn=so.name, recipient_id="nabin@erpnext.com", return_doc=1
		)
		pr1.grand_total = 200
		pr1.submit()

		# Make a 2nd Payment Request
		pr2 = make_payment_request(
			dt="Sales Order", dn=so.name, recipient_id="nabin@erpnext.com", return_doc=1
		)

		self.assertEqual(pr2.grand_total, 800)

		# Try to make Payment Request more than SO amount, should give validation
		pr2.grand_total = 900
		self.assertRaises(frappe.ValidationError, pr2.save)
