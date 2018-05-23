# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from six.moves.urllib.parse import urlencode
from frappe.utils import get_url, call_hook_method, cint, flt
from frappe.integrations.utils import make_get_request, make_post_request, create_request_log, create_payment_gateway
import stripe

class StripeSettings(Document):
	supported_currencies = [
		"AED", "ALL", "ANG", "ARS", "AUD", "AWG", "BBD", "BDT", "BIF", "BMD", "BND",
		"BOB", "BRL", "BSD", "BWP", "BZD", "CAD", "CHF", "CLP", "CNY", "COP", "CRC", "CVE", "CZK", "DJF",
		"DKK", "DOP", "DZD", "EGP", "ETB", "EUR", "FJD", "FKP", "GBP", "GIP", "GMD", "GNF", "GTQ", "GYD",
		"HKD", "HNL", "HRK", "HTG", "HUF", "IDR", "ILS", "INR", "ISK", "JMD", "JPY", "KES", "KHR", "KMF",
		"KRW", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD", "MAD", "MDL", "MNT", "MOP", "MRO", "MUR", "MVR",
		"MWK", "MXN", "MYR", "NAD", "NGN", "NIO", "NOK", "NPR", "NZD", "PAB", "PEN", "PGK", "PHP", "PKR",
		"PLN", "PYG", "QAR", "RUB", "SAR", "SBD", "SCR", "SEK", "SGD", "SHP", "SLL", "SOS", "STD", "SVC",
		"SZL", "THB", "TOP", "TTD", "TWD", "TZS", "UAH", "UGX", "USD", "UYU", "UZS", "VND", "VUV", "WST",
		"XAF", "XOF", "XPF", "YER", "ZAR"
	]

	currency_wise_minimum_charge_amount = {
		'JPY': 50, 'MXN': 10, 'DKK': 2.50, 'HKD': 4.00, 'NOK': 3.00, 'SEK': 3.00,
		'USD': 0.50, 'AUD': 0.50, 'BRL': 0.50, 'CAD': 0.50, 'CHF': 0.50, 'EUR': 0.50,
		'GBP': 0.30, 'NZD': 0.50, 'SGD': 0.50
	}

	def on_update(self):
		create_payment_gateway('Stripe-' + self.gateway_name, settings='Stripe Settings', controller=self.gateway_name)
		call_hook_method('payment_gateway_enabled', gateway='Stripe-' + self.gateway_name)
		if not self.flags.ignore_mandatory:
			self.validate_stripe_credentails()

	def validate_stripe_credentails(self):
		if self.publishable_key and self.secret_key:
			header = {"Authorization": "Bearer {0}".format(self.get_password(fieldname="secret_key", raise_exception=False))}
			try:
				make_get_request(url="https://api.stripe.com/v1/charges", headers=header)
			except Exception:
				frappe.throw(_("Seems Publishable Key or Secret Key is wrong !!!"))

	def validate_transaction_currency(self, currency):
		if currency not in self.supported_currencies:
			frappe.throw(_("Please select another payment method. Stripe does not support transactions in currency '{0}'").format(currency))

	def validate_minimum_transaction_amount(self, currency, amount):
		if currency in self.currency_wise_minimum_charge_amount:
			if flt(amount) < self.currency_wise_minimum_charge_amount.get(currency, 0.0):
				frappe.throw(_("For currency {0}, the minimum transaction amount should be {1}").format(currency,
					self.currency_wise_minimum_charge_amount.get(currency, 0.0)))

	def get_payment_url(self, **kwargs):
		return get_url("./integrations/stripe_checkout?{0}".format(urlencode(kwargs)))

	def create_request(self, data):
		self.data = frappe._dict(data)
		stripe.api_key = self.get_password(fieldname="secret_key", raise_exception=False)
		stripe.default_http_client = stripe.http_client.RequestsClient()

		try:
			self.integration_request = create_request_log(self.data, "Host", "Stripe")
			if frappe.db.get_value("Payment Request", self.data.reference_docname, 'is_a_subscription'):
				self.payment_plan = frappe.db.get_value("Payment Request", self.data.reference_docname, 'payment_plan')
				return self.create_subscription_on_stripe()
			else:
				return self.create_charge_on_stripe()

		except Exception:
			frappe.log_error(frappe.get_traceback())
			return{
				"redirect_to": frappe.redirect_to_message(_('Server Error'), _("It seems that there is an issue with the server's stripe configuration. In case of failure, the amount will get refunded to your account.")),
				"status": 401
			}

	def create_charge_on_stripe(self):
		try:
			charge = stripe.Charge.create(amount=cint(flt(self.data.amount)*100), currency=self.data.currency, source=self.data.stripe_token_id, description=self.data.description)

			if charge.captured == True:
				self.integration_request.db_set('status', 'Completed', update_modified=False)
				self.flags.status_changed_to = "Completed"

			else:
				frappe.log_error(charge.failure_message, 'Stripe Payment not completed')

		except:
			frappe.log_error(frappe.get_traceback())
			# failed
			pass

		return self.finalize_request()

	def create_subscription_on_stripe(self):
		items = [
				{
				"plan": self.payment_plan
				}
			]

		try:
			customer = stripe.Customer.create(description=self.data.payer_name, email=self.data.payer_email, source=self.data.stripe_token_id)
			subscription = stripe.Subscription.create(customer=customer, items=items)

			if subscription.status == "active":
				self.integration_request.db_set('status', 'Completed', update_modified=False)
				self.flags.status_changed_to = "Completed"

			else:
				self.integration_request.db_set('status', 'Failed', update_modified=False)
				frappe.log_error(str(resp), 'Stripe Payment not completed')

		except:
			self.integration_request.db_set('status', 'Failed', update_modified=False)
			frappe.log_error(frappe.get_traceback())
			# failed
			pass

		return self.finalize_request()

	def finalize_request(self):
		redirect_to = self.data.get('redirect_to') or None
		redirect_message = self.data.get('redirect_message') or None
		status = self.integration_request.status

		if self.flags.status_changed_to == "Completed":
			if self.data.reference_doctype and self.data.reference_docname:
				custom_redirect_to = None
				try:
					custom_redirect_to = frappe.get_doc(self.data.reference_doctype,
						self.data.reference_docname).run_method("on_payment_authorized", self.flags.status_changed_to)
				except Exception:
					frappe.log_error(frappe.get_traceback())

				if custom_redirect_to:
					redirect_to = custom_redirect_to

				redirect_url = 'payment-success'

			if self.redirect_url:
				redirect_url = self.redirect_url
				redirect_to = None
		else:
			redirect_url = 'payment-failed'

		if redirect_to:
			redirect_url += '?' + urlencode({'redirect_to': redirect_to})
		if redirect_message:
			redirect_url += '&' + urlencode({'redirect_message': redirect_message})

		return {
			"redirect_to": redirect_url,
			"status": status
		}

def get_gateway_controller(doc):
	payment_request = frappe.get_doc("Payment Request", doc)
	gateway_controller = frappe.db.get_value("Payment Gateway", payment_request.payment_gateway, "gateway_controller")
	return gateway_controller
