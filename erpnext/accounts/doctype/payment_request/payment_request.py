# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate, get_url
from erpnext.accounts.party import get_party_account
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry, get_company_defaults
from frappe.integrations.utils import get_payment_gateway_controller

class PaymentRequest(Document):
	def validate(self):
		self.validate_reference_document()
		self.validate_payment_request()
		self.validate_currency()

	def validate_reference_document(self):
		if not self.reference_doctype or not self.reference_name:
			frappe.throw(_("To create a Payment Request reference document is required"))

	def validate_payment_request(self):
		if frappe.db.get_value("Payment Request", {"reference_name": self.reference_name,
			"name": ("!=", self.name), "status": ("not in", ["Initiated", "Paid"]), "docstatus": 1}, "name"):
			frappe.throw(_("Payment Request already exists {0}".format(self.reference_name)))

	def validate_currency(self):
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if self.payment_account and ref_doc.currency != frappe.db.get_value("Account", self.payment_account, "account_currency"):
			frappe.throw(_("Transaction currency must be same as Payment Gateway currency"))

	def on_submit(self):
		send_mail = True
		self.make_communication_entry()
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)

		if hasattr(ref_doc, "order_type") and getattr(ref_doc, "order_type") == "Shopping Cart":
			send_mail = False

		if send_mail and not self.flags.mute_email:
			self.set_payment_request_url()
			self.send_email()

	def on_cancel(self):
		self.check_if_payment_entry_exists()
		self.set_as_cancelled()

	def make_invoice(self):
		ref_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		if hasattr(ref_doc, "order_type") and getattr(ref_doc, "order_type") == "Shopping Cart":
			from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
			si = make_sales_invoice(self.reference_name, ignore_permissions=True)
			si = si.insert(ignore_permissions=True)
			si.submit()

	def set_payment_request_url(self):
		if self.payment_account:
			self.payment_url = self.get_payment_url()

		if self.payment_url:
			self.db_set('payment_url', self.payment_url)

		if self.payment_url or not self.payment_gateway_account:
			self.db_set('status', 'Initiated')

	def get_payment_url(self):
		data = frappe.db.get_value(self.reference_doctype, self.reference_name,
			["company", "customer_name"], as_dict=1)

		controller = get_payment_gateway_controller(self.payment_gateway)
		controller.validate_transaction_currency(self.currency)

		return controller.get_payment_url(**{
			"amount": flt(self.grand_total, self.precision("grand_total")),
			"title": data.company,
			"description": self.subject,
			"reference_doctype": "Payment Request",
			"reference_docname": self.name,
			"payer_email": self.email_to or frappe.session.user,
			"payer_name": data.customer_name,
			"order_id": self.name,
			"currency": self.currency
		})

	def set_as_paid(self):
		if frappe.session.user == "Guest":
			frappe.set_user("Administrator")

		payment_entry = self.create_payment_entry()
		self.make_invoice()

		return payment_entry

	def create_payment_entry(self, submit=True):
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

		if payment_entry.difference_amount:
			company_details = get_company_defaults(ref_doc.company)

			payment_entry.append("deductions", {
				"account": company_details.exchange_gain_loss_account,
				"cost_center": company_details.cost_center,
				"amount": payment_entry.difference_amount
			})

		if submit:
			payment_entry.insert(ignore_permissions=True)
			payment_entry.submit()

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

		if self.message:
			return frappe.render_template(self.message, context)

	def set_failed(self):
		pass

	def set_as_cancelled(self):
		self.db_set("status", "Cancelled")

	def check_if_payment_entry_exists(self):
		if self.status == "Paid":
			payment_entry = frappe.db.sql_list("""select parent from `tabPayment Entry Reference`
				where reference_name=%s""", self.reference_name)
			if payment_entry:
				frappe.throw(_("Payment Entry already exists"), title=_('Error'))

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

	def on_payment_authorized(self, status=None):
		if not status:
			return

		shopping_cart_settings = frappe.get_doc("Shopping Cart Settings")

		if status in ["Authorized", "Completed"]:
			redirect_to = None
			self.run_method("set_as_paid")

			# if shopping cart enabled and in session
			if (shopping_cart_settings.enabled and hasattr(frappe.local, "session")
				and frappe.local.session.user != "Guest"):

				success_url = shopping_cart_settings.payment_success_url
				if success_url:
					redirect_to = ({
						"Orders": "orders",
						"Invoices": "invoices",
						"My Account": "me"
					}).get(success_url, "me")
				else:
					redirect_to = get_url("/orders/{0}".format(self.reference_name))

			return redirect_to

@frappe.whitelist(allow_guest=True)
def make_payment_request(**args):
	"""Make payment request"""

	args = frappe._dict(args)

	ref_doc = frappe.get_doc(args.dt, args.dn)

	gateway_account = get_gateway_details(args) or frappe._dict()

	grand_total = get_amount(ref_doc, args.dt)

	existing_payment_request = frappe.db.get_value("Payment Request",
		{"reference_doctype": args.dt, "reference_name": args.dn, "docstatus": ["!=", 2]})

	if existing_payment_request:
		pr = frappe.get_doc("Payment Request", existing_payment_request)

	else:
		pr = frappe.new_doc("Payment Request")
		pr.update({
			"payment_gateway_account": gateway_account.get("name"),
			"payment_gateway": gateway_account.get("payment_gateway"),
			"payment_account": gateway_account.get("payment_account"),
			"currency": ref_doc.currency,
			"grand_total": grand_total,
			"email_to": args.recipient_id or "",
			"subject": "Payment Request for %s"%args.dn,
			"message": gateway_account.get("message") or get_dummy_message(ref_doc),
			"reference_doctype": args.dt,
			"reference_name": args.dn
		})

		if args.return_doc:
			return pr

		if args.mute_email:
			pr.flags.mute_email = True

		if args.submit_doc:
			pr.insert(ignore_permissions=True)
			pr.submit()

	if hasattr(ref_doc, "order_type") and getattr(ref_doc, "order_type") == "Shopping Cart":
		frappe.db.commit()
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = pr.get_payment_url()

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
def resend_payment_email(docname):
	return frappe.get_doc("Payment Request", docname).send_email()

@frappe.whitelist()
def make_payment_entry(docname):
	doc = frappe.get_doc("Payment Request", docname)
	return doc.create_payment_entry(submit=False).as_dict()

def make_status_as_paid(doc, method):
	for ref in doc.references:
		payment_request_name = frappe.db.get_value("Payment Request",
			{"reference_doctype": ref.reference_doctype, "reference_name": ref.reference_name,
			"docstatus": 1})

		if payment_request_name:
			doc = frappe.get_doc("Payment Request", payment_request_name)
			if doc.status != "Paid":
				doc.db_set('status', 'Paid')
				frappe.db.commit()

def get_dummy_message(doc):
	return frappe.render_template("""{% if doc.contact_person -%}
<p>Dear {{ doc.contact_person }},</p>
{%- else %}<p>Hello,</p>{% endif %}

<p>{{ _("Requesting payment against {0} {1} for amount {2}").format(doc.doctype,
	doc.name, doc.get_formatted("grand_total")) }}</p>

<a href="{{ payment_url }}">{{ _("Make Payment") }}</a>

<p>{{ _("If you have any questions, please get back to us.") }}</p>

<p>{{ _("Thank you for your business!") }}</p>
""", dict(doc=doc, payment_url = '{{ payment_url }}'))
