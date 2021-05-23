# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt


from __future__ import unicode_literals
from json import loads, dumps

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import call_hook_method, fmt_money
from frappe.integrations.utils import create_request_log, create_payment_gateway
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
		call_hook_method('payment_gateway_enabled', gateway='Mpesa-' + self.payment_gateway_name, payment_channel="Phone")

		# required to fetch the bank account details from the payment gateway account
		frappe.db.commit()
		create_mode_of_payment('Mpesa-' + self.payment_gateway_name, payment_type="Phone")

	def request_for_payment(self, **kwargs):
		args = frappe._dict(kwargs)
		request_amounts = self.split_request_amount_according_to_transaction_limit(args)

		for i, amount in enumerate(request_amounts):
			args.request_amount = amount
			if frappe.flags.in_test:
				from erpnext.erpnext_integrations.doctype.mpesa_settings.test_mpesa_settings import get_payment_request_response_payload
				response = frappe._dict(get_payment_request_response_payload(amount))
			else:
				response = frappe._dict(generate_stk_push(**args))

			self.handle_api_response("CheckoutRequestID", args, response)

	def split_request_amount_according_to_transaction_limit(self, args):
		request_amount = args.request_amount
		if request_amount > self.transaction_limit:
			# make multiple requests
			request_amounts = []
			requests_to_be_made = frappe.utils.ceil(request_amount / self.transaction_limit) # 480/150 = ceil(3.2) = 4
			for i in range(requests_to_be_made):
				amount = self.transaction_limit
				if i == requests_to_be_made - 1:
					amount = request_amount - (self.transaction_limit * i) # for 4th request, 480 - (150 * 3) = 30
				request_amounts.append(amount)
		else:
			request_amounts = [request_amount]

		return request_amounts

	@frappe.whitelist()
	def get_account_balance_info(self):
		payload = dict(
			reference_doctype="Mpesa Settings",
			reference_docname=self.name,
			doc_details=vars(self)
		)

		if frappe.flags.in_test:
			from erpnext.erpnext_integrations.doctype.mpesa_settings.test_mpesa_settings import get_test_account_balance_response
			response = frappe._dict(get_test_account_balance_response())
		else:
			response = frappe._dict(get_account_balance(payload))

		self.handle_api_response("ConversationID", payload, response)

	def handle_api_response(self, global_id, request_dict, response):
		"""Response received from API calls returns a global identifier for each transaction, this code is returned during the callback."""
		# check error response
		if getattr(response, "requestId"):
			req_name = getattr(response, "requestId")
			error = response
		else:
			# global checkout id used as request name
			req_name = getattr(response, global_id)
			error = None

		if not frappe.db.exists('Integration Request', req_name):
			create_request_log(request_dict, "Host", "Mpesa", req_name, error)

		if error:
			frappe.throw(_(getattr(response, "errorMessage")), title=_("Transaction Error"))

def generate_stk_push(**kwargs):
	"""Generate stk push by making a API call to the stk push API."""
	args = frappe._dict(kwargs)
	try:
		callback_url = get_request_site_address(True) + "/api/method/erpnext.erpnext_integrations.doctype.mpesa_settings.mpesa_settings.verify_transaction"

		mpesa_settings = frappe.get_doc("Mpesa Settings", args.payment_gateway[6:])
		env = "production" if not mpesa_settings.sandbox else "sandbox"
		# for sandbox, business shortcode is same as till number
		business_shortcode = mpesa_settings.business_shortcode if env == "production" else mpesa_settings.till_number

		connector = MpesaConnector(env=env,
			app_key=mpesa_settings.consumer_key,
			app_secret=mpesa_settings.get_password("consumer_secret"))

		mobile_number = sanitize_mobile_number(args.sender)

		response = connector.stk_push(
			business_shortcode=business_shortcode, amount=args.request_amount,
			passcode=mpesa_settings.get_password("online_passkey"),
			callback_url=callback_url, reference_code=mpesa_settings.till_number,
			phone_number=mobile_number, description="POS Payment"
		)

		return response

	except Exception:
		frappe.log_error(title=_("Mpesa Express Transaction Error"))
		frappe.throw(_("Issue detected with Mpesa configuration, check the error logs for more details"), title=_("Mpesa Express Error"))

def sanitize_mobile_number(number):
	"""Add country code and strip leading zeroes from the phone number."""
	return "254" + str(number).lstrip("0")

@frappe.whitelist(allow_guest=True)
def verify_transaction(**kwargs):
	"""Verify the transaction result received via callback from stk."""
	transaction_response = frappe._dict(kwargs["Body"]["stkCallback"])

	checkout_id = getattr(transaction_response, "CheckoutRequestID", "")
	integration_request = frappe.get_doc("Integration Request", checkout_id)
	transaction_data = frappe._dict(loads(integration_request.data))
	total_paid = 0 # for multiple integration request made against a pos invoice
	success = False # for reporting successfull callback to point of sale ui

	if transaction_response['ResultCode'] == 0:
		if integration_request.reference_doctype and integration_request.reference_docname:
			try:
				item_response = transaction_response["CallbackMetadata"]["Item"]
				amount = fetch_param_value(item_response, "Amount", "Name")
				mpesa_receipt = fetch_param_value(item_response, "MpesaReceiptNumber", "Name")
				pr = frappe.get_doc(integration_request.reference_doctype, integration_request.reference_docname)

				mpesa_receipts, completed_payments = get_completed_integration_requests_info(
					integration_request.reference_doctype,
					integration_request.reference_docname,
					checkout_id
				)

				total_paid = amount + sum(completed_payments)
				mpesa_receipts = ', '.join(mpesa_receipts + [mpesa_receipt])

				if total_paid >= pr.grand_total:
					pr.run_method("on_payment_authorized", 'Completed')
					success = True

				frappe.db.set_value("POS Invoice", pr.reference_name, "mpesa_receipt_number", mpesa_receipts)
				integration_request.handle_success(transaction_response)
			except Exception:
				integration_request.handle_failure(transaction_response)
				frappe.log_error(frappe.get_traceback())

	else:
		integration_request.handle_failure(transaction_response)

	frappe.publish_realtime(
		event='process_phone_payment',
		doctype="POS Invoice",
		docname=transaction_data.payment_reference,
		user=integration_request.owner,
		message={
			'amount': total_paid,
			'success': success,
			'failure_message': transaction_response["ResultDesc"] if transaction_response['ResultCode'] != 0 else ''
		},
	)

def get_completed_integration_requests_info(reference_doctype, reference_docname, checkout_id):
	output_of_other_completed_requests = frappe.get_all("Integration Request", filters={
		'name': ['!=', checkout_id],
		'reference_doctype': reference_doctype,
		'reference_docname': reference_docname,
		'status': 'Completed'
	}, pluck="output")

	mpesa_receipts, completed_payments = [], []

	for out in output_of_other_completed_requests:
		out = frappe._dict(loads(out))
		item_response = out["CallbackMetadata"]["Item"]
		completed_amount = fetch_param_value(item_response, "Amount", "Name")
		completed_mpesa_receipt = fetch_param_value(item_response, "MpesaReceiptNumber", "Name")
		completed_payments.append(completed_amount)
		mpesa_receipts.append(completed_mpesa_receipt)

	return mpesa_receipts, completed_payments

def get_account_balance(request_payload):
	"""Call account balance API to send the request to the Mpesa Servers."""
	try:
		mpesa_settings = frappe.get_doc("Mpesa Settings", request_payload.get("reference_docname"))
		env = "production" if not mpesa_settings.sandbox else "sandbox"
		connector = MpesaConnector(env=env,
			app_key=mpesa_settings.consumer_key,
			app_secret=mpesa_settings.get_password("consumer_secret"))

		callback_url = get_request_site_address(True) + "/api/method/erpnext.erpnext_integrations.doctype.mpesa_settings.mpesa_settings.process_balance_info"

		response = connector.get_balance(mpesa_settings.initiator_name, mpesa_settings.security_credential, mpesa_settings.till_number, 4, mpesa_settings.name, callback_url, callback_url)
		return response
	except Exception:
		frappe.log_error(title=_("Account Balance Processing Error"))
		frappe.throw(_("Please check your configuration and try again"), title=_("Error"))

@frappe.whitelist(allow_guest=True)
def process_balance_info(**kwargs):
	"""Process and store account balance information received via callback from the account balance API call."""
	account_balance_response = frappe._dict(kwargs["Result"])

	conversation_id = getattr(account_balance_response, "ConversationID", "")
	request = frappe.get_doc("Integration Request", conversation_id)

	if request.status == "Completed":
		return

	transaction_data = frappe._dict(loads(request.data))

	if account_balance_response["ResultCode"] == 0:
		try:
			result_params = account_balance_response["ResultParameters"]["ResultParameter"]

			balance_info = fetch_param_value(result_params, "AccountBalance", "Key")
			balance_info = format_string_to_json(balance_info)

			ref_doc = frappe.get_doc(transaction_data.reference_doctype, transaction_data.reference_docname)
			ref_doc.db_set("account_balance", balance_info)

			request.handle_success(account_balance_response)
			frappe.publish_realtime("refresh_mpesa_dashboard", doctype="Mpesa Settings",
				docname=transaction_data.reference_docname, user=transaction_data.owner)
		except Exception:
			request.handle_failure(account_balance_response)
			frappe.log_error(title=_("Mpesa Account Balance Processing Error"), message=account_balance_response)
	else:
		request.handle_failure(account_balance_response)

def format_string_to_json(balance_info):
	"""
	Format string to json.

	e.g: '''Working Account|KES|481000.00|481000.00|0.00|0.00'''
	=> {'Working Account': {'current_balance': '481000.00',
		'available_balance': '481000.00',
		'reserved_balance': '0.00',
		'uncleared_balance': '0.00'}}
	"""
	balance_dict = frappe._dict()
	for account_info in balance_info.split("&"):
		account_info = account_info.split('|')
		balance_dict[account_info[0]] = dict(
			current_balance=fmt_money(account_info[2], currency="KES"),
			available_balance=fmt_money(account_info[3], currency="KES"),
			reserved_balance=fmt_money(account_info[4], currency="KES"),
			uncleared_balance=fmt_money(account_info[5], currency="KES")
		)
	return dumps(balance_dict)

def fetch_param_value(response, key, key_field):
	"""Fetch the specified key from list of dictionary. Key is identified via the key field."""
	for param in response:
		if param[key_field] == key:
			return param["Value"]