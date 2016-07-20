# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_url, nowdate
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry, get_company_defaults

class PaymentRequest(Document):
	def validate(self):
		self.validate_payment_gateway_account()
		self.validate_payment_request()
		self.validate_currency()

	def validate_payment_request(self):
		if frappe.db.get_value("Payment Request", {"reference_name": self.reference_name,
			"name": ("!=", self.name), "status": ("not in", ["Initiated", "Paid"]), "docstatus": 1}, "name"):
			frappe.throw(_("Payment Request already exists {0}".format(self.reference_name)))

	def validate_currency(self):
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if ref_doc.currency != frappe.db.get_value("Account", self.payment_account, "account_currency"):
			frappe.throw(_("Transaction currency must be same as Payment Gateway currency"))

	def validate_payment_gateway_account(self):
		if not self.payment_gateway:
			frappe.throw(_("Payment Gateway Account is not configured"))

	def validate_payment_gateway(self):
		if self.payment_gateway == "PayPal":
			if not frappe.db.get_value("PayPal Settings", None, "api_username"):
				if not frappe.conf.paypal_username:
					frappe.throw(_("PayPal Settings missing"))

	def on_submit(self):
		send_mail = True
		self.make_communication_entry()
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)

		if hasattr(ref_doc, "order_type") and getattr(ref_doc, "order_type") == "Shopping Cart":
			send_mail = False

		if send_mail:
			self.send_payment_request()
			self.send_email()

	def on_cancel(self):
		self.set_as_cancelled()

	def get_payment_url(self):
		""" This is blanck method to trigger hooks call from individual payment gateway app
		which will return respective payment gateway"""
		pass

	def make_invoice(self):
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if hasattr(ref_doc, "order_type") and getattr(ref_doc, "order_type") == "Shopping Cart":
			from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
			si = make_sales_invoice(self.reference_name, ignore_permissions=True)
			si = si.insert(ignore_permissions=True)
			si.submit()

	def send_payment_request(self):
		self.payment_url = get_url("/api/method/erpnext.accounts.doctype.payment_request.payment_request.generate_payment_request?name={0}".format(self.name))
		if self.payment_url:
			self.db_set('payment_url', self.payment_url)
			self.db_set('status', 'Initiated')

	def set_as_paid(self):
		if frappe.session.user == "Guest":
			frappe.set_user("Administrator")

		payment_entry = self.create_payment_entry()
		self.make_invoice()

		return payment_entry

	def create_payment_entry(self):
		"""create entry"""
		frappe.flags.ignore_account_permission = True

		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)

		if self.reference_doctype == "Sales Invoice":
			party_account = ref_doc.debit_to
		elif self.reference_doctype == "Purchase Invoice":
			party_account = ref_doc.credit_to
		else:
			party_account = get_party_account("Customer", ref_doc.get("customer"), ref_doc.company)

		party_account_currency = ref_doc.get("party_account_currency") or get_account_currency(party_account)

		bank_amount = self.grand_total
		if party_account_currency == ref_doc.company_currency and party_account_currency != self.currency:
			party_amount = ref_doc.base_grand_total
		else:
			party_amount = self.grand_total

		payment_entry = get_payment_entry(self.reference_doctype, self.reference_name,
			party_amount=party_amount, bank_account=self.payment_account, bank_amount=bank_amount)

		payment_entry.update({
			"reference_no": self.name,
			"reference_date": nowdate(),
			"remarks": "Payment Entry against {0} {1} via Payment Request {2}".format(self.reference_doctype,
				self.reference_name, self.name)
		})

		company_details = get_company_defaults(ref_doc.company)
		if payment_entry.difference_amount:
			payment_entry.append("deductions", {
				"account": company_details.exchange_gain_loss_account,
				"cost_center": company_details.cost_center,
				"amount": payment_entry.difference_amount
			})
		payment_entry.insert(ignore_permissions=True)
		payment_entry.submit()

		#set status as paid for Payment Request
		self.db_set('status', 'Paid')

		return payment_entry

	def send_email(self):
		"""send email with payment link"""
		frappe.sendmail(recipients=self.email_to, sender=None, subject=self.subject,
			message=self.get_message(), attachments=[frappe.attach_print(self.reference_doctype,
			self.reference_name, file_name=self.reference_name, print_format=self.print_format)])

	def get_message(self):
		"""return message with payment gateway link"""

		context = {
			"doc": frappe.get_doc(self.reference_doctype, self.reference_name),
			"payment_url": self.payment_url
		}

		return frappe.render_template(self.message, context)

	def set_failed(self):
		pass

	def set_as_cancelled(self):
		self.db_set("status", "Cancelled")

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

	def get_payment_success_url(self):
		return self.payment_success_url

@frappe.whitelist(allow_guest=True)
def make_payment_request(**args):
	"""Make payment request"""

	args = frappe._dict(args)

	ref_doc = frappe.get_doc(args.dt, args.dn)

	gateway_account = get_gateway_details(args)

	grand_total = get_amount(ref_doc, args.dt)

	existing_payment_request = frappe.db.get_value("Payment Request",
		{"reference_doctype": args.dt, "reference_name": args.dn, "docstatus": ["!=", 2]})

	if existing_payment_request:
		pr = frappe.get_doc("Payment Request", existing_payment_request)

	else:
		pr = frappe.new_doc("Payment Request")
		pr.update({
			"payment_gateway_account": gateway_account.name,
			"payment_gateway": gateway_account.payment_gateway,
			"payment_account": gateway_account.payment_account,
			"currency": ref_doc.currency,
			"grand_total": grand_total,
			"email_to": args.recipient_id or "",
			"subject": "Payment Request for %s"%args.dn,
			"message": gateway_account.message,
			"reference_doctype": args.dt,
			"reference_name": args.dn
		})

		if args.return_doc:
			return pr
		if args.submit_doc:
			pr.insert(ignore_permissions=True)
			pr.submit()

	if hasattr(ref_doc, "order_type") and getattr(ref_doc, "order_type") == "Shopping Cart":
		generate_payment_request(pr.name)
		frappe.db.commit()

	if not args.cart:
		return pr

	return pr.as_dict()

def get_amount(ref_doc, dt):
	"""get amount based on doctype"""
	if dt == "Sales Order":
		grand_total = flt(ref_doc.grand_total) - flt(ref_doc.advance_paid)

	if dt == "Sales Invoice":
		if ref_doc.party_account_currency == ref_doc.currency:
			grand_total = flt(ref_doc.outstanding_amount)
		else:
			grand_total = flt(ref_doc.outstanding_amount) / ref_doc.conversion_rate

	if grand_total > 0 :
		return grand_total

	else:
		frappe.throw(_("Payment Entry is already created"))

def get_gateway_details(args):
	"""return gateway and payment account of default payment gateway"""
	if args.get("payment_gateway"):
		return get_payment_gateway_account(args.get("payment_gateway"))

	if args.cart:
		payment_gateway_account = frappe.get_doc("Shopping Cart Settings").payment_gateway_account
		return get_payment_gateway_account(payment_gateway_account)

	gateway_account = get_payment_gateway_account({"is_default": 1})

	if not gateway_account:
		frappe.throw(_("Payment Gateway Account is not configured"))

	return gateway_account

def get_payment_gateway_account(args):
	return frappe.db.get_value("Payment Gateway Account", args,
		["name", "payment_gateway", "payment_account", "message"],
			as_dict=1)

@frappe.whitelist()
def get_print_format_list(ref_doctype):
	print_format_list = ["Standard"]

	print_format_list.extend([p.name for p in frappe.get_all("Print Format",
		filters={"doc_type": ref_doctype})])

	return {
		"print_format": print_format_list
	}

@frappe.whitelist(allow_guest=True)
def generate_payment_request(name):
	frappe.get_doc("Payment Request", name).run_method("get_payment_url")

@frappe.whitelist(allow_guest=True)
def resend_payment_email(docname):
	return frappe.get_doc("Payment Request", docname).send_email()
