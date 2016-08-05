# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.integration_broker.integration_controller import IntegrationController
from frappe.utils import get_url
import urllib, json
from erpnext.integrations.utils.request_handler import get_request, post_request, make_request
from erpnext.integrations.utils.payment_gateway_handler import (create_payment_gateway_and_account,
	set_redirect, validate_transaction_currency)

class Controller(IntegrationController):
	service_name = 'Razorpay'
	parameters_template = [
		{
			"label": "API Key",
			'fieldname': 'api_key',
			'reqd': 1
		},
		{
			"label": "API Secret",
			'fieldname': 'api_secret',
			'reqd': 1
		}
	]
	
	scheduled_jobs = [
		{"daily": ["erpnext.integrations.events.payment_completion.complete_payment"]}
	]
	
	supported_currencies = ["INR"]
	
	def enable(self, parameters):
		create_payment_gateway_and_account("Razorpay")
		
		self.parameters = parameters
		self.validate_razorpay_credentails()

	def validate_razorpay_credentails(self):
		razorpay_settings = self.get_settings()

		if razorpay_settings.get("api_key"):
			try:
				get_request(url="https://api.razorpay.com/v1/payments",
					auth=(razorpay_settings.api_key, razorpay_settings.api_secret))
			except Exception:
				frappe.throw(_("Seems API Key or API Secret is wrong !!!"))
	
	def validate_transaction_currency(self, doc):
		if getattr(doc, "currency", None):
			validate_transaction_currency(self.supported_currencies, doc.currency, self.service_name)
	
	def get_payment_url(self, **kwargs):
		return get_url("./razorpay_checkout?{0}".format(urllib.urlencode(kwargs)))
	
	def get_settings(self):
		return frappe._dict(self.get_parameters())
	
	def make_request(self, data):
		setattr(self, "reference_docname", data.get("reference_docname"))
		setattr(self, "reference_doctype", data.get("reference_doctype"))
		setattr(self, "razorpay_payment_id", data.get("razorpay_payment_id"))
		
		try:
			self.integration_request = make_request(data, "Host", self.service_name)
			return self.authorise_payment(data)

		except Exception:
			return{
				"redirect_to": frappe.redirect_to_message(_('Server Error'), _("Seems issue with server's razorpay config. Don't worry, in case of failure amount will get refunded to your account.")),
				"status": 401
			}
		
	def authorise_payment(self, data):
		settings = self.get_settings()
		if self.integration_request.status != "Authorized":
			confirm_payment(self, settings.api_key, settings.api_secret, self.flags.is_sandbox)
		
		set_redirect(self)
				
		if frappe.db.get_value("Integration Request", self.integration_request.name, "status") == "Authorized":
			return {
				"redirect_to": self.flags.redirect_to or "razorpay-payment-success",
				"status": 200
			}


def confirm_payment(doc, api_key, api_secret, is_sandbox=False):
	"""
	An authorization is performed when user’s payment details are successfully authenticated by the bank.
	The money is deducted from the customer’s account, but will not be transferred to the merchant’s account
	until it is explicitly captured by merchant.
	"""
	
	if is_sandbox and doc.sanbox_response:
		resp = doc.sanbox_response
	else:
		resp = get_request("https://api.razorpay.com/v1/payments/{0}".format(doc.razorpay_payment_id),
			auth=(api_key, api_secret))

	if resp.get("status") == "authorized":
		doc.integration_request.db_set('status', 'Authorized', update_modified=False)
		doc.flags.status_changed_to = "Authorized"


def capture_payment(is_sandbox=False, sanbox_response=None):
	"""
		Verifies the purchase as complete by the merchant.
		After capture, the amount is transferred to the merchant within T+3 days
		where T is the day on which payment is captured.

		Note: Attempting to capture a payment whose status is not authorized will produce an error.
	"""
	settings = frappe.get_doc("Integration Service", "Razorpay").get_parameters()
	
	for doc in frappe.get_all("Integration Request", filters={"status": "Authorized",
		"integration_request_service": "Razorpay"}, fields=["name", "data"]):
		try:
			if is_sandbox:
				resp = sanbox_response
			else:
				data = json.loads(doc.data)
				resp = post_request("https://api.razorpay.com/v1/payments/{0}/capture".format(data.get("razorpay_payment_id")),
					auth=(settings["api_key"], settings["api_secret"]), data={"amount": data.get("amount")})
			
			if resp.get("status") == "captured":
				frappe.db.set_value("Integration Request", doc.name, "status", "Completed")

		except Exception:
			doc = frappe.get_doc("Integration Request", doc.name)
			doc.status = "Failed"
			doc.error = frappe.get_traceback()
