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

@frappe.whitelist()
def callback(*args, **kwargs):
	frappe.respond_as_web_page("Quickbooks Authentication", html="<script>window.close()</script>")
	code = kwargs.get("code")
	company_id = kwargs.get("realmId")
	token = get_access_token(code)
	fetch_method = "erpnext.erpnext_integrations.doctype.quickbooks_connector.quickbooks_connector.fetch_all_entries"
	make_custom_fields()
	relevant_doctypes = ["Customer", "Item"]
	for doctype in relevant_doctypes:
		frappe.enqueue(fetch_method, doctype=doctype, token=token, company_id=company_id)

token_endpoint = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
def get_access_token(code):
	token = oauth.fetch_token(token_endpoint, client_secret=client_secret, code=code)["access_token"]
	return token

def save_customer(customer):
	erpcustomer = frappe.get_doc({
		"doctype": "Customer",
		"quickbooks_id": customer["Id"],
		"customer_name" : customer["DisplayName"],
		"customer_type" : _("Individual"),
		"customer_group" : _("Commercial"),
		"territory" : _("All Territories"),
	}).insert(ignore_permissions=True)
	if "BillAddr" in customer:
		create_customer_address(erpcustomer, customer["BillAddr"], "Billing")
	if "ShipAddr" in customer:
		create_customer_address(erpcustomer, customer["ShipAddr"], "Shipping")

def save_item(item):
	frappe.get_doc({
		"doctype": "Item",
		"quickbooks_id": item["Id"],
		"item_code" : item["Name"],
		"stock_uom": "Unit",
		"item_group": "All Item Groups",
		"item_defaults": [{"company": "Sandbox Actual"}]
	}).insert(ignore_permissions=True)

def create_customer_address(customer, address, address_type):
	try :
		frappe.get_doc({
			"doctype": "Address",
			"quickbooks_address_id": address["Id"],
			"address_title": customer.name,
			"address_type": address_type,
			"address_line1": address["Line1"],
			"city": address["City"],
			"gst_state": "Maharashtra",
			"links": [{"link_doctype": "Customer", "link_name": customer.name}]
		}).insert()
	except:
		print("couldn't create address")



def make_custom_fields():
	relevant_doctypes = ["Customer", "Address", "Item"]
	for doctype in relevant_doctypes:
		make_custom_quickbooks_id_field(doctype)

def make_custom_quickbooks_id_field(doctype):
	if not frappe.get_meta(doctype).has_field("quickbooks_id"):
		frappe.get_doc({
			"doctype": "Custom Field",
			"label": "QuickBooks ID",
			"dt": doctype,
			"fieldname": "quickbooks_id",
			"fieldtype": "Data",
			"unique": True
		}).insert(ignore_permissions=True)

save_methods = {
	"Customer": save_customer,
	"Item": save_item
}

def save_entries(doctype, entries):
	save = save_methods[doctype]
	for entry in entries:
		try:
			save(entry)
		except:
			import traceback
			traceback.print_exc()

# A quickbooks api contraint
MAX_RESULT_COUNT = 10
BASE_QUERY_URL = "https://sandbox-quickbooks.api.intuit.com/v3/company/{}/{}"
qb_map = {
	"Customer": "Customer",
	"Item": "Item",
}

def fetch_all_entries(doctype="", token="", company_id=1):
	query_uri = BASE_QUERY_URL.format(company_id, "query")

	# Count number of entries
	entry_count = requests.get(query_uri,
		params={
			"query": """SELECT COUNT(*) FROM {}""".format(qb_map[doctype])
		},
		headers=get_headers(token)
	).json()["QueryResponse"]["totalCount"]

	# fetch pages and accumulate
	entries = []
	for start_position in range(1, entry_count + 1, MAX_RESULT_COUNT):
		response = requests.get(query_uri,
			params={
				"query": """SELECT * FROM {} STARTPOSITION {} MAXRESULTS {}""".format(qb_map[doctype], start_position, MAX_RESULT_COUNT)
			},
			headers=get_headers(token)
		).json()["QueryResponse"][qb_map[doctype]]
		entries.extend(response)
	save_entries(doctype, entries)

def get_headers(token):
	return {"Accept": "application/json",
	"Authorization": "Bearer {}".format(token)}

class QuickBooksConnector(Document):
	pass
