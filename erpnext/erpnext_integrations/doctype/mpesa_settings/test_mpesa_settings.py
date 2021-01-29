# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
from json import dumps
import frappe
import unittest
from erpnext.erpnext_integrations.doctype.mpesa_settings.mpesa_settings import process_balance_info, verify_transaction
from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice

class TestMpesaSettings(unittest.TestCase):
	def tearDown(self):
		frappe.db.sql('delete from `tabMpesa Settings`')
		frappe.db.sql('delete from `tabIntegration Request` where integration_request_service = "Mpesa"')

	def test_creation_of_payment_gateway(self):
		create_mpesa_settings(payment_gateway_name="_Test")

		mode_of_payment = frappe.get_doc("Mode of Payment", "Mpesa-_Test")
		self.assertTrue(frappe.db.exists("Payment Gateway Account", {'payment_gateway': "Mpesa-_Test"}))
		self.assertTrue(mode_of_payment.name)
		self.assertEquals(mode_of_payment.type, "Phone")

	def test_processing_of_account_balance(self):
		mpesa_doc = create_mpesa_settings(payment_gateway_name="_Account Balance")
		mpesa_doc.get_account_balance_info()

		callback_response = get_account_balance_callback_payload()
		process_balance_info(**callback_response)
		integration_request = frappe.get_doc("Integration Request", "AG_20200927_00007cdb1f9fb6494315")

		# test integration request creation and successful update of the status on receiving callback response
		self.assertTrue(integration_request)
		self.assertEquals(integration_request.status, "Completed")

		# test formatting of account balance received as string to json with appropriate currency symbol
		mpesa_doc.reload()
		self.assertEquals(mpesa_doc.account_balance, dumps({
			"Working Account": {
				"current_balance": "Sh 481,000.00",
				"available_balance": "Sh 481,000.00",
				"reserved_balance": "Sh 0.00",
				"uncleared_balance": "Sh 0.00"
			}
		}))

		integration_request.delete()

	def test_processing_of_callback_payload(self):
		create_mpesa_settings(payment_gateway_name="Payment")
		mpesa_account = frappe.db.get_value("Payment Gateway Account", {"payment_gateway": 'Mpesa-Payment'}, "payment_account")
		frappe.db.set_value("Account", mpesa_account, "account_currency", "KES")
		frappe.db.set_value("Customer", "_Test Customer", "default_currency", "KES")

		pos_invoice = create_pos_invoice(do_not_submit=1)
		pos_invoice.append("payments", {'mode_of_payment': 'Mpesa-Payment', 'account': mpesa_account, 'amount': 500})
		pos_invoice.contact_mobile = "093456543894"
		pos_invoice.currency = "KES"
		pos_invoice.save()

		pr = pos_invoice.create_payment_request()
		# test payment request creation
		self.assertEquals(pr.payment_gateway, "Mpesa-Payment")

		# submitting payment request creates integration requests with random id
		integration_req_ids = frappe.get_all("Integration Request", filters={
			'reference_doctype': pr.doctype,
			'reference_docname': pr.name,
		}, pluck="name")

		callback_response = get_payment_callback_payload(Amount=500, CheckoutRequestID=integration_req_ids[0])
		verify_transaction(**callback_response)
		# test creation of integration request
		integration_request = frappe.get_doc("Integration Request", integration_req_ids[0])

		# test integration request creation and successful update of the status on receiving callback response
		self.assertTrue(integration_request)
		self.assertEquals(integration_request.status, "Completed")

		pos_invoice.reload()
		integration_request.reload()
		self.assertEquals(pos_invoice.mpesa_receipt_number, "LGR7OWQX0R")
		self.assertEquals(integration_request.status, "Completed")
		
		frappe.db.set_value("Customer", "_Test Customer", "default_currency", "")
		integration_request.delete()
		pr.reload()
		pr.cancel()
		pr.delete()
		pos_invoice.delete()

	def test_processing_of_multiple_callback_payload(self):
		create_mpesa_settings(payment_gateway_name="Payment")
		mpesa_account = frappe.db.get_value("Payment Gateway Account", {"payment_gateway": 'Mpesa-Payment'}, "payment_account")
		frappe.db.set_value("Account", mpesa_account, "account_currency", "KES")
		frappe.db.set_value("Mpesa Settings", "Payment", "transaction_limit", "500")
		frappe.db.set_value("Customer", "_Test Customer", "default_currency", "KES")

		pos_invoice = create_pos_invoice(do_not_submit=1)
		pos_invoice.append("payments", {'mode_of_payment': 'Mpesa-Payment', 'account': mpesa_account, 'amount': 1000})
		pos_invoice.contact_mobile = "093456543894"
		pos_invoice.currency = "KES"
		pos_invoice.save()

		pr = pos_invoice.create_payment_request()
		# test payment request creation
		self.assertEquals(pr.payment_gateway, "Mpesa-Payment")

		# submitting payment request creates integration requests with random id
		integration_req_ids = frappe.get_all("Integration Request", filters={
			'reference_doctype': pr.doctype,
			'reference_docname': pr.name,
		}, pluck="name")

		# create random receipt nos and send it as response to callback handler
		mpesa_receipt_numbers = [frappe.utils.random_string(5) for d in integration_req_ids]

		integration_requests = []
		for i in range(len(integration_req_ids)):
			callback_response = get_payment_callback_payload(
				Amount=500,
				CheckoutRequestID=integration_req_ids[i],
				MpesaReceiptNumber=mpesa_receipt_numbers[i]
			)
			# handle response manually
			verify_transaction(**callback_response)
			# test completion of integration request
			integration_request = frappe.get_doc("Integration Request", integration_req_ids[i])
			self.assertEquals(integration_request.status, "Completed")
			integration_requests.append(integration_request)

		# check receipt number once all the integration requests are completed
		pos_invoice.reload()
		self.assertEquals(pos_invoice.mpesa_receipt_number, ', '.join(mpesa_receipt_numbers))

		frappe.db.set_value("Customer", "_Test Customer", "default_currency", "")
		[d.delete() for d in integration_requests]
		pr.reload()
		pr.cancel()
		pr.delete()
		pos_invoice.delete()
	
	def test_processing_of_only_one_succes_callback_payload(self):
		create_mpesa_settings(payment_gateway_name="Payment")
		mpesa_account = frappe.db.get_value("Payment Gateway Account", {"payment_gateway": 'Mpesa-Payment'}, "payment_account")
		frappe.db.set_value("Account", mpesa_account, "account_currency", "KES")
		frappe.db.set_value("Mpesa Settings", "Payment", "transaction_limit", "500")
		frappe.db.set_value("Customer", "_Test Customer", "default_currency", "KES")

		pos_invoice = create_pos_invoice(do_not_submit=1)
		pos_invoice.append("payments", {'mode_of_payment': 'Mpesa-Payment', 'account': mpesa_account, 'amount': 1000})
		pos_invoice.contact_mobile = "093456543894"
		pos_invoice.currency = "KES"
		pos_invoice.save()

		pr = pos_invoice.create_payment_request()
		# test payment request creation
		self.assertEquals(pr.payment_gateway, "Mpesa-Payment")

		# submitting payment request creates integration requests with random id
		integration_req_ids = frappe.get_all("Integration Request", filters={
			'reference_doctype': pr.doctype,
			'reference_docname': pr.name,
		}, pluck="name")

		# create random receipt nos and send it as response to callback handler
		mpesa_receipt_numbers = [frappe.utils.random_string(5) for d in integration_req_ids]

		callback_response = get_payment_callback_payload(
			Amount=500,
			CheckoutRequestID=integration_req_ids[0],
			MpesaReceiptNumber=mpesa_receipt_numbers[0]
		)
		# handle response manually
		verify_transaction(**callback_response)
		# test completion of integration request
		integration_request = frappe.get_doc("Integration Request", integration_req_ids[0])
		self.assertEquals(integration_request.status, "Completed")

		# now one request is completed
		# second integration request fails
		# now retrying payment request should make only one integration request again
		pr = pos_invoice.create_payment_request()
		new_integration_req_ids = frappe.get_all("Integration Request", filters={
			'reference_doctype': pr.doctype,
			'reference_docname': pr.name,
			'name': ['not in', integration_req_ids]
		}, pluck="name")

		self.assertEquals(len(new_integration_req_ids), 1)

		frappe.db.set_value("Customer", "_Test Customer", "default_currency", "")
		frappe.db.sql("delete from `tabIntegration Request` where integration_request_service = 'Mpesa'")
		pr.reload()
		pr.cancel()
		pr.delete()
		pos_invoice.delete()

def create_mpesa_settings(payment_gateway_name="Express"):
	if frappe.db.exists("Mpesa Settings", payment_gateway_name):
		return frappe.get_doc("Mpesa Settings", payment_gateway_name)

	doc = frappe.get_doc(dict( #nosec
		doctype="Mpesa Settings",
		payment_gateway_name=payment_gateway_name,
		consumer_key="5sMu9LVI1oS3oBGPJfh3JyvLHwZOdTKn",
		consumer_secret="VI1oS3oBGPJfh3JyvLHw",
		online_passkey="LVI1oS3oBGPJfh3JyvLHwZOd",
		till_number="174379"
	))

	doc.insert(ignore_permissions=True)
	return doc

def get_test_account_balance_response():
	"""Response received after calling the account balance API."""
	return {
		"ResultType":0,
		"ResultCode":0,
		"ResultDesc":"The service request has been accepted successfully.",
		"OriginatorConversationID":"10816-694520-2",
		"ConversationID":"AG_20200927_00007cdb1f9fb6494315",
		"TransactionID":"LGR0000000",
		"ResultParameters":{
		"ResultParameter":[
			{
			"Key":"ReceiptNo",
			"Value":"LGR919G2AV"
			},
			{
			"Key":"Conversation ID",
			"Value":"AG_20170727_00004492b1b6d0078fbe"
			},
			{
			"Key":"FinalisedTime",
			"Value":20170727101415
			},
			{
			"Key":"Amount",
			"Value":10
			},
			{
			"Key":"TransactionStatus",
			"Value":"Completed"
			},
			{
			"Key":"ReasonType",
			"Value":"Salary Payment via API"
			},
			{
			"Key":"TransactionReason"
			},
			{
			"Key":"DebitPartyCharges",
			"Value":"Fee For B2C Payment|KES|33.00"
			},
			{
			"Key":"DebitAccountType",
			"Value":"Utility Account"
			},
			{
			"Key":"InitiatedTime",
			"Value":20170727101415
			},
			{
			"Key":"Originator Conversation ID",
			"Value":"19455-773836-1"
			},
			{
			"Key":"CreditPartyName",
			"Value":"254708374149 - John Doe"
			},
			{
			"Key":"DebitPartyName",
			"Value":"600134 - Safaricom157"
			}
		]
	},
	"ReferenceData":{
	"ReferenceItem":{
		"Key":"Occasion",
		"Value":"aaaa"
	}
	}
		}

def get_payment_request_response_payload(Amount=500):
	"""Response received after successfully calling the stk push process request API."""

	CheckoutRequestID = frappe.utils.random_string(10)

	return {
		"MerchantRequestID": "8071-27184008-1",
		"CheckoutRequestID": CheckoutRequestID,
		"ResultCode": 0,
		"ResultDesc": "The service request is processed successfully.",
		"CallbackMetadata": {
			"Item": [
				{ "Name": "Amount", "Value": Amount },
				{ "Name": "MpesaReceiptNumber", "Value": "LGR7OWQX0R" },
				{ "Name": "TransactionDate", "Value": 20201006113336 },
				{ "Name": "PhoneNumber", "Value": 254723575670 }
			]
		}
	}

def get_payment_callback_payload(Amount=500, CheckoutRequestID="ws_CO_061020201133231972", MpesaReceiptNumber="LGR7OWQX0R"):
	"""Response received from the server as callback after calling the stkpush process request API."""
	return {
		"Body":{
			"stkCallback":{
				"MerchantRequestID":"19465-780693-1",
				"CheckoutRequestID":CheckoutRequestID,
				"ResultCode":0,
				"ResultDesc":"The service request is processed successfully.",
				"CallbackMetadata":{
					"Item":[
						{ "Name":"Amount", "Value":Amount },
						{ "Name":"MpesaReceiptNumber", "Value":MpesaReceiptNumber },
						{ "Name":"Balance" },
						{ "Name":"TransactionDate", "Value":20170727154800 },
						{ "Name":"PhoneNumber", "Value":254721566839 }
					]
				}
			}
		}
	}

def get_account_balance_callback_payload():
	"""Response received from the server as callback after calling the account balance API."""
	return {
		"Result":{
			"ResultType": 0,
			"ResultCode": 0,
			"ResultDesc": "The service request is processed successfully.",
			"OriginatorConversationID": "16470-170099139-1",
			"ConversationID": "AG_20200927_00007cdb1f9fb6494315",
			"TransactionID": "OIR0000000",
			"ResultParameters": {
				"ResultParameter": [
					{
						"Key": "AccountBalance",
						"Value": "Working Account|KES|481000.00|481000.00|0.00|0.00"
					},
					{ "Key": "BOCompletedTime", "Value": 20200927234123 }
				]
			},
			"ReferenceData": {
				"ReferenceItem": {
					"Key": "QueueTimeoutURL",
					"Value": "https://internalsandbox.safaricom.co.ke/mpesa/abresults/v1/submit"
				}
			}
		}
	}