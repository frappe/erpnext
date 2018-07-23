# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from requests_oauthlib import OAuth2Session
import requests
from erpnext import encode_company_abbr

client_id = "Q02P61JeL3TNEr5HjcWTrXB9bQEab6LhoPaGg3uF2RQ1iKG6nL"
client_secret = "B1se8GzM4FvfNAbeRjZGF5q2BNyRcV4O2V4fb0ZQ"
scope = "com.intuit.quickbooks.accounting"
redirect_uri = "http://localhost/api/method/erpnext.erpnext_integrations.doctype.quickbooks_connector.quickbooks_connector.callback"

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

authorization_endpoint = "https://appcenter.intuit.com/connect/oauth2"
@frappe.whitelist()
def get_authorization_url():
	return oauth.authorization_url(authorization_endpoint)[0]


"""
from frappe import delete_doc
from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import get_account_tree_from_existing_company
from frappe.model.rename_doc import get_link_fields

def delete_compnay_default_accounts(company):
	company = frappe.get_doc("Company", company)

	account_fields = list(filter(lambda x: x['parent'] == "Company", get_link_fields("Account")
	account_fields = [_["fieldname"] for _ in account_fields]
	print(account_fields)
	print(company.__dict__)
	for field in account_fields:
		frappe.db.set_value("Company", company.name, field, None)
	for field in company.__dict__.keys():
		if "account" in field:
			frappe.db.set_value("Company", company.name, field, None)
	frappe.db.commit()
	company = frappe.get_doc("Company", company.name)
	print(company.__dict__)

def traverse(tree):
	global traverse
	children = list(filter(lambda x: x not in ("root_type", "account_type", "is_group", "account_number"), tree.keys()))
	print(children)
	for child in children:
		traverse(tree[child])
		print("Going to delete now", encode_company_abbr(child, "Sandbox Actual"))
		delete_doc("Account", encode_company_abbr(child, "Sandbox Actual"))

delete_compnay_default_accounts("Sandbox Actual")
traverse(get_account_tree_from_existing_company("Sandbox Actual"))
"""

@frappe.whitelist()
def callback(*args, **kwargs):
	frappe.respond_as_web_page("Quickbooks Authentication", html="<script>window.close()</script>")
	code = kwargs.get("code")
	company_id = kwargs.get("realmId")
	token = get_access_token(code)
	fetch_method = "erpnext.erpnext_integrations.doctype.quickbooks_connector.quickbooks_connector.fetch_all_entries"
	make_custom_fields()
	print("Mkaing roots")
	make_root_accounts()
	print("Made roots")
	relevant_doctypes = ["Account", "Customer", "Item", "Supplier", "Sales Invoice"]
	for doctype in relevant_doctypes:
		frappe.enqueue(fetch_method, doctype=doctype, token=token, company_id=company_id)

token_endpoint = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
def get_access_token(code):
	token = oauth.fetch_token(token_endpoint, client_secret=client_secret, code=code)["access_token"]
	return token

def make_root_accounts():
	roots = ["Asset", "Equity", "Expense", "Liability", "Income"]
	for root in roots:
		print("trying", root)
		try:
			if not frappe.db.exists("Account", encode_company_abbr("{} - QB".format(root), "Sandbox Actual")):
				frappe.get_doc({
					"doctype": "Account",
					"account_name": "{} - QB".format(root),
					"root_type": root,
					"is_group": "1",
					"company": "Sandbox Actual",
				}).insert(ignore_permissions=True, ignore_mandatory=True)
				print("Inserted", root)
		except:
			import traceback
			traceback.print_exc()
	frappe.db.commit()

mapping = {
	"Bank": "Asset",
	"Other Current Asset": "Asset",
	"Fixed Asset": "Asset",
	"Other Asset": "Asset",
	"Accounts Receivable": "Asset",

	"Equity": "Equity",

	"Expense": "Expense",
	"Other Expense": "Expense",
	"Cost of Goods Sold": "Expense",

	"Accounts Payable": "Liability",
	"Credit Card": "Liability",
	"Long Term Liability": "Liability",
	"Other Current Liability": "Liability",

	"Income": "Income",
	"Other Income": "Income",
}

def save_account(account):
	# Map Quickbooks Account Types to ERPNext root_accunts and and root_type
	try:
		frappe.get_doc({
			"doctype": "Account",
			"quickbooks_id": account["Id"],
			"account_name": "{} - QB".format(account["Name"]),
			"root_type": mapping[account["AccountType"]],
			"parent_account": encode_company_abbr("{} - QB".format(mapping[account["AccountType"]]), "Sandbox Actual"),
			"is_group": "0",
			"company": "Sandbox Actual",
		}).insert(ignore_permissions=True, ignore_mandatory=True)
	except:
		pass

def save_customer(customer):
	try:
		erpcustomer = frappe.get_doc({
			"doctype": "Customer",
			"quickbooks_id": customer["Id"],
			"customer_name" : customer["DisplayName"],
			"customer_type" : _("Individual"),
			"customer_group" : _("Commercial"),
			"territory" : _("All Territories"),
		}).insert(ignore_permissions=True)
		if "BillAddr" in customer:
			create_address(erpcustomer, "Customer", customer["BillAddr"], "Billing")
		if "ShipAddr" in customer:
			create_address(erpcustomer, "Customer", customer["ShipAddr"], "Shipping")
	except:
		pass

def save_item(item):
	try:
		frappe.get_doc({
			"doctype": "Item",
			"quickbooks_id": item["Id"],
			"item_code" : item["Name"],
			"stock_uom": "Unit",
			"item_group": "All Item Groups",
			"item_defaults": [{"company": "Sandbox Actual"}]
		}).insert(ignore_permissions=True)
	except:
		pass

def save_supplier(supplier):
	try:
		erpsupplier = frappe.get_doc({
			"doctype": "Supplier",
			"quickbooks_id": supplier["Id"],
			"supplier_name" : supplier["DisplayName"],
			"supplier_group" : _("All Supplier Groups"),
		}).insert(ignore_permissions=True)
		if "BillAddr" in supplier:
			create_address(erpsupplier, "Supplier", supplier["BillAddr"], "Billing")
		if "ShipAddr" in supplier:
			create_address(erpsupplier, "Supplier",supplier["ShipAddr"], "Shipping")
	except:
		pass

def save_si(si):
	try:
		erp_si = frappe.get_doc({
			"doctype": "Sales Invoice",
			"quickbooks_id": si["Id"],
			"naming_series": "SINV-",

			# Need to check with someone as to what exactly this field represents
			# And whether it is equivalent to posting_date
			"posting_date": si["TxnDate"],

			# Due Date should be calculated from SalesTerm if not provided.
			# For Now Just setting a default to suppress mandatory errors.
			"due_date": si.get("DueDate", "2020-01-01"),

			# Shouldn't default to Current Bank Account
			# Decide using AccountRef from TxnRef
			# And one more thing, While creating accounts set account_type
			"debit_to": "Current - QB - SA",

			"customer": frappe.get_all("Customer",
				filters={
					"quickbooks_id": si["CustomerRef"]["value"]
				})[0]["name"],
			"items": get_items(si["Line"]),

			# Do not change posting_date upon submission
			"set_posting_time": 1
		}).insert().submit()
		frappe.db.commit()
	except:
		import traceback
		traceback.print_exc()

def get_items(lines):
	items = []
	for line in lines:
		if line["DetailType"] == "SalesItemLineDetail":
			item = frappe.db.get_all("Item",
				filters={
					"quickbooks_id": line["SalesItemLineDetail"]["ItemRef"]["value"]
				},
				fields=["name", "stock_uom"]
			)[0]
			items.append({
				"item_name": item["name"],
				"conversion_factor": 1,
				"income_account": "Sales of Product Income - QB - SA",
				"uom": item["stock_uom"],
				"description": line.get("Description", line["SalesItemLineDetail"]["ItemRef"]["name"]),
				"qty": line["SalesItemLineDetail"]["Qty"],
				"rate": line["SalesItemLineDetail"]["UnitPrice"],
			})
	return items

def create_address(entity, doctype, address, address_type):
	try :
		frappe.get_doc({
			"doctype": "Address",
			"quickbooks_address_id": address["Id"],
			"address_title": entity.name,
			"address_type": address_type,
			"address_line1": address["Line1"],
			"city": address["City"],
			"gst_state": "Maharashtra",
			"links": [{"link_doctype": doctype, "link_name": entity.name}]
		}).insert()
	except:
		pass


def make_custom_fields():
	relevant_doctypes = ["Account", "Customer", "Address", "Item", "Supplier", "Sales Invoice"]
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
	"Account": save_account,
	"Customer": save_customer,
	"Item": save_item,
	"Supplier": save_supplier,
	"Sales Invoice": save_si,
}

def save_entries(doctype, entries):
	save = save_methods[doctype]
	for entry in entries:
		save(entry)

# A quickbooks api contraint
MAX_RESULT_COUNT = 10
BASE_QUERY_URL = "https://sandbox-quickbooks.api.intuit.com/v3/company/{}/{}"
qb_map = {
	"Account": "Account",
	"Customer": "Customer",
	"Item": "Item",
	"Supplier": "Vendor",
	"Sales Invoice": "Invoice",
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
