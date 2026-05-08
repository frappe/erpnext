# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import re
import sys
from unittest.mock import MagicMock, patch

import frappe
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_terms_template
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.setup.utils import get_exchange_rate
from erpnext.tests.utils import ERPNextTestSuite

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
		"company": "_Test Company",
	},
	{
		"doctype": "Payment Gateway Account",
		"payment_gateway": "_Test Gateway",
		"payment_account": "_Test Bank USD - _TC",
		"currency": "USD",
		"company": "_Test Company",
	},
	{
		"doctype": "Payment Gateway Account",
		"payment_gateway": "_Test Gateway Other",
		"payment_account": "_Test Bank USD - _TC",
		"payment_channel": "Other",
		"currency": "USD",
		"company": "_Test Company",
	},
	{
		"doctype": "Payment Gateway Account",
		"payment_gateway": "_Test Gateway Phone",
		"payment_account": "_Test Bank USD - _TC",
		"payment_channel": "Phone",
		"currency": "USD",
		"company": "_Test Company",
	},
]


class TestPaymentRequest(ERPNextTestSuite):
	def setUp(self):
		for payment_gateway in payment_gateways:
			if not frappe.db.get_value("Payment Gateway", payment_gateway["gateway"], "name"):
				frappe.get_doc(payment_gateway).insert(ignore_permissions=True)

		for method in payment_method:
			if not frappe.db.get_value(
				"Payment Gateway Account",
				{
					"payment_gateway": method["payment_gateway"],
					"currency": method["currency"],
					"company": method["company"],
				},
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
			payment_gateway_account="_Test Gateway - INR - _TC",
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
			payment_gateway_account="_Test Gateway - USD - _TC",
		)

		self.assertEqual(pr.reference_doctype, "Sales Invoice")
		self.assertEqual(pr.reference_name, si_usd.name)
		self.assertEqual(pr.currency, "USD")

	def test_payment_channels(self):
		so = make_sales_order(currency="USD")

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			payment_gateway_account="_Test Gateway Other - USD - _TC",
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
			payment_gateway_account="_Test Gateway - USD - _TC",  # email channel
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
			payment_gateway_account="_Test Gateway Phone - USD - _TC",
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
			payment_gateway_account="_Test Gateway - USD - _TC",  # email channel
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
			payment_gateway_account="_Test Gateway - USD - _TC",  # email channel
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
			supplier="_Test Supplier USD",
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
			payment_gateway_account="_Test Gateway - USD - _TC",
			submit_doc=1,
			return_doc=1,
		)

		pr.create_payment_entry()
		pr.load_from_db()

		self.assertEqual(pr.status, "Paid")

	def test_multiple_payment_entry_against_purchase_invoice(self):
		purchase_invoice = make_purchase_invoice(
			supplier="_Test Supplier USD",
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
			payment_gateway_account="_Test Gateway - USD - _TC",
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
			payment_gateway_account="_Test Gateway - USD - _TC",
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
			payment_gateway_account="_Test Gateway - INR - _TC",
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
			payment_gateway_account="_Test Gateway - USD - _TC",
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
			payment_gateway_account="_Test Gateway - USD - _TC",
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

	def test_conversion_on_foreign_currency_accounts(self):
		po_doc = create_purchase_order(supplier="_Test Supplier USD", currency="USD", do_not_submit=1)
		po_doc.conversion_rate = 80
		po_doc.items[0].qty = 1
		po_doc.items[0].rate = 10
		po_doc.save().submit()

		pr = make_payment_request(dt=po_doc.doctype, dn=po_doc.name, recipient_id="nabin@erpnext.com")
		pr = frappe.get_doc(pr).save().submit()

		pe = pr.create_payment_entry()
		self.assertEqual(pe.base_paid_amount, 800)
		self.assertEqual(pe.paid_amount, 800)
		self.assertEqual(pe.base_received_amount, 800)
		self.assertEqual(pe.received_amount, 10)

	def test_multiple_payment_if_partially_paid_for_same_currency(self):
		so = make_sales_order(currency="INR", qty=1, rate=1000)

		self.assertEqual(so.advance_payment_status, "Not Requested")

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)

		self.assertEqual(pr.grand_total, 1000)
		self.assertEqual(pr.outstanding_amount, pr.grand_total)
		self.assertEqual(pr.party_account_currency, pr.currency)  # INR
		self.assertEqual(pr.status, "Requested")

		so.load_from_db()
		self.assertEqual(so.advance_payment_status, "Requested")

		# to make partial payment
		pe = pr.create_payment_entry(submit=False)
		pe.paid_amount = 200
		pe.references[0].allocated_amount = 200
		pe.submit()

		self.assertEqual(pe.references[0].payment_request, pr.name)

		so.load_from_db()
		self.assertEqual(so.advance_payment_status, "Partially Paid")

		pr.load_from_db()
		self.assertEqual(pr.status, "Partially Paid")
		self.assertEqual(pr.outstanding_amount, 800)
		self.assertEqual(pr.grand_total, 1000)

		self.assertRaisesRegex(
			frappe.exceptions.ValidationError,
			re.compile(r"Payment Request is already created"),
			make_payment_request,
			dt="Sales Order",
			dn=so.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)
		# complete payment
		pe = pr.create_payment_entry()

		self.assertEqual(pe.paid_amount, 800)  # paid amount set from pr's outstanding amount
		self.assertEqual(pe.references[0].allocated_amount, 800)
		self.assertEqual(pe.references[0].outstanding_amount, 0)  # Also for orders it will zero
		self.assertEqual(pe.references[0].payment_request, pr.name)

		so.load_from_db()
		self.assertEqual(so.advance_payment_status, "Fully Paid")

		pr.load_from_db()
		self.assertEqual(pr.status, "Paid")
		self.assertEqual(pr.outstanding_amount, 0)
		self.assertEqual(pr.grand_total, 1000)

		# creating a more payment Request must not allowed
		self.assertRaisesRegex(
			frappe.exceptions.ValidationError,
			re.compile(r"Payment Entry is already created"),
			make_payment_request,
			dt="Sales Order",
			dn=so.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)

	@ERPNextTestSuite.change_settings(
		"Accounts Settings", {"allow_multi_currency_invoices_against_single_party_account": 1}
	)
	def test_multiple_payment_if_partially_paid_for_multi_currency(self):
		pi = make_purchase_invoice(currency="USD", conversion_rate=50, qty=1, rate=100, do_not_save=1)
		pi.credit_to = "Creditors - _TC"
		pi.submit()

		pr = make_payment_request(
			dt="Purchase Invoice",
			dn=pi.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)

		# 100 USD -> 5000 INR
		self.assertEqual(pr.grand_total, 100)
		self.assertEqual(pr.outstanding_amount, 5000)
		self.assertEqual(pr.currency, "USD")
		self.assertEqual(pr.party_account_currency, "INR")
		self.assertEqual(pr.status, "Initiated")

		self.assertRaisesRegex(
			frappe.exceptions.ValidationError,
			re.compile(r"Payment Request is already created"),
			make_payment_request,
			dt="Purchase Invoice",
			dn=pi.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)

		# to make partial payment
		pe = pr.create_payment_entry(submit=False)
		pe.paid_amount = 2000
		pe.references[0].allocated_amount = 2000
		pe.submit()

		self.assertEqual(pe.references[0].payment_request, pr.name)

		pr.load_from_db()
		self.assertEqual(pr.status, "Partially Paid")
		self.assertEqual(pr.outstanding_amount, 3000)
		self.assertEqual(pr.grand_total, 100)

		# complete payment
		pe = pr.create_payment_entry()
		self.assertEqual(pe.paid_amount, 3000)  # paid amount set from pr's outstanding amount
		self.assertEqual(pe.references[0].allocated_amount, 3000)
		self.assertEqual(pe.references[0].outstanding_amount, 0)  # for Invoices it will zero
		self.assertEqual(pe.references[0].payment_request, pr.name)

		pr.load_from_db()
		self.assertEqual(pr.status, "Paid")
		self.assertEqual(pr.outstanding_amount, 0)
		self.assertEqual(pr.grand_total, 100)

		# creating a more payment Request must not allowed
		self.assertRaisesRegex(
			frappe.exceptions.ValidationError,
			re.compile(r"Payment Entry is already created"),
			make_payment_request,
			dt="Purchase Invoice",
			dn=pi.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)

	def test_single_payment_with_payment_term_for_same_currency(self):
		create_payment_terms_template()

		po = create_purchase_order(do_not_save=1, currency="INR", qty=1, rate=20000)
		po.payment_terms_template = "Test Receivable Template"  # 84.746 and 15.254
		po.save()
		po.submit()

		self.assertEqual(po.advance_payment_status, "Not Initiated")

		pr = make_payment_request(
			dt="Purchase Order",
			dn=po.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)

		self.assertEqual(pr.grand_total, 20000)
		self.assertEqual(pr.outstanding_amount, pr.grand_total)
		self.assertEqual(pr.party_account_currency, pr.currency)  # INR
		self.assertEqual(pr.status, "Initiated")

		po.load_from_db()
		self.assertEqual(po.advance_payment_status, "Initiated")

		pe = pr.create_payment_entry()

		self.assertEqual(len(pe.references), 2)
		self.assertEqual(pe.paid_amount, 20000)

		# check 1st payment term
		self.assertEqual(pe.references[0].allocated_amount, 16949.2)
		self.assertEqual(pe.references[0].payment_request, pr.name)

		# check 2nd payment term
		self.assertEqual(pe.references[1].allocated_amount, 3050.8)
		self.assertEqual(pe.references[1].payment_request, pr.name)

		po.load_from_db()
		self.assertEqual(po.advance_payment_status, "Fully Paid")

		pr.load_from_db()
		self.assertEqual(pr.status, "Paid")
		self.assertEqual(pr.outstanding_amount, 0)
		self.assertEqual(pr.grand_total, 20000)

	@ERPNextTestSuite.change_settings(
		"Accounts Settings", {"allow_multi_currency_invoices_against_single_party_account": 1}
	)
	def test_single_payment_with_payment_term_for_multi_currency(self):
		create_payment_terms_template()

		si = create_sales_invoice(
			do_not_save=1, currency="USD", debit_to="Debtors - _TC", qty=1, rate=200, conversion_rate=50
		)
		si.payment_terms_template = "Test Receivable Template"  # 84.746 and 15.254
		si.save()
		si.submit()

		pr = make_payment_request(
			dt="Sales Invoice",
			dn=si.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)

		# 200 USD -> 10000 INR
		self.assertEqual(pr.grand_total, 200)
		self.assertEqual(pr.outstanding_amount, 10000)
		self.assertEqual(pr.currency, "USD")
		self.assertEqual(pr.party_account_currency, "INR")
		self.assertEqual(pr.status, "Requested")

		pe = pr.create_payment_entry()
		self.assertEqual(len(pe.references), 2)
		self.assertEqual(pe.paid_amount, 10000)

		# check 1st payment term
		# convert it via dollar and conversion_rate
		self.assertEqual(pe.references[0].allocated_amount, 8474.5)  # multi currency conversion
		self.assertEqual(pe.references[0].payment_request, pr.name)

		# check 2nd payment term
		self.assertEqual(pe.references[1].allocated_amount, 1525.5)  # multi currency conversion
		self.assertEqual(pe.references[1].payment_request, pr.name)

		pr.load_from_db()
		self.assertEqual(pr.status, "Paid")
		self.assertEqual(pr.outstanding_amount, 0)
		self.assertEqual(pr.grand_total, 200)

	def test_payment_cancel_process(self):
		so = make_sales_order(currency="INR", qty=1, rate=1000)
		self.assertEqual(so.advance_payment_status, "Not Requested")

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			mute_email=1,
			submit_doc=1,
			return_doc=1,
		)

		self.assertEqual(pr.status, "Requested")
		self.assertEqual(pr.grand_total, 1000)
		self.assertEqual(pr.outstanding_amount, pr.grand_total)

		so.load_from_db()
		self.assertEqual(so.advance_payment_status, "Requested")

		pe = pr.create_payment_entry(submit=False)
		pe.paid_amount = 800
		pe.references[0].allocated_amount = 800
		pe.submit()

		self.assertEqual(pe.references[0].payment_request, pr.name)

		so.load_from_db()
		self.assertEqual(so.advance_payment_status, "Partially Paid")

		pr.load_from_db()
		self.assertEqual(pr.status, "Partially Paid")
		self.assertEqual(pr.outstanding_amount, 200)
		self.assertEqual(pr.grand_total, 1000)

		# cancelling PE
		pe.cancel()

		pr.load_from_db()
		self.assertEqual(pr.status, "Requested")
		self.assertEqual(pr.outstanding_amount, 1000)
		self.assertEqual(pr.grand_total, 1000)

		so.load_from_db()
		self.assertEqual(so.advance_payment_status, "Requested")

	def test_partial_paid_invoice_with_payment_request(self):
		si = create_sales_invoice(currency="INR", qty=1, rate=5000)
		si.save()
		si.submit()

		pe = get_payment_entry("Sales Invoice", si.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "PAYEE0002"
		pe.reference_date = frappe.utils.nowdate()
		pe.paid_amount = 2500
		pe.references[0].allocated_amount = 2500
		pe.save()
		pe.submit()

		si.load_from_db()
		pr = make_payment_request(dt="Sales Invoice", dn=si.name, mute_email=1)

		self.assertEqual(pr.grand_total, si.outstanding_amount)

	def test_partial_paid_invoice_with_more_payment_entry(self):
		pi = make_purchase_invoice(currency="INR", qty=1, rate=500)
		pi.submit()
		pi_1 = make_purchase_invoice(currency="INR", qty=1, rate=300)
		pi_1.submit()

		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1)
		pr.grand_total = 200
		pr.submit()
		pr.create_payment_entry()
		pr_1 = make_payment_request(
			dt="Purchase Invoice", dn=pi.name, mute_email=1, submit_doc=0, return_doc=1
		)
		pr_1.grand_total = 200
		pr_1.submit()
		pr_1.create_payment_entry()

		pe = get_payment_entry(dt="Purchase Invoice", dn=pi.name)
		pe.paid_amount = 200
		pe.references[0].reference_doctype = pi.doctype
		pe.references[0].reference_name = pi.name
		pe.references[0].grand_total = pi.grand_total
		pe.references[0].outstanding_amount = pi.outstanding_amount
		pe.references[0].allocated_amount = 100
		pe.append(
			"references",
			{
				"reference_doctype": pi_1.doctype,
				"reference_name": pi_1.name,
				"grand_total": pi_1.grand_total,
				"outstanding_amount": pi_1.outstanding_amount,
				"allocated_amount": 100,
			},
		)

		pr_2 = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1)
		pi.load_from_db()
		self.assertEqual(pr_2.grand_total, pi.outstanding_amount)

	def test_consider_journal_entry_and_return_invoice(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		si = create_sales_invoice(currency="INR", qty=5, rate=500)

		je = make_journal_entry("_Test Cash - _TC", "Debtors - _TC", 500, save=False)
		je.accounts[1].party_type = "Customer"
		je.accounts[1].party = si.customer
		je.accounts[1].reference_type = "Sales Invoice"
		je.accounts[1].reference_name = si.name
		je.accounts[1].credit_in_account_currency = 500
		je.submit()

		pe = get_payment_entry("Sales Invoice", si.name)
		pe.paid_amount = 500
		pe.references[0].allocated_amount = 500
		pe.save()
		pe.submit()

		cr_note = create_sales_invoice(qty=-1, rate=500, is_return=1, return_against=si.name, do_not_save=1)
		cr_note.update_outstanding_for_self = 0
		cr_note.save()
		cr_note.submit()

		si.load_from_db()
		pr = make_payment_request(dt="Sales Invoice", dn=si.name, mute_email=1)
		self.assertEqual(pr.grand_total, si.outstanding_amount)

	def test_partial_paid_invoice_with_submitted_payment_entry(self):
		pi = make_purchase_invoice(currency="INR", qty=1, rate=5000)
		pi.save()
		pi.submit()

		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "PURINV0001"
		pe.reference_date = frappe.utils.nowdate()
		pe.paid_amount = 2500
		pe.references[0].allocated_amount = 2500
		pe.save()
		pe.submit()
		pe.cancel()

		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "PURINV0002"
		pe.reference_date = frappe.utils.nowdate()
		pe.paid_amount = 2500
		pe.references[0].allocated_amount = 2500
		pe.save()
		pe.submit()

		pi.load_from_db()
		pr = make_payment_request(dt="Purchase Invoice", dn=pi.name, mute_email=1)
		self.assertEqual(pr.grand_total, pi.outstanding_amount)

	def test_payment_request_on_unreconcile(self):
		pi = make_purchase_invoice(currency="INR", qty=1, rate=500)
		pi.submit()

		pr = make_payment_request(
			dt=pi.doctype,
			dn=pi.name,
			mute_email=1,
			submit_doc=True,
			return_doc=True,
		)
		self.assertEqual(pr.grand_total, pi.outstanding_amount)

		pe = pr.create_payment_entry()
		unreconcile = frappe.get_doc(
			{
				"doctype": "Unreconcile Payment",
				"company": pe.company,
				"voucher_type": pe.doctype,
				"voucher_no": pe.name,
			}
		)
		unreconcile.add_references()
		unreconcile.submit()

		pi.load_from_db()
		pr.load_from_db()

		self.assertEqual(pr.grand_total, pi.outstanding_amount)

	def test_payment_request_grand_total_from_selected_schedules(self):
		po = create_purchase_order(do_not_save=1, currency="INR", qty=1, rate=100)
		po.payment_schedule = []

		po.append("payment_schedule", {"due_date": nowdate(), "payment_amount": 30})
		po.append("payment_schedule", {"due_date": add_days(nowdate(), 1), "payment_amount": 30})
		po.append("payment_schedule", {"due_date": add_days(nowdate(), 2), "payment_amount": 40})

		po.save()
		po.submit()

		schedules = json.dumps(
			[
				{
					"payment_term": row.payment_term,
					"name": row.name,
					"due_date": row.due_date,
					"payment_amount": row.payment_amount,
					"description": row.description,
				}
				for row in [po.payment_schedule[0], po.payment_schedule[2]]
			]
		)
		pr = make_payment_request(
			dt="Purchase Order",
			dn=po.name,
			mute_email=1,
			submit_doc=False,
			return_doc=True,
			schedules=schedules,
		)

		pr.submit()

		self.assertEqual(pr.grand_total, 70)
		self.assertEqual(len(pr.payment_reference), 2)

	def test_draft_pr_reuse_merges_payment_references(self):
		from frappe.utils import add_days, nowdate

		po = create_purchase_order(do_not_save=1, currency="INR", qty=1, rate=100)
		po.payment_schedule = []
		po.append("payment_schedule", {"due_date": nowdate(), "payment_amount": 50})
		po.append("payment_schedule", {"due_date": add_days(nowdate(), 1), "payment_amount": 50})
		po.save()
		po.submit()
		schedules = json.dumps(
			[
				{
					"payment_term": row.payment_term,
					"name": row.name,
					"due_date": row.due_date,
					"payment_amount": row.payment_amount,
					"description": row.description,
				}
				for row in [po.payment_schedule[0]]
			]
		)
		pr = make_payment_request(
			dt="Purchase Order",
			dn=po.name,
			mute_email=1,
			submit_doc=False,
			return_doc=True,
			schedules=schedules,
		)

		pr.save()
		schedules = json.dumps(
			[
				{
					"payment_term": row.payment_term,
					"name": row.name,
					"due_date": row.due_date,
					"payment_amount": row.payment_amount,
					"description": row.description,
				}
				for row in [po.payment_schedule[1]]
			]
		)
		# call make_payment_request again → reuse draft
		pr_reused = make_payment_request(
			dt="Purchase Order",
			dn=po.name,
			mute_email=1,
			submit_doc=False,
			return_doc=True,
			schedules=schedules,
		)

		self.assertEqual(pr.name, pr_reused.name)
		self.assertEqual(pr_reused.grand_total, 100)
		self.assertEqual(len(pr_reused.payment_reference), 2)

	def test_schedule_pr_not_allowed_if_payment_entry_exists(self):
		po = create_purchase_order(do_not_save=1, currency="INR", qty=1, rate=100)
		po.payment_schedule = []
		row = po.append("payment_schedule", {"due_date": nowdate(), "payment_amount": 100})
		po.save()
		po.submit()

		# create PE first
		pr = make_payment_request(dt="Purchase Order", dn=po.name, mute_email=1, submit_doc=1, return_doc=1)
		pr.create_payment_entry()

		schedules = json.dumps(
			[
				{
					"name": row.name,
					"payment_term": row.payment_term,
					"due_date": row.due_date,
					"payment_amount": row.payment_amount,
					"description": row.description,
				}
			]
		)

		with self.assertRaises(frappe.ValidationError):
			make_payment_request(
				dt="Purchase Order",
				dn=po.name,
				mute_email=1,
				submit_doc=False,
				return_doc=True,
				schedules=schedules,
			)


class TestPaymentRequestV2Gateway(ERPNextTestSuite):
	"""Tests for PaymentController v2 gateway integration."""

	def setUp(self):
		"""Set up payment gateway fixtures for flow tests."""
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

	def _mock_payments_modules(self, is_v2_gateway_return_value):
		"""Helper to mock both payments and payments.utils modules.

		Python requires the parent module to be in sys.modules before importing
		a child module. This helper ensures both are mocked properly.
		"""
		mock_payments = MagicMock()
		mock_utils = MagicMock()
		mock_utils.is_v2_gateway = MagicMock(return_value=is_v2_gateway_return_value)
		mock_payments.utils = mock_utils
		return {"payments": mock_payments, "payments.utils": mock_utils}, mock_utils

	def test_is_v2_gateway_returns_false_for_none(self):
		"""_is_v2_gateway returns False for None input."""
		from erpnext.accounts.doctype.payment_request.payment_request import _is_v2_gateway

		# Mock returns True, but is_v2_gateway(None) in payments.utils returns False
		modules, mock_utils = self._mock_payments_modules(False)

		with patch.dict(sys.modules, modules):
			result = _is_v2_gateway(None)
			self.assertFalse(result)
			mock_utils.is_v2_gateway.assert_called_once_with(None)

	def test_is_v2_gateway_returns_false_for_empty_string(self):
		"""_is_v2_gateway returns False for empty string input."""
		from erpnext.accounts.doctype.payment_request.payment_request import _is_v2_gateway

		modules, mock_utils = self._mock_payments_modules(False)

		with patch.dict(sys.modules, modules):
			result = _is_v2_gateway("")
			self.assertFalse(result)
			mock_utils.is_v2_gateway.assert_called_once_with("")

	def test_is_v2_gateway_returns_false_for_nonexistent_gateway(self):
		"""_is_v2_gateway returns False for nonexistent gateway."""
		from erpnext.accounts.doctype.payment_request.payment_request import _is_v2_gateway

		modules, mock_utils = self._mock_payments_modules(False)

		with patch.dict(sys.modules, modules):
			result = _is_v2_gateway("NonExistentGateway12345")
			self.assertFalse(result)
			mock_utils.is_v2_gateway.assert_called_once_with("NonExistentGateway12345")

	def test_is_v2_gateway_delegates_to_payments_util(self):
		"""_is_v2_gateway delegates to payments.utils.is_v2_gateway."""
		from erpnext.accounts.doctype.payment_request.payment_request import _is_v2_gateway

		modules, mock_utils = self._mock_payments_modules(True)

		with patch.dict(sys.modules, modules):
			result = _is_v2_gateway("_Test Gateway")
			self.assertTrue(result)
			mock_utils.is_v2_gateway.assert_called_once_with("_Test Gateway")

	def test_is_v2_gateway_returns_false_when_payments_util_returns_false(self):
		"""_is_v2_gateway returns False when payments.utils.is_v2_gateway returns False."""
		from erpnext.accounts.doctype.payment_request.payment_request import _is_v2_gateway

		modules, _ = self._mock_payments_modules(False)

		with patch.dict(sys.modules, modules):
			result = _is_v2_gateway("_Test Gateway")
			self.assertFalse(result)

	def test_is_v2_gateway_catches_unexpected_exceptions(self):
		"""_is_v2_gateway catches unexpected exceptions and returns False."""
		from erpnext.accounts.doctype.payment_request.payment_request import _is_v2_gateway

		mock_payments = MagicMock()
		mock_utils = MagicMock()
		mock_utils.is_v2_gateway = MagicMock(side_effect=RuntimeError("Unexpected error"))
		mock_payments.utils = mock_utils
		modules = {"payments": mock_payments, "payments.utils": mock_utils}

		with patch.dict(sys.modules, modules):
			# Should not raise, should return False
			result = _is_v2_gateway("_Test Gateway")
			self.assertFalse(result)

	def test_get_tx_data_returns_required_fields(self):
		"""get_tx_data returns all fields required by TxData."""
		so = make_sales_order(currency="INR")

		# Use make_payment_request to properly populate all mandatory fields
		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			recipient_id="test@example.com",
			mute_email=True,
			submit_doc=False,
			return_doc=True,
		)

		tx_data = pr.get_tx_data()

		# Verify all required TxData fields are present
		self.assertIn("amount", tx_data)
		self.assertIn("currency", tx_data)
		self.assertIn("reference_doctype", tx_data)
		self.assertIn("reference_docname", tx_data)
		self.assertIn("payer_contact", tx_data)
		self.assertIn("payer_address", tx_data)
		self.assertIn("loyalty_points", tx_data)
		self.assertIn("discount_amount", tx_data)

		# Verify values - amount should come from get_request_amount()
		self.assertEqual(tx_data.amount, pr.get_request_amount())
		self.assertEqual(tx_data.currency, "INR")
		self.assertEqual(tx_data.reference_doctype, "Payment Request")
		self.assertEqual(tx_data.reference_docname, pr.name)

	def test_get_tx_data_uses_request_amount_not_grand_total(self):
		"""get_tx_data should use get_request_amount() to support partial payments."""
		so = make_sales_order(currency="INR", qty=1, rate=1000)

		# Use make_payment_request to properly populate all mandatory fields
		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			recipient_id="test@example.com",
			mute_email=True,
			submit_doc=False,
			return_doc=True,
		)

		# Mock get_request_amount to return a partial amount
		with patch.object(pr, "get_request_amount", return_value=500.0):
			tx_data = pr.get_tx_data()
			# Amount should be the partial request amount, not grand_total
			self.assertEqual(tx_data.amount, 500.0)
			self.assertNotEqual(tx_data.amount, pr.grand_total)

	def test_get_party_contact_and_address_returns_whitelisted_fields_only(self):
		"""_get_party_contact_and_address should only return payment-relevant fields."""
		# Create a customer with contact and address to ensure assertions run
		customer = frappe.get_doc("Customer", "_Test Customer")

		# Create or get test contact
		contact_name = f"_Test Contact for {customer.name}"
		if not frappe.db.exists("Contact", contact_name):
			test_contact = frappe.get_doc(
				{
					"doctype": "Contact",
					"first_name": "Test",
					"last_name": "Contact",
					"email_id": "test.contact@example.com",
					"phone": "+1234567890",
				}
			)
			test_contact.insert(ignore_permissions=True)
			contact_name = test_contact.name

		# Create or get test address
		address_name = f"_Test Address for {customer.name}"
		if not frappe.db.exists("Address", {"address_title": address_name}):
			test_address = frappe.get_doc(
				{
					"doctype": "Address",
					"address_title": address_name,
					"address_type": "Billing",
					"address_line1": "123 Test Street",
					"city": "Test City",
					"country": "United States",
				}
			)
			test_address.insert(ignore_permissions=True)
			address_name = test_address.name

		# Link contact and address to customer
		customer.customer_primary_contact = contact_name
		customer.customer_primary_address = address_name
		customer.save(ignore_permissions=True)

		pr = frappe.new_doc("Payment Request")
		pr.party_type = "Customer"
		pr.party = customer.name

		contact, address = pr._get_party_contact_and_address()

		# Assertions should always run now that we've ensured contact/address exist
		self.assertTrue(contact, "Contact should be returned")
		allowed_contact_fields = {"first_name", "last_name", "email_id", "email", "phone"}
		self.assertTrue(set(contact.keys()).issubset(allowed_contact_fields))
		# Verify internal/sensitive fields are NOT present
		self.assertNotIn("owner", contact)
		self.assertNotIn("creation", contact)
		self.assertNotIn("modified", contact)
		self.assertNotIn("doctype", contact)

		self.assertTrue(address, "Address should be returned")
		allowed_address_fields = {"address_line1", "address_line2", "city", "state", "pincode", "country"}
		self.assertTrue(set(address.keys()).issubset(allowed_address_fields))
		# Verify internal/sensitive fields are NOT present
		self.assertNotIn("owner", address)
		self.assertNotIn("creation", address)
		self.assertNotIn("modified", address)
		self.assertNotIn("doctype", address)

	def test_get_party_contact_and_address_handles_missing_party(self):
		"""_get_party_contact_and_address returns empty dicts for missing party."""
		pr = frappe.new_doc("Payment Request")
		pr.party_type = None
		pr.party = None

		contact, address = pr._get_party_contact_and_address()

		self.assertEqual(contact, {})
		self.assertEqual(address, {})

	def test_get_party_contact_and_address_handles_deleted_party(self):
		"""_get_party_contact_and_address handles deleted party gracefully."""
		pr = frappe.new_doc("Payment Request")
		pr.party_type = "Customer"
		pr.party = "NonExistentCustomer12345"

		contact, address = pr._get_party_contact_and_address()

		self.assertEqual(contact, {})
		self.assertEqual(address, {})

	def test_v2_gateway_uses_process_v2_gateway(self):
		"""v2 gateways should use _process_v2_gateway flow, not legacy flow."""
		so = make_sales_order(currency="INR")

		with patch(
			"erpnext.accounts.doctype.payment_request.payment_request._is_v2_gateway",
			return_value=True,
		):
			with patch(
				"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest._process_v2_gateway"
			) as mock_process_v2:
				with patch(
					"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.set_payment_request_url"
				) as mock_set_url:
					with patch(
						"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.send_email"
					):
						make_payment_request(
							dt="Sales Order",
							dn=so.name,
							recipient_id="test@example.com",
							payment_gateway_account="_Test Gateway - INR - _TC",
							mute_email=True,
							submit_doc=True,
							return_doc=True,
						)

						# v2 flow should be called
						mock_process_v2.assert_called_once()
						# Legacy flow should NOT be called
						mock_set_url.assert_not_called()

	def test_v1_gateway_uses_legacy_flow(self):
		"""v1 gateways should use set_payment_request_url flow, not v2 flow."""
		so = make_sales_order(currency="INR")

		with patch(
			"erpnext.accounts.doctype.payment_request.payment_request._is_v2_gateway",
			return_value=False,
		):
			with patch(
				"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.set_payment_request_url"
			) as mock_set_url:
				with patch(
					"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest._process_v2_gateway"
				) as mock_process_v2:
					with patch(
						"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.get_payment_url",
						return_value=PAYMENT_URL,
					):
						with patch(
							"erpnext.accounts.doctype.payment_request.payment_request._get_payment_gateway_controller"
						):
							with patch(
								"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.send_email"
							):
								make_payment_request(
									dt="Sales Order",
									dn=so.name,
									recipient_id="test@example.com",
									payment_gateway_account="_Test Gateway - INR - _TC",
									mute_email=True,
									submit_doc=True,
									return_doc=True,
								)

								# Legacy flow should be called
								mock_set_url.assert_called_once()
								# v2 flow should NOT be called
								mock_process_v2.assert_not_called()

	# ============================================================================
	# Codecov Gap Tests
	# ============================================================================

	def test_is_v2_gateway_returns_false_when_payments_not_installed(self):
		"""_is_v2_gateway returns False when payments app raises ValidationError."""
		from erpnext.accounts.doctype.payment_request.payment_request import _is_v2_gateway

		# Simulate payments app not installed (ValidationError from import guard)
		with patch(
			"erpnext.accounts.doctype.payment_request.payment_request.payment_app_import_guard",
			side_effect=frappe.ValidationError("Payments app not installed"),
		):
			result = _is_v2_gateway("_Test Gateway")
			self.assertFalse(result)

	def test_process_v2_gateway_handles_initiate_failure(self):
		"""_process_v2_gateway shows user-friendly error on initiate failure."""
		so = make_sales_order(currency="INR")

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			recipient_id="test@example.com",
			payment_gateway_account="_Test Gateway - INR - _TC",
			mute_email=True,
			submit_doc=False,
			return_doc=True,
		)
		# Ensure payment_gateway is set (make_payment_request may not populate it)
		pr.payment_gateway = "_Test Gateway"

		# Mock PaymentController to raise an exception
		mock_controller = MagicMock()
		mock_controller.initiate = MagicMock(side_effect=Exception("Gateway connection failed"))

		with patch("erpnext.accounts.doctype.payment_request.payment_request.payment_app_import_guard"):
			with patch.dict(
				sys.modules,
				{
					"payments": MagicMock(),
					"payments.controllers": MagicMock(PaymentController=mock_controller),
				},
			):
				with self.assertRaises(frappe.ValidationError) as context:
					pr._process_v2_gateway()

				self.assertIn("Failed to initiate payment", str(context.exception))
				self.assertIn("_Test Gateway", str(context.exception))

	def test_process_v2_gateway_handles_none_psl(self):
		"""_process_v2_gateway throws when PaymentController returns None PSL."""
		so = make_sales_order(currency="INR")

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			recipient_id="test@example.com",
			payment_gateway_account="_Test Gateway - INR - _TC",
			mute_email=True,
			submit_doc=False,
			return_doc=True,
		)

		# Mock PaymentController.initiate to return (controller, None)
		mock_controller_class = MagicMock()
		mock_controller_class.initiate = MagicMock(return_value=(MagicMock(), None))

		with patch("erpnext.accounts.doctype.payment_request.payment_request.payment_app_import_guard"):
			with patch.dict(
				sys.modules,
				{
					"payments": MagicMock(),
					"payments.controllers": MagicMock(PaymentController=mock_controller_class),
				},
			):
				with self.assertRaises(frappe.ValidationError) as context:
					pr._process_v2_gateway()

				self.assertIn("failed to create a payment session", str(context.exception))

	def test_process_v2_gateway_sets_payment_session_log(self):
		"""_process_v2_gateway sets payment_session_log field when it exists."""
		so = make_sales_order(currency="INR")

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			recipient_id="test@example.com",
			payment_gateway_account="_Test Gateway - INR - _TC",
			mute_email=True,
			submit_doc=False,
			return_doc=True,
		)

		# Add payment_session_log attribute to simulate custom field
		pr.payment_session_log = None

		mock_controller_class = MagicMock()
		mock_controller_class.initiate = MagicMock(return_value=(MagicMock(), "PSL-00001"))
		mock_controller_class.get_payment_url = MagicMock(return_value="https://pay.example.com/xyz")

		with patch("erpnext.accounts.doctype.payment_request.payment_request.payment_app_import_guard"):
			with patch.dict(
				sys.modules,
				{
					"payments": MagicMock(),
					"payments.controllers": MagicMock(PaymentController=mock_controller_class),
				},
			):
				pr._process_v2_gateway()

				self.assertEqual(pr.payment_session_log, "PSL-00001")
				self.assertEqual(pr.payment_url, "https://pay.example.com/xyz")

	def test_get_party_contact_and_address_supplier(self):
		"""_get_party_contact_and_address works for Supplier party type."""
		# Get or create test supplier
		supplier_name = "_Test Supplier"
		if not frappe.db.exists("Supplier", supplier_name):
			frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": supplier_name,
					"supplier_group": "All Supplier Groups",
				}
			).insert(ignore_permissions=True)

		supplier = frappe.get_doc("Supplier", supplier_name)
		original_contact = supplier.supplier_primary_contact
		original_address = supplier.supplier_primary_address

		# Create test contact for supplier (always recreate to ensure known state)
		contact_name = "_Test PR Supplier Contact"
		if frappe.db.exists("Contact", contact_name):
			frappe.delete_doc("Contact", contact_name, force=True)

		test_contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "SupplierTest",
				"last_name": "Contact",
				# Email and phone are set via child tables in Frappe
				"email_ids": [{"email_id": "supplier.test@example.com", "is_primary": 1}],
				"phone_nos": [{"phone": "+9876543210", "is_primary_phone": 1}],
			}
		)
		test_contact.insert(ignore_permissions=True)

		# Create test address for supplier (always recreate to ensure known state)
		address_title = "_Test PR Supplier Address"
		existing_address = frappe.db.get_value("Address", {"address_title": address_title}, "name")
		if existing_address:
			frappe.delete_doc("Address", existing_address, force=True)

		test_address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": address_title,
				"address_type": "Billing",
				"address_line1": "456 Supplier Street",
				"city": "Supplier City",
				"country": "United States",
			}
		)
		test_address.insert(ignore_permissions=True)

		try:
			# Link contact and address to supplier
			supplier.db_set("supplier_primary_contact", test_contact.name, update_modified=False)
			supplier.db_set("supplier_primary_address", test_address.name, update_modified=False)

			pr = frappe.new_doc("Payment Request")
			pr.party_type = "Supplier"
			pr.party = supplier.name

			contact, address = pr._get_party_contact_and_address()

			self.assertTrue(contact, "Contact should be returned for Supplier")
			self.assertEqual(contact.get("first_name"), "SupplierTest")
			self.assertEqual(contact.get("email_id"), "supplier.test@example.com")

			self.assertTrue(address, "Address should be returned for Supplier")
			self.assertEqual(address.get("address_line1"), "456 Supplier Street")
			self.assertEqual(address.get("city"), "Supplier City")
		finally:
			# Restore original values
			supplier.db_set("supplier_primary_contact", original_contact, update_modified=False)
			supplier.db_set("supplier_primary_address", original_address, update_modified=False)
			frappe.delete_doc("Contact", test_contact.name, force=True)
			frappe.delete_doc("Address", test_address.name, force=True)

	def test_get_party_contact_and_address_unsupported_party_type(self):
		"""_get_party_contact_and_address returns empty dicts for unsupported party types."""
		pr = frappe.new_doc("Payment Request")
		pr.party_type = "Lead"  # Not in field_map (only Customer/Supplier supported)
		pr.party = "some-lead-name"

		# Mock the party lookup to avoid DoesNotExistError for Lead
		with patch.object(frappe, "get_doc", return_value=MagicMock()):
			contact, address = pr._get_party_contact_and_address()

		self.assertEqual(contact, {})
		self.assertEqual(address, {})

	def test_get_party_contact_and_address_deleted_contact(self):
		"""_get_party_contact_and_address handles deleted contact gracefully."""
		customer = frappe.get_doc("Customer", "_Test Customer")

		# Set a nonexistent contact name
		original_contact = customer.customer_primary_contact
		customer.db_set("customer_primary_contact", "NonExistentContact12345", update_modified=False)

		try:
			pr = frappe.new_doc("Payment Request")
			pr.party_type = "Customer"
			pr.party = customer.name

			contact, _address = pr._get_party_contact_and_address()

			# Should return empty dict for contact, not raise
			self.assertEqual(contact, {})
		finally:
			# Restore original contact
			customer.db_set("customer_primary_contact", original_contact, update_modified=False)

	def test_get_party_contact_and_address_deleted_address(self):
		"""_get_party_contact_and_address handles deleted address gracefully."""
		customer = frappe.get_doc("Customer", "_Test Customer")

		# Set a nonexistent address name
		original_address = customer.customer_primary_address
		customer.db_set("customer_primary_address", "NonExistentAddress12345", update_modified=False)

		try:
			pr = frappe.new_doc("Payment Request")
			pr.party_type = "Customer"
			pr.party = customer.name

			_contact, address = pr._get_party_contact_and_address()

			# Should return empty dict for address, not raise
			self.assertEqual(address, {})
		finally:
			# Restore original address
			customer.db_set("customer_primary_address", original_address, update_modified=False)

	# ============================================================================
	# before_submit Flow Gap Tests
	# ============================================================================

	def test_v2_gateway_sends_email_when_not_muted(self):
		"""v2 gateways should send email when mute_email is False."""
		so = make_sales_order(currency="INR")

		with patch(
			"erpnext.accounts.doctype.payment_request.payment_request._is_v2_gateway",
			return_value=True,
		):
			with patch(
				"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest._process_v2_gateway"
			):
				with patch(
					"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.send_email"
				) as mock_send_email:
					with patch(
						"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.make_communication_entry"
					) as mock_make_comm:
						make_payment_request(
							dt="Sales Order",
							dn=so.name,
							recipient_id="test@example.com",
							payment_gateway_account="_Test Gateway - INR - _TC",
							mute_email=False,  # Email should be sent
							submit_doc=True,
							return_doc=True,
						)

						mock_send_email.assert_called_once()
						mock_make_comm.assert_called_once()

	def test_v1_phone_payment_skips_email(self):
		"""Phone payment channel should skip email sending entirely."""
		so = make_sales_order(currency="INR")

		with patch(
			"erpnext.accounts.doctype.payment_request.payment_request._is_v2_gateway",
			return_value=False,
		):
			with patch(
				"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.request_phone_payment"
			) as mock_phone:
				with patch(
					"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.send_email"
				) as mock_send_email:
					with patch(
						"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.make_communication_entry"
					) as mock_make_comm:
						pr = make_payment_request(
							dt="Sales Order",
							dn=so.name,
							recipient_id="test@example.com",
							payment_gateway_account="_Test Gateway - INR - _TC",
							mute_email=False,
							submit_doc=False,
							return_doc=True,
						)
						pr.payment_channel = "Phone"
						pr.submit()

						# Phone payment should be called
						mock_phone.assert_called_once()
						# Email should NOT be sent for phone payments
						mock_send_email.assert_not_called()
						mock_make_comm.assert_not_called()

	def test_no_payment_gateway_skips_payment_processing(self):
		"""Payment request without gateway should skip all payment processing."""
		so = make_sales_order(currency="INR")

		with patch("erpnext.accounts.doctype.payment_request.payment_request._is_v2_gateway") as mock_is_v2:
			with patch(
				"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest._process_v2_gateway"
			) as mock_v2:
				with patch(
					"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.set_payment_request_url"
				) as mock_v1:
					pr = make_payment_request(
						dt="Sales Order",
						dn=so.name,
						recipient_id="test@example.com",
						mute_email=True,
						submit_doc=False,
						return_doc=True,
					)
					# Clear the payment gateway
					pr.payment_gateway = None
					pr.payment_gateway_account = None
					pr.submit()

					# Neither v1 nor v2 flow should be called
					mock_is_v2.assert_not_called()
					mock_v2.assert_not_called()
					mock_v1.assert_not_called()

	def test_outward_payment_request_skips_gateway_processing(self):
		"""Outward payment requests should not trigger v1/v2 gateway flows."""
		po = create_purchase_order()

		with patch("erpnext.accounts.doctype.payment_request.payment_request._is_v2_gateway") as mock_is_v2:
			with patch(
				"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest._process_v2_gateway"
			) as mock_v2:
				with patch(
					"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.set_payment_request_url"
				) as mock_v1:
					pr = make_payment_request(
						dt="Purchase Order",
						dn=po.name,
						recipient_id="test@example.com",
						mute_email=True,
						submit_doc=True,
						return_doc=True,
					)

					# Outward requests should not call gateway processing
					mock_is_v2.assert_not_called()
					mock_v2.assert_not_called()
					mock_v1.assert_not_called()
					self.assertEqual(pr.payment_request_type, "Outward")
					self.assertEqual(pr.status, "Initiated")

	def test_flags_mute_email_suppresses_communication(self):
		"""flags.mute_email should suppress email even when mute_email field is False."""
		so = make_sales_order(currency="INR")

		with patch(
			"erpnext.accounts.doctype.payment_request.payment_request._is_v2_gateway",
			return_value=True,
		):
			with patch(
				"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest._process_v2_gateway"
			):
				with patch(
					"erpnext.accounts.doctype.payment_request.payment_request.PaymentRequest.send_email"
				) as mock_send_email:
					pr = make_payment_request(
						dt="Sales Order",
						dn=so.name,
						recipient_id="test@example.com",
						payment_gateway_account="_Test Gateway - INR - _TC",
						mute_email=False,  # Field says don't mute
						submit_doc=False,
						return_doc=True,
					)
					pr.flags.mute_email = True  # But flag says mute
					pr.submit()

					# Email should NOT be sent because of flags.mute_email
					mock_send_email.assert_not_called()

	# ============================================================================
	# _get_party_contact_and_address Edge Case Tests
	# ============================================================================

	def test_contact_uses_mobile_no_fallback(self):
		"""Contact with mobile_no but no phone should use mobile_no as fallback."""
		customer = frappe.get_doc("Customer", "_Test Customer")

		# Create contact with only mobile_no (via phone_nos child table)
		contact_name = "_Test Contact Mobile Only"
		if frappe.db.exists("Contact", contact_name):
			frappe.delete_doc("Contact", contact_name, force=True)

		test_contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Mobile",
				"last_name": "Only",
				"email_id": "mobile.only@example.com",
				# Phone numbers in Frappe are set via the phone_nos child table
				# is_primary_mobile_no sets the mobile_no field, is_primary_phone sets phone
				"phone_nos": [{"phone": "+1999888777", "is_primary_mobile_no": 1}],
			}
		)
		test_contact.insert(ignore_permissions=True)

		original_contact = customer.customer_primary_contact
		customer.db_set("customer_primary_contact", test_contact.name, update_modified=False)

		try:
			pr = frappe.new_doc("Payment Request")
			pr.party_type = "Customer"
			pr.party = customer.name

			contact, _ = pr._get_party_contact_and_address()

			# Should fall back to mobile_no since phone is empty
			self.assertEqual(contact.get("phone"), "+1999888777")
		finally:
			customer.db_set("customer_primary_contact", original_contact, update_modified=False)
			frappe.delete_doc("Contact", test_contact.name, force=True)

	def test_contact_with_no_email_returns_empty_string(self):
		"""Contact without email_id should return empty string, not None."""
		customer = frappe.get_doc("Customer", "_Test Customer")

		# Create contact without email
		contact_name = "_Test Contact No Email"
		if frappe.db.exists("Contact", contact_name):
			frappe.delete_doc("Contact", contact_name, force=True)

		test_contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "No",
				"last_name": "Email",
				"email_id": "",  # No email
				"phone": "+1234567890",
			}
		)
		test_contact.insert(ignore_permissions=True)

		original_contact = customer.customer_primary_contact
		customer.db_set("customer_primary_contact", test_contact.name, update_modified=False)

		try:
			pr = frappe.new_doc("Payment Request")
			pr.party_type = "Customer"
			pr.party = customer.name

			contact, _ = pr._get_party_contact_and_address()

			# Should be empty string, not None
			self.assertEqual(contact.get("email_id"), "")
			self.assertEqual(contact.get("email"), "")
			self.assertIsNotNone(contact.get("email_id"))
		finally:
			customer.db_set("customer_primary_contact", original_contact, update_modified=False)
			frappe.delete_doc("Contact", test_contact.name, force=True)

	def test_address_with_missing_optional_fields(self):
		"""Address missing optional fields should return empty strings."""
		customer = frappe.get_doc("Customer", "_Test Customer")

		# Create minimal address
		address_title = "_Test Minimal Address"
		existing = frappe.db.get_value("Address", {"address_title": address_title}, "name")
		if existing:
			frappe.delete_doc("Address", existing, force=True)

		test_address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": address_title,
				"address_type": "Billing",
				"address_line1": "123 Main St",
				# No address_line2, state, pincode
				"city": "Test City",
				"country": "United States",
			}
		)
		test_address.insert(ignore_permissions=True)

		original_address = customer.customer_primary_address
		customer.db_set("customer_primary_address", test_address.name, update_modified=False)

		try:
			pr = frappe.new_doc("Payment Request")
			pr.party_type = "Customer"
			pr.party = customer.name

			_, address = pr._get_party_contact_and_address()

			# Optional fields should be empty strings, not None
			self.assertEqual(address.get("address_line2"), "")
			self.assertEqual(address.get("state"), "")
			self.assertEqual(address.get("pincode"), "")
			# Required fields should have values
			self.assertEqual(address.get("address_line1"), "123 Main St")
			self.assertEqual(address.get("city"), "Test City")
		finally:
			customer.db_set("customer_primary_address", original_address, update_modified=False)
			frappe.delete_doc("Address", test_address.name, force=True)

	def test_customer_without_primary_contact(self):
		"""Customer without primary_contact set should return empty contact dict."""
		customer = frappe.get_doc("Customer", "_Test Customer")

		original_contact = customer.customer_primary_contact
		customer.db_set("customer_primary_contact", None, update_modified=False)

		try:
			pr = frappe.new_doc("Payment Request")
			pr.party_type = "Customer"
			pr.party = customer.name

			contact, _ = pr._get_party_contact_and_address()

			self.assertEqual(contact, {})
		finally:
			customer.db_set("customer_primary_contact", original_contact, update_modified=False)

	def test_customer_without_primary_address(self):
		"""Customer without primary_address set should return empty address dict."""
		customer = frappe.get_doc("Customer", "_Test Customer")

		original_address = customer.customer_primary_address
		customer.db_set("customer_primary_address", None, update_modified=False)

		try:
			pr = frappe.new_doc("Payment Request")
			pr.party_type = "Customer"
			pr.party = customer.name

			_, address = pr._get_party_contact_and_address()

			self.assertEqual(address, {})
		finally:
			customer.db_set("customer_primary_address", original_address, update_modified=False)

	# ============================================================================
	# get_tx_data Edge Case Tests
	# ============================================================================

	def test_get_tx_data_multi_currency(self):
		"""get_tx_data handles multi-currency payment requests correctly."""
		# Create USD sales order
		so = make_sales_order(currency="USD", qty=1, rate=100)

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			recipient_id="test@example.com",
			payment_gateway_account="_Test Gateway - USD - _TC",
			mute_email=True,
			submit_doc=False,
			return_doc=True,
		)

		tx_data = pr.get_tx_data()

		self.assertEqual(tx_data.currency, "USD")
		self.assertGreater(tx_data.amount, 0)

	def test_get_tx_data_without_party(self):
		"""get_tx_data returns empty contact/address when party is not set."""
		so = make_sales_order(currency="INR")

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			recipient_id="test@example.com",
			mute_email=True,
			submit_doc=False,
			return_doc=True,
		)
		# Clear party info
		pr.party_type = None
		pr.party = None

		tx_data = pr.get_tx_data()

		self.assertEqual(tx_data.payer_contact, {})
		self.assertEqual(tx_data.payer_address, {})

	def test_get_tx_data_loyalty_and_discount_are_none(self):
		"""get_tx_data sets loyalty_points and discount_amount to None."""
		so = make_sales_order(currency="INR")

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			recipient_id="test@example.com",
			mute_email=True,
			submit_doc=False,
			return_doc=True,
		)

		tx_data = pr.get_tx_data()

		# These are explicitly set to None as per current implementation
		self.assertIsNone(tx_data.loyalty_points)
		self.assertIsNone(tx_data.discount_amount)

	# ============================================================================
	# _process_v2_gateway Success Path Tests
	# ============================================================================

	def test_process_v2_gateway_sets_payment_url(self):
		"""_process_v2_gateway sets payment_url from PaymentController."""
		so = make_sales_order(currency="INR")

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			recipient_id="test@example.com",
			payment_gateway_account="_Test Gateway - INR - _TC",
			mute_email=True,
			submit_doc=False,
			return_doc=True,
		)

		expected_url = "https://gateway.example.com/pay/session123"
		mock_controller_class = MagicMock()
		mock_controller_class.initiate = MagicMock(return_value=(MagicMock(), "PSL-00001"))
		mock_controller_class.get_payment_url = MagicMock(return_value=expected_url)

		with patch("erpnext.accounts.doctype.payment_request.payment_request.payment_app_import_guard"):
			with patch.dict(
				sys.modules,
				{
					"payments": MagicMock(),
					"payments.controllers": MagicMock(PaymentController=mock_controller_class),
				},
			):
				pr._process_v2_gateway()

				self.assertEqual(pr.payment_url, expected_url)
				mock_controller_class.get_payment_url.assert_called_once_with("PSL-00001")

	def test_process_v2_gateway_logs_error_on_failure(self):
		"""_process_v2_gateway logs error with frappe.log_error on initiate failure."""
		so = make_sales_order(currency="INR")

		pr = make_payment_request(
			dt="Sales Order",
			dn=so.name,
			recipient_id="test@example.com",
			payment_gateway_account="_Test Gateway - INR - _TC",
			mute_email=True,
			submit_doc=False,
			return_doc=True,
		)
		# Ensure payment_gateway is set (make_payment_request may not populate it)
		pr.payment_gateway = "_Test Gateway"

		mock_controller_class = MagicMock()
		mock_controller_class.initiate = MagicMock(side_effect=Exception("API timeout"))

		with patch("erpnext.accounts.doctype.payment_request.payment_request.payment_app_import_guard"):
			with patch.dict(
				sys.modules,
				{
					"payments": MagicMock(),
					"payments.controllers": MagicMock(PaymentController=mock_controller_class),
				},
			):
				with patch("frappe.log_error") as mock_log_error:
					with self.assertRaises(frappe.ValidationError):
						pr._process_v2_gateway()

					# Verify error was logged
					mock_log_error.assert_called_once()
					call_kwargs = mock_log_error.call_args
					self.assertIn("Payment Initialization Failed", str(call_kwargs))
					self.assertIn("_Test Gateway", str(call_kwargs))
