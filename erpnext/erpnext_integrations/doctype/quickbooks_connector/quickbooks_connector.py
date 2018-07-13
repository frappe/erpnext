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
	print("Enqueing Customer Fetch Job")
	frappe.enqueue("erpnext.erpnext_integrations.doctype.quickbooks_connector.quickbooks_connector.fetch_and_save_customer", token=token, company_id=company_id, customer_id=63)

token_endpoint = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
def get_access_token(code):
	token = oauth.fetch_token(token_endpoint, client_secret=client_secret, code=code)["access_token"]
	return token

BASE_URL = "https://sandbox-quickbooks.api.intuit.com/v3/company/{}/{}/{}"
def fetch_and_save_customer(token="", company_id=1, customer_id=1):
	customer_uri = BASE_URL.format(company_id, "customer", customer_id)
	customer = requests.get(customer_uri, headers=get_headers(token)).json()["Customer"]
	erpcustomer = frappe.get_doc({
		"doctype": "Customer",
		"customer_name" : customer["DisplayName"],
		"customer_type" : _("Individual"),
		"customer_group" : _("Commercial"),
		"territory" : _("All Territories"),
	}).insert(ignore_permissions=True)

def get_headers(token):
	return {"Accept": "application/json",
	"Authorization": "Bearer {}".format(token)}

class QuickBooksConnector(Document):
	pass
