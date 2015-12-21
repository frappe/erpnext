# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, today
from frappe import _
from erpnext.accounts.doctype.journal_entry.journal_entry import get_payment_entry
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import get_account_currency, get_balance_on
from itertools import chain
from paypal_integration.express_checkout import set_express_checkout
class PaymentRequest(Document):		
	def validate(self):
		self.validate_payment_request()	
		
	def validate_payment_request(self):
		if frappe.db.get_value("Payment Request", {"reference_name": self.reference_name, 
			"name": ("!=", self.name), "status": "Paid", "docstatus": 1}, "name"):
			frappe.throw(_("Payment Request already exist"))
		
	def on_submit(self):
		self.send_payment_request()
		self.send_email()
		self.make_communication_entry()
	
	def on_cancel(self):
		pass
	
	def on_update_after_submit(self):
		pass
	
	def set_status(self):
		pass
	
	def send_payment_request(self):
		if self.payment_gateway == "PayPal":	
			self.payment_url = set_express_checkout(self.amount, "USD", {"doctype": self.doctype, 
				"docname": self.name})
		
		if self.payment_url:
			frappe.db.set_value(self.doctype, self.name, "status", "Initiated")
			
	def set_paid(self):
		if frappe.session.user == "Guest":
			frappe.set_user("Administrator")
			
		self.create_journal_voucher_entry()
	
	def create_journal_voucher_entry(self):
		"""create voucher entry"""
		payment_details = {
			"party_type": "Customer",
			"amount_field_party": "credit_in_account_currency",
			"amount_field_bank": "debit_in_account_currency",
			"amount": self.amount,
			"return_obj": True
		}
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name) 
		
		if self.reference_doctype == "Sales Order":
			party_account = get_party_account("Customer", ref_doc.get('customer'), ref_doc.company)
			payment_details.update({
				"party_account": party_account,
				"party_account_currency": get_account_currency(party_account),
				"remarks": 'Advance Payment received against {0} {1}'.format(self.reference_doctype, self.reference_name),
				"is_advance": "Yes"
			})
		if self.reference_doctype == "Sales Invoice":
			payment_details.update({
				"party_account": ref_doc.debit_to,
				"party_account_currency": ref_doc.party_account_currency,
				"remarks": 'Payment received against {0} {1}. {2}'.format(self.reference_doctype, self.reference_name, ref_doc.remarks),
				"is_advance": "No"
			})
		
		account_details = frappe.db.get_value("Account", self.payment_account,
					["account_currency", "account_type"], as_dict=1)
					
		payment_details["bank_account"] = {
			"account": self.payment_account,
			"balance": get_balance_on(self.payment_account),
			"account_currency": account_details.account_currency,
			"account_type": account_details.account_type
		}
		
		jv =  get_payment_entry(ref_doc, payment_details)
		
		jv.update({
			"voucher_type": "Journal Entry",
			"posting_date": today()
		})
		jv.submit()
		
		frappe.db.set_value(self.doctype, self.name, "status", "Paid")
		
	def send_email(self):
		"""send email with payment link"""
		frappe.sendmail(recipients=self.email_to, sender=None, subject=self.subject,
			message=self.get_message(), attachments=[frappe.attach_print(self.reference_doctype, 
			self.reference_name, file_name=self.reference_name, print_format=self.print_format)])
						
	def get_message(self):
		"""return message with payment gateway link"""
		return self.message + self.payment_url if self.payment_url else ""
		
	def set_failed(self):
		pass
	
	def set_cancelled(self):
		frappe.db.set_value(self.doctype, self.name, "status", "Cancelled")
	
	def make_communication_entry(self):
		"""Make communication entry"""
		comm = frappe.get_doc({
			"doctype":"Communication",
			"subject": self.subject,
			"content": self.get_message(),
			"sent_or_received": "Sent",
			"reference_doctype": self.reference_doctype,
			"reference_name": self.reference_name
		})
		comm.insert(ignore_permissions=True)

@frappe.whitelist()
def make_payment_request(dt, dn, recipient_id=None):
	"""Make payment request"""
	ref_doc = get_reference_doc_details(dt, dn)
	payment_gateway, payment_account = get_gateway_details()
	
	pr = frappe.new_doc("Payment Request")
	pr.update({
		"payment_gateway": payment_gateway,
		"payment_account": payment_account,
		"currency": ref_doc.currency,
		"amount": get_amount(ref_doc, dt),
		"email_to": recipient_id,
		"subject": "Payment Request for %s"%dn,
		"message": frappe.get_doc("Accounts Settings").message,
		"reference_doctype": dt,
		"reference_name": dn
	})
	
	return pr.as_dict()

def get_reference_doc_details(dt, dn):
	""" return reference doc Sales Order/Sales Invoice"""
	return frappe.get_doc(dt, dn)

def get_amount(ref_doc, dt):
	"""get amount based on doctype"""
	if dt == "Sales Order":
		amount = flt(ref_doc.grand_total) - flt(ref_doc.advance_paid)
	
	if dt == "Sales Invoice":
		amount = abs(ref_doc.outstanding_amount)
	
	if amount > 0:
		return amount
	else:
		frappe.throw(_("Payment Entry is already created"))
		
def get_gateway_details():
	"""return gateway and payment account of default payment gateway"""
	return frappe.db.get_value("Payment Gateway", {"is_default": 1}, ["gateway", "payment_account"])

@frappe.whitelist()
def get_print_format_list(ref_doctype):
	print_format_list = ["Standard"]
	
	print_format_list.extend(list(chain.from_iterable(frappe.db.sql("""select name from `tabPrint Format` 
		where doc_type=%s""", ref_doctype, as_list=1))))
	
	return {
		"print_format": print_format_list
	}
	