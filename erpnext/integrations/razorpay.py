# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.integrations.utils.request_handler import get_request
from erpnext.integrations.utils.payment_gateway_handler import create_payment_gateway_and_account

from frappe.integration_broker.integration_controller import IntegrationController

class Controller(IntegrationController):
	service_name = 'RazorPay'
	_events = [
		{
			"event": "Payment Initialization",
			'called_by': 'Host',
			"enabled": 1,
			'method': 'start_payment'
		},
		{
			"event": "Payment Completion",
			'called_by': 'Remote',
			"enabled": 0,
		},
	]

	_parameters = [
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
	
	def enable(self, parameters):
		self.parameters = parameters
		create_payment_gateway_and_account("Razorpay")
		self.validate_razorpay_credentails()

	def validate_razorpay_credentails(self):
		razorpay_settings = frappe._dict(self.get_parameters())

		if razorpay_settings.get("api_key"):
			try:
				get_request(url="https://api.razorpay.com/v1/payments", auth=(razorpay_settings.api_key,
					razorpay_settings.api_secret))
			except Exception, e:
				frappe.throw(_(e.message))
				
	def get_payemnt_url(self):
		pass
		