# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
import json
import requests
from six.moves.urllib.parse import urlencode

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import get_url, call_hook_method, cint, flt, cstr
from frappe.integrations.utils import create_request_log, create_payment_gateway
from frappe.utils import get_request_site_address
from frappe.utils.password import get_decrypted_password
from frappe.utils import get_request_site_address
from erpnext.erpnext_integrations.utils import create_mode_of_payment
from erpnext.erpnext_integrations.doctype.mpesa_settings.mpesa_connector import MpesaConnector
from erpnext.erpnext_integrations.doctype.mpesa_settings.mpesa_custom_fields import create_custom_pos_fields

class MpesaSettings(Document):
	supported_currencies = ["KES"]

	def validate_transaction_currency(self, currency):
		if currency not in self.supported_currencies:
			frappe.throw(_("Please select another payment method. Mpesa does not support transactions in currency '{0}'").format(currency))

	def on_update(self):
		create_custom_pos_fields()
		create_payment_gateway('Mpesa-' + self.payment_gateway_name, settings='Mpesa Settings', controller=self.payment_gateway_name)
		create_mode_of_payment('Mpesa-' + self.payment_gateway_name)
		call_hook_method('payment_gateway_enabled', gateway='Mpesa-' + self.payment_gateway_name, payment_channel="Phone")

	def request_for_payment(self, **kwargs):
		response = frappe._dict(generate_stk_push(**kwargs))
		# check error response
		if hasattr(response, "requestId"):
			req_name = getattr(response, "requestId")
			error = response
		else:
			# global checkout id used as request name
			req_name = getattr(response, "CheckoutRequestID")
			error = None

		create_request_log(kwargs, "Host", "Mpesa", req_name, error)
		if error:
			frappe.throw(_(getattr(response, "errorMessage")), title=_("Transaction Error"))

def generate_stk_push(**kwargs):
	args = frappe._dict(kwargs)
	try:
		callback_url = get_request_site_address(True) + "/api/method/erpnext.erpnext_integrations.doctype.mpesa_settings.mpesa_settings.verify_transaction"

		mpesa_settings = frappe.get_doc("Mpesa Settings", args.payment_gateway[6:])
		env = "production" if not mpesa_settings.sandbox else "sandbox"

		connector = MpesaConnector(env=env,
			app_key=mpesa_settings.consumer_key,
			app_secret=mpesa_settings.get_password("consumer_secret"))

		response = connector.stk_push(business_shortcode=mpesa_settings.till_number,
			passcode=mpesa_settings.get_password("online_passkey"), amount=args.grand_total,
			callback_url=callback_url, reference_code=args.payment_request_name,
			phone_number=args.sender, description="POS Payment")

		return response

	except Exception:
		frappe.log_error(title=_("Mpesa Express Transaction Error"))
		frappe.throw(_("Issue detected with Mpesa configuration, check the error logs for more details"), title=_("Mpesa Express Error"))

@frappe.whitelist(allow_guest=True)
def verify_transaction(**kwargs):
	""" Verify the transaction result received via callback """
	transaction_response = frappe._dict(kwargs["Body"]["stkCallback"])

	checkout_id = getattr(transaction_response, "CheckoutRequestID")
	request = frappe.get_doc("Integration Request", checkout_id)
	transaction_data = frappe._dict(json.loads(request.data))

	if transaction_response['ResultCode'] == 0:
		if transaction_data.reference_doctype and transaction_data.reference_docname:
			try:
				frappe.get_doc(transaction_data.reference_doctype,
					transaction_data.reference_docname).run_method("on_payment_authorized", 'Completed')
				request.db_set('output', transaction_response)
				request.db_set('status', 'Completed')
			except Exception:
				request.db_set('error', transaction_response)
				request.db_set('status', 'Failed')
				frappe.log_error(frappe.get_traceback())

	else:
		request.db_set('error', transaction_response)
		request.db_set('status', 'Failed')

	frappe.publish_realtime('process_phone_payment', after_commit=True, user=request.owner, message=transaction_response)