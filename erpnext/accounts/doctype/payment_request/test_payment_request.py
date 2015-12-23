# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
# test_records = frappe.get_test_records('Payment Request')

test_dependencies = ["Currency Exchange", "Journal Entry", "Contact", "Address"]

payment_method = [
	{
		"doctype": "Payment Gateway",
		"is_default": 1,
		"gateway": "_Test Gateway INR",
		"payment_account": "_Test Bank - _TC",
		"currency": "INR"
	},
	{
		"doctype": "Payment Gateway",
		"gateway": "_Test Gateway USD",
		"payment_account": "_Test Bank - _TC",
		"currency": "USD"
	}
]

class TestPaymentRequest(unittest.TestCase):
	def setUp(self):
		for gateway in payment_method:
			if not frappe.db.get_value("Payment Gateway", gateway["gateway"], "name"):
				frappe.get_doc(gateway).insert(ignore_permissions=True)
			
	def test_payment_request_linkings(self):
		SO_INR = make_sales_order(currency="INR")
		pr = make_payment_request(dt="Sales Order", dn=SO_INR.name, recipient_id="saurabh@erpnext.com")
		
		self.assertEquals(pr.reference_doctype, "Sales Order")
		self.assertEquals(pr.reference_name, SO_INR.name)
		self.assertEquals(pr.currency, "INR")
		
		SI_USD = create_sales_invoice(currency="USD", conversion_rate=50)
		pr = make_payment_request(dt="Sales Invoice", dn=SI_USD.name, recipient_id="saurabh@erpnext.com")

		self.assertEquals(pr.reference_doctype, "Sales Invoice")
		self.assertEquals(pr.reference_name, SI_USD.name)
		self.assertEquals(pr.currency, "USD")
	
	def test_payment_entry(self):
		SO_INR = make_sales_order(currency="INR")
		pr = make_payment_request(dt="Sales Order", dn=SO_INR.name, recipient_id="saurabh@erpnext.com", 
			mute_email=1, submit_doc=1)	 
		jv = pr.set_paid()
		
		SO_INR = frappe.get_doc("Sales Order", SO_INR.name)
		
		self.assertEquals(SO_INR.advance_paid, jv.total_debit)
		
		SI_USD = create_sales_invoice(customer="_Test Customer USD", debit_to="_Test Receivable USD - _TC",
			currency="USD", conversion_rate=50)

		pr = make_payment_request(dt="Sales Invoice", dn=SI_USD.name, recipient_id="saurabh@erpnext.com",
			mute_email=1, submit_doc=1, payemnt_gateway="_Test Gateway USD")
		jv = pr.set_paid()

		self.assertEquals(jv.accounts[0].account, "_Test Receivable USD - _TC")
		self.assertEquals(jv.accounts[0].account_currency, "USD")
		self.assertEquals(jv.accounts[1].account, pr.payment_account)
