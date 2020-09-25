# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
from json import loads, dumps

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import call_hook_method
from frappe.integrations.utils import create_request_log, create_payment_gateway
from frappe.utils import get_request_site_address
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
		self.handle_api_response("CheckoutRequestID", kwargs, response)

	def get_account_balance_info(self):
		payload = dict(
			reference_doctype="Mpesa Settings",
			reference_docname=self.name,
			doc_details=vars(self)
		)
		response = frappe._dict(get_account_balance(payload))
		self.handle_api_response("ConversationID", payload, response)

	def handle_api_response(self, global_id, request_dict, response):
		# check error response
		if getattr(response, "requestId"):
			req_name = getattr(response, "requestId")
			error = response
		else:
			# global checkout id used as request name
			req_name = getattr(response, global_id)
			error = None

		create_request_log(request_dict, "Host", "Mpesa", req_name, error)

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

	checkout_id = getattr(transaction_response, "CheckoutRequestID", "")
	request = frappe.get_doc("Integration Request", checkout_id)
	transaction_data = frappe._dict(loads(request.data))

	if transaction_response['ResultCode'] == 0:
		if transaction_data.reference_doctype and transaction_data.reference_docname:
			try:
				frappe.get_doc(transaction_data.reference_doctype,
					transaction_data.reference_docname).run_method("on_payment_authorized", 'Completed')
				request.process_response('error', transaction_response)
			except Exception:
				request.process_response('error', transaction_response)
				frappe.log_error(frappe.get_traceback())

	else:
		request.process_response('error', transaction_response)

	frappe.publish_realtime('process_phone_payment', after_commit=True, doctype=transaction_data.reference_doctype,
		docname=transaction_data.reference_docname, user=request.owner, message=transaction_response)

def get_account_balance(request_payload):
	""" Call account balance API to send the request to the Mpesa Servers """
	try:
		mpesa_settings = frappe.get_doc("Mpesa Settings", request_payload.get("reference_docname"))
		env = "production" if not mpesa_settings.sandbox else "sandbox"
		connector = MpesaConnector(env=env,
			app_key=mpesa_settings.consumer_key,
			app_secret=mpesa_settings.get_password("consumer_secret"))

		# callback_url = get_request_site_address(True) + "/api/method/erpnext.erpnext_integrations.doctype.mpesa_settings.mpesa_settings.process_balance_info"
		callback_url = "https://b014ca8e7957.ngrok.io/api/method/erpnext.erpnext_integrations.doctype.mpesa_settings.mpesa_settings.process_balance_info"

		response = connector.get_balance(mpesa_settings.initiator_name, mpesa_settings.security_credential, mpesa_settings.till_number, 4, mpesa_settings.name, callback_url, callback_url)
		return response
	except Exception:
		frappe.log_error(title=_("Account Balance Processing Error"))
		frappe.throw(title=_("Error"), message=_("Please check your configuration and try again"))

@frappe.whitelist(allow_guest=True)
def process_balance_info(**kwargs):

	account_balance_response = frappe._dict(kwargs["Result"])

	conversation_id = getattr(account_balance_response, "ConversationID", "")
	request = frappe.get_doc("Integration Request", conversation_id)

	if request.status == "Completed":
		return

	transaction_data = frappe._dict(loads(request.data))
	frappe.logger().debug(account_balance_response)

	if account_balance_response["ResultCode"] == 0:
		try:
			result_params = account_balance_response["ResultParameters"]["ResultParameter"]
			for param in result_params:
				if param["Key"] == "AccountBalance":
					balance_info = param["Value"]
					balance_info = convert_to_json(balance_info)

			ref_doc = frappe.get_doc(transaction_data.reference_doctype, transaction_data.reference_docname)
			ref_doc.db_set("account_balance", balance_info)

			request.process_response('output', account_balance_response)
		except:
			request.process_response('error', account_balance_response)
			frappe.log_error(title=_("Mpesa Account Balance Processing Error"), message=account_balance_response)
	else:
		request.process_response('error', account_balance_response)

def convert_to_json(balance_info):
	balance_dict = frappe._dict()
	for account_info in balance_info.split("&"):
		account_info = account_info.split('|')
		balance_dict[account_info[0]] = dict(
			current_balance=account_info[2],
			available_balance=account_info[3],
			reserved_balance=account_info[4],
			uncleared_balance=account_info[5]
		)
	return dumps(balance_dict)