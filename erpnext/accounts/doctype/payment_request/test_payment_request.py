# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request, get_gateway_details
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.setup.utils import get_exchange_rate
# test_records = frappe.get_test_records('Payment Request')

test_dependencies = ["Currency Exchange", "Journal Entry", "Contact", "Address"]

payment_gateway = {
	"doctype": "Payment Gateway",
	"gateway": "_Test Gateway"
}

payment_method = [
	{
		"doctype": "Payment Gateway Account",
		"is_default": 1,
		"payment_gateway": "_Test Gateway",
		"payment_account": "_Test Bank - _TC",
		"currency": "INR"
	},
	{
		"doctype": "Payment Gateway Account",
		"payment_gateway": "_Test Gateway",
		"payment_account": "_Test Bank USD - _TC",
		"currency": "USD"
	}
]

class TestPaymentRequest(unittest.TestCase):
	def setUp(self):
		if not frappe.db.get_value("Payment Gateway", payment_gateway["gateway"], "name"):
			frappe.get_doc(payment_gateway).insert(ignore_permissions=True)
			
		for method in payment_method:
			if not frappe.db.get_value("Payment Gateway Account", {"payment_gateway": method["payment_gateway"], 
				"currency": method["currency"]}, "name"):
				frappe.get_doc(method).insert(ignore_permissions=True)
			
	def test_payment_request_linkings(self):
		so_inr = make_sales_order(currency="INR")
		pr = make_payment_request(dt="Sales Order", dn=so_inr.name, recipient_id="saurabh@erpnext.com")

		self.assertEquals(pr.reference_doctype, "Sales Order")
		self.assertEquals(pr.reference_name, so_inr.name)
		self.assertEquals(pr.currency, "INR")

		conversion_rate = get_exchange_rate("USD", "INR")

		si_usd = create_sales_invoice(currency="USD", conversion_rate=conversion_rate)
		pr = make_payment_request(dt="Sales Invoice", dn=si_usd.name, recipient_id="saurabh@erpnext.com")

		self.assertEquals(pr.reference_doctype, "Sales Invoice")
		self.assertEquals(pr.reference_name, si_usd.name)
		self.assertEquals(pr.currency, "USD")

	def test_payment_entry(self):
		so_inr = make_sales_order(currency="INR")
		pr = make_payment_request(dt="Sales Order", dn=so_inr.name, recipient_id="saurabh@erpnext.com",
			mute_email=1, submit_doc=1)
		jv = pr.set_as_paid()

		so_inr = frappe.get_doc("Sales Order", so_inr.name)

		self.assertEquals(so_inr.advance_paid, jv.total_debit)

		conversion_rate = get_exchange_rate("USD", "INR")

		si_usd = create_sales_invoice(customer="_Test Customer USD", debit_to="_Test Receivable USD - _TC",
			currency="USD", conversion_rate=conversion_rate)

		pr = make_payment_request(dt="Sales Invoice", dn=si_usd.name, recipient_id="saurabh@erpnext.com",
			mute_email=1, return_doc=1, payment_gateway="_Test Gateway - USD")

		jv = pr.set_as_paid()

		payment_gateway_details = get_gateway_details({"payment_gateway": "_Test Gateway - USD"})
				
		self.assertEquals(jv.accounts[0].account, "_Test Receivable USD - _TC")
		self.assertEquals(jv.accounts[1].account, payment_gateway_details.payment_account)
		