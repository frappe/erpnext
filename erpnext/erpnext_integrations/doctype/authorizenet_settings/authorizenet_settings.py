# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
# Integrating Authorizenet

### 1. Validate Currency Support

Example:

	controller().validate_transaction_currency(currency)

### 2. Redirect for payment

Example:

	payment_details = {
		"createTransactionRequest": {
			"merchantAuthentication": {
				"name": "xxxxxxxxxx",
				"transactionKey": "xxxxxxxxxxxx"
			},
			"refId": "123456",
			"transactionRequest": {
				"transactionType": "authCaptureTransaction",
				"amount": "5",
				"payment": {
					"credit_card": {
						"card_number": "XXXX-XXXX-XXXX-XXXX",
						"expiration_date": "YYYY-MM",
						"card_code": "XXX"
					}
				},
				"lineItems": {
					"lineItem": {
						"itemId": "1",
						"name": "vase",
						"description": "Cannes logo",
						"quantity": "18",
						"unitPrice": "45.00"
					}
				}
			}
		}
	}

	# redirect the user to this url
	url = controller().get_payment_url(**payment_details)

### 3. On Completion of Payment

Return payment status after processing the payment

"""
from __future__ import unicode_literals

import imp
import json
import os
import re
import sys

from authorizenet import apicontractsv1
from authorizenet.apicontrollers import createTransactionController
from six.moves.urllib.parse import urlencode

import frappe
from frappe.integrations.utils import create_payment_gateway, create_request_log
from frappe.model.document import Document
from frappe.utils import call_hook_method, cstr, get_url
from frappe.utils.password import get_decrypted_password


class AuthorizenetSettings(Document):
	supported_currencies = ["USD", "CAD"]

	def validate_transaction_currency(self, currency):
		if currency not in self.supported_currencies:
			frappe.throw(_("Please select another payment method. Authorizenet does not support transactions in currency '{0}'").format(currency))

	def validate(self):
		create_payment_gateway('Authorizenet')
		call_hook_method('payment_gateway_enabled', gateway="Authorizenet")

	def get_payment_url(self, **kwargs):
		return get_url("./integrations/authorizenet_checkout?{0}".format(urlencode(kwargs)))


@frappe.whitelist()
def charge_credit_card(data, card_number, expiration_date, card_code):
	"""
	Charge a credit card
	"""
	data = json.loads(data)
	data = frappe._dict(data)

	# Create Integration Request
	integration_request = create_request_log(data, "Host", "Authorizenet")

	# Authenticate with Authorizenet
	merchant_auth = apicontractsv1.merchantAuthenticationType()
	merchant_auth.name = frappe.db.get_single_value("Authorizenet Settings", "api_login_id")
	merchant_auth.transactionKey = get_decrypted_password('Authorizenet Settings', 'Authorizenet Settings', fieldname='api_transaction_key', raise_exception=False)

	# Create the payment data for a credit card
	credit_card = apicontractsv1.creditCardType()
	credit_card.cardNumber = card_number
	credit_card.expirationDate = expiration_date
	credit_card.cardCode = card_code

	# Add the payment data to a paymentType object
	payment = apicontractsv1.paymentType()
	payment.creditCard = credit_card

	pr = frappe.get_doc(data.reference_doctype, data.reference_docname)
	reference_doc = frappe.get_doc(pr.reference_doctype, pr.reference_name).as_dict()

	customer_address = apicontractsv1.customerAddressType()
	customer_address.firstName = data.payer_name
	customer_address.email = data.payer_email
	customer_address.address = reference_doc.customer_address[:60]

	# Create order information
	order = apicontractsv1.orderType()
	order.invoiceNumber = reference_doc.name

	# build the array of line items
	line_items = apicontractsv1.ArrayOfLineItem()

	for item in reference_doc.get("items"):
		# setup individual line items
		line_item = apicontractsv1.lineItemType()
		line_item.itemId = item.item_code
		line_item.name = item.item_name[:30]
		line_item.description = item.item_name
		line_item.quantity = item.qty
		line_item.unitPrice = cstr(item.rate)

		line_items.lineItem.append(line_item)

	# Create a transactionRequestType object and add the previous objects to it.
	transaction_request = apicontractsv1.transactionRequestType()
	transaction_request.transactionType = "authCaptureTransaction"
	transaction_request.amount = data.amount
	transaction_request.payment = payment
	transaction_request.order = order
	transaction_request.billTo = customer_address
	transaction_request.lineItems = line_items

	# Assemble the complete transaction request
	create_transaction_request = apicontractsv1.createTransactionRequest()
	create_transaction_request.merchantAuthentication = merchant_auth
	create_transaction_request.transactionRequest = transaction_request

	# Create the controller
	createtransactioncontroller = createTransactionController(
		create_transaction_request)
	createtransactioncontroller.execute()

	response = createtransactioncontroller.getresponse()

	status = "Failed"

	if response is not None:
		# Check to see if the API request was successfully received and acted upon
		if response.messages.resultCode == "Ok" and hasattr(response.transactionResponse, 'messages') is True:
			status = "Completed"

	if status != "Failed":
		try:
			pr.run_method("on_payment_authorized", status)
		except Exception as ex:
			raise ex

	response_dict = to_dict(response)

	integration_request.update_status(data, status)

	if status == "Completed":
		description = response_dict.get("transactionResponse").get("messages").get("message").get("description")
	elif status == "Failed":
		description = error_text = response_dict.get("transactionResponse").get("errors").get("error").get("errorText")
		integration_request.error = error_text
		integration_request.save(ignore_permissions=True)

	return frappe._dict({
		"status": status,
		"description" : description
	})

def to_dict(response):
	response_dict = {}
	if response.getchildren() == []:
		return response.text
	else:
		for elem in response.getchildren():
			subdict = to_dict(elem)
			response_dict[re.sub('{.*}', '', elem.tag)] = subdict
	return response_dict
