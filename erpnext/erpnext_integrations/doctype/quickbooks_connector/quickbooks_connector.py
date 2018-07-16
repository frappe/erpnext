# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from requests_oauthlib import OAuth2Session
import requests

client_id = "Q02P61JeL3TNEr5HjcWTrXB9bQEab6LhoPaGg3uF2RQ1iKG6nL"
client_secret = "B1se8GzM4FvfNAbeRjZGF5q2BNyRcV4O2V4fb0ZQ"
scope = "com.intuit.quickbooks.accounting"
redirect_uri = "http://localhost/api/method/erpnext.erpnext_integrations.doctype.quickbooks_connector.quickbooks_connector.callback"

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

authorization_endpoint = "https://appcenter.intuit.com/connect/oauth2"
@frappe.whitelist()
def get_authorization_url():
	return oauth.authorization_url(authorization_endpoint)[0]

@frappe.whitelist(allow_guest=True)
def callback(*args, **kwargs):
	frappe.respond_as_web_page("Quickbooks Authentication", html="<script>window.close()</script>")
	code = kwargs.get("code")
	company_id = kwargs.get("realmId")
	token = get_access_token(code)
	print("Enqueing Customer Bulk Fetch Job")
	frappe.enqueue("erpnext.erpnext_integrations.doctype.quickbooks_connector.quickbooks_connector.fetch_all_customers", token=token, company_id=company_id)

token_endpoint = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
def get_access_token(code):
	token = oauth.fetch_token(token_endpoint, client_secret=client_secret, code=code)["access_token"]
	return token

BASE_URL = "https://sandbox-quickbooks.api.intuit.com/v3/company/{}/{}/{}"
def save_customers(customers):
	for customer in customers:
		erpcustomer = frappe.get_doc({
			"doctype": "Customer",
			"customer_name" : customer["DisplayName"],
			"customer_type" : _("Individual"),
			"customer_group" : _("Commercial"),
			"territory" : _("All Territories"),
		}).insert(ignore_permissions=True)

# A quickbooks api contraint
MAX_RESULT_COUNT = 10
BASE_QUERY_URL = "https://sandbox-quickbooks.api.intuit.com/v3/company/{}/{}"

def fetch_all_customers(token="", company_id=1):
	make_custom_quickbooksid_field()
	query_uri = BASE_QUERY_URL.format(company_id, "query")

	# Count number of customers
	customer_query_response = requests.get(query_uri,
		params={
			"query": """SELECT COUNT(*) FROM Customer"""
		},
		headers=get_headers(token)
	).json()
	customer_count = customer_query_response["QueryResponse"]["totalCount"]

	# fetch pages and accumulate
	customers = []
	for start_position in range(1, customer_count + 1, MAX_RESULT_COUNT):
		response = requests.get(query_uri,
			params={
				"query": """SELECT * FROM Customer STARTPOSITION {} MAXRESULTS {}""".format(start_position, MAX_RESULT_COUNT)
			},
			headers=get_headers(token)
		).json()["QueryResponse"]["Customer"]
		customers.extend(response)
	save_customers(customers)

def make_custom_quickbooksid_field():
	if frappe.get_meta("Customer").has_field("quickbooks_id"):
		return
	frappe.get_doc({
		"doctype": "Custom Field",
		"label": "QuickBooks ID",
		"dt": "Customer",
		"fieldname": "quickbooks_id",
		"fieldtype": "Data",
		"unique": True
	}).insert(ignore_permissions=True)

def get_headers(token):
	return {"Accept": "application/json",
	"Authorization": "Bearer {}".format(token)}

class QuickBooksConnector(Document):
	pass
