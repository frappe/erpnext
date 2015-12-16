# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class PaymentRequest(Document):
	def on_submit(self):
		self.send_payment_request()
	
	def send_payment_request(self):
		pass
		
	def set_paid(self):
		pass
	
	def set_failed(self):
		pass
	
	def set_cancelled(self):
		pass

@frappe.whitelist()
def make_payment_request(dt, dn, recipient_id):
	"""Make payment request"""
	ref_doc = get_reference_doc_details(dt, dn)
	
	pr = frappe.get_doc({
		"doctype": "Payment Request",
		"currency": ref_doc.currency,
		"amount": get_amount(ref_doc, dt),
		"email_to": recipient_id,
		"reference_doctype": dt,
		"reference_name": dn
	}).insert()

	pr.submit()

def get_reference_doc_details(dt, dn):
	""" return reference doc Sales Order/Sales Invoice"""
	return frappe.get_doc(dt, dn)

def get_amount(ref_doc, dt):
	if dt == "Sales Order":
		return flt(ref_doc.grand_total) - flt(ref_doc.advance_paid)