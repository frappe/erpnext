# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.integration_controller.utils.request_handler import get_request
from erpnext.integration_controller.utils.gateway_accounts_handler import create_payment_gateway_and_account

def enable_service(doc=None):
	create_payment_gateway_and_account("Razorpay")
	validate_razorpay_credentails(doc)

def validate_razorpay_credentails(doc=None, method=None):
	razorpay_settings = get_razorpay_settings(doc)

	if razorpay_settings.get("api_key"):
		try:
			get_request(url="https://api.razorpay.com/v1/payments", auth=(razorpay_settings.api_key,
				razorpay_settings.api_secret))
		except Exception, e:
			frappe.throw(_(e.message))

def get_razorpay_settings(doc=None):
	settings = frappe._dict()
	
	if not doc and frappe.db.exists("Integration Service", "Razorpay"):
		doc = frappe.get_doc("Integration Service", "Razorpay")
	
	for auth in doc.authentication_details:
		settings[auth.parameter.strip().lower().replace(' ','_')] = auth.value

	return settings
		