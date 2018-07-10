# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from requests_oauthlib import OAuth2Session

client_id = "Q02P61JeL3TNEr5HjcWTrXB9bQEab6LhoPaGg3uF2RQ1iKG6nL"
client_secret = "B1se8GzM4FvfNAbeRjZGF5q2BNyRcV4O2V4fb0ZQ"
scope = "com.intuit.quickbooks.accounting"
redirect_uri = "http://localhost/api/method/erpnext.erpnext_integrations.doctype.quickbooks_connector.quickbooks_connector.callback"

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

authorization_endpoint = "https://appcenter.intuit.com/connect/oauth2"

@frappe.whitelist(allow_guest=True)
def callback(*args, **kwargs):
	print("*"*50)
	print(args, kwargs)
	frappe.respond_as_web_page("Quickbooks Authentication", html="<script>window.close()</script>")

@frappe.whitelist()
def get_authorization_url():
	return oauth.authorization_url(authorization_endpoint)[0]

token_endpoint = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

class QuickBooksConnector(Document):
	pass
