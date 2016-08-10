# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from urllib import urlencode
from frappe.utils import get_url, call_hook_method
from frappe.integration_broker.integration_controller import IntegrationController

class Controller(IntegrationController):
	service_name = 'PayPal'
	parameters_template = [
		{
			"label": "API Username",
			'fieldname': 'api_username',
			'reqd': 1
		},
		{
			"label": "API Password",
			'fieldname': 'api_password',
			'reqd': 1
		},
		{
			"label": "Signature",
			"fieldname": "signature",
			"reqd": 1
		}
	]
	
	supported_currencies = ["AUD", "BRL", "CAD", "CZK", "DKK", "EUR", "HKD", "HUF", "ILS", "JPY", "MYR", "MXN",
		"TWD", "NZD", "NOK", "PHP", "PLN", "GBP", "RUB", "SGD", "SEK", "CHF", "THB", "TRY", "USD"]
	
	test_url = "https://api-3t.sandbox.paypal.com/nvp"
	
	live_url = "https://api-3t.paypal.com/nvp"
	
	def enable(self, parameters, use_test_account=0):
		call_hook_method('payment_gateway_enabled', gateway=self.service_name)
		self.parameters = parameters
		self.validate_paypal_credentails(use_test_account)
	
	def get_settings(self):
		if hasattr(self, "parameters"):
			return frappe._dict(self.get_parameters())
		else:
			return frappe.get_doc("Integration Service", self.service_name).get_parameters()
	
	def validate_transaction_currency(self, currency):
		if currency not in self.supported_currencies:
			frappe.throw(_("Please select another payment method. {0} does not support transactions in currency '{1}'").format(self.service_name, currency))
	
	def get_paypal_params_and_url(self, use_test_account):
		payapl_settings = frappe._dict(self.get_settings())
		
		params = {
			"USER": payapl_settings.api_username,
			"PWD": payapl_settings.api_password,
			"SIGNATURE": payapl_settings.signature,
			"VERSION": "98",
			"METHOD": "GetPalDetails"
		}

		if use_test_account:
			api_url = self.test_url
		else:
			api_url = self.live_url
		
		return params, api_url

	def validate_paypal_credentails(self, use_test_account):
		params, url = self.get_paypal_params_and_url(use_test_account)
		params = urlencode(params)

		try:
			self.post_request(url=url, data=params.encode("utf-8"))
		except Exception, e:
			frappe.throw(_("Invalid payment gateway credentials"))

	def get_payment_url(self, **kwargs):
		use_test_account = frappe.db.get_value("Integration Service", self.service_name, "use_test_account")
		
		response = self.execute_set_express_checkout(kwargs["amount"], kwargs["currency"], use_test_account)
		
		if use_test_account:
			return_url = "https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token={0}"
		else:
			return_url = "https://www.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token={0}"

		kwargs.update({
			"token": response.get("TOKEN")[0],
			"correlation_id": response.get("CORRELATIONID")[0]
		})
		
		self.integration_request = self.make_integration_request(kwargs, "Remote", self.service_name, response.get("TOKEN")[0])
				
		return return_url.format(kwargs["token"])
		# frappe.local.response["type"] = "redirect"
		# frappe.local.response["location"] = return_url.format(data["token"])

	def execute_set_express_checkout(self, amount, currency, use_test_account):
		params, url = self.get_paypal_params_and_url(use_test_account)
		params.update({
			"METHOD": "SetExpressCheckout",
			"PAYMENTREQUEST_0_PAYMENTACTION": "SALE",
			"PAYMENTREQUEST_0_AMT": amount,
			"PAYMENTREQUEST_0_CURRENCYCODE": currency,
			"returnUrl": get_url("/api/method/erpnext.integrations.paypal.get_express_checkout_details"),
			"cancelUrl": get_url("/paypal-express-cancel")
		})
		
		params = urlencode(params)

		response = self.post_request(url, data=params.encode("utf-8"))
		
		if response.get("ACK")[0] != "Success":
			frappe.respond_as_web_page(_("Something went wrong"),
				_("Looks like something is wrong with this site's Paypal configuration. Don't worry! No payment has been made from your Paypal account."),
				success=False,
				http_status_code=frappe.ValidationError.http_status_code)

			return
		
		return response

@frappe.whitelist(allow_guest=True, xss_safe=True)
def get_express_checkout_details(token):
	use_test_account = frappe.db.get_value("Integration Service", "PayPal", "use_test_account")
	
	params, url = Controller().get_paypal_params_and_url(use_test_account)
	params.update({
		"METHOD": "GetExpressCheckoutDetails",
		"TOKEN": token
	})

	response = Controller().post_request(url, data=params)

	if response.get("ACK")[0] != "Success":
		frappe.respond_as_web_page(_("Something went wrong"),
			_("Looks like something went wrong during the transaction. Since we haven't confirmed the payment, Paypal will automatically refund you this amount. If it doesn't, please send us an email and mention the Correlation ID: {0}.").format(response.get("CORRELATIONID", [None])[0]),
			success=False,
			http_status_code=frappe.ValidationError.http_status_code)

		return
	
	update_integration_request_status(token, {
			"payerid": response.get("PAYERID")[0],
			"payer_email": response.get("EMAIL")[0]
		}, "Authorized")
	
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = get_url( \
		"/api/method/erpnext.integrations.paypal.confirm_payment?token={0}".format(token))

@frappe.whitelist(allow_guest=True, xss_safe=True)
def confirm_payment(token):
	redirect = True
	status_changed_to, redirect_to = None, None
	
	use_test_account = frappe.db.get_value("Integration Service", "PayPal", "use_test_account")
	integration_request = frappe.get_doc("Integration Request", token)

	data = json.loads(integration_request.data)

	params, url = Controller().get_paypal_params_and_url(use_test_account)
	params.update({
		"METHOD": "DoExpressCheckoutPayment",
		"PAYERID": data.get("payerid"),
		"TOKEN": token,
		"PAYMENTREQUEST_0_PAYMENTACTION": "SALE",
		"PAYMENTREQUEST_0_AMT": data.get("amount"),
		"PAYMENTREQUEST_0_CURRENCYCODE": data.get("currency")
	})

	response = Controller().post_request(url, data=params)

	if response.get("ACK")[0] == "Success":
		update_integration_request_status(token, {
			"transaction_id": response.get("PAYMENTINFO_0_TRANSACTIONID")[0],
			"correlation_id": response.get("CORRELATIONID")[0]
		}, "Completed")

		if data.get("reference_doctype") and data.get("reference_docname"):
			redirect_to = frappe.get_doc(data.get("reference_doctype"), data.get("reference_docname")).run_method("on_payment_authorized", "Completed")

		redirect_to = redirect_to or get_url("/razorpay-payment-success")

	else:
		redirect_to = get_url("/paypal-express-failed")

	# this is done so that functions called via hooks can update flags.redirect_to
	if redirect:
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = redirect_to

def update_integration_request_status(token, data, status, error=False):
	frappe.get_doc("Integration Request", token).update_status(data, status)