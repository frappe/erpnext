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


client_id = frappe.db.get_value("Quickbooks Migrator", None, "client_id")
client_secret = frappe.db.get_value("Quickbooks Migrator", None, "client_secret")
scope = frappe.db.get_value("Quickbooks Migrator", None, "scope")
redirect_uri = frappe.db.get_value("Quickbooks Migrator", None, "redirect_url")
company = frappe.db.get_value("Quickbooks Migrator", None, "company")
expense_account = frappe.db.get_value("Quickbooks Migrator", None, "expense_account")
income_account = frappe.db.get_value("Quickbooks Migrator", None, "income_account")
receivable_account = frappe.db.get_value("Quickbooks Migrator", None, "receivable_account")

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

authorization_endpoint = "https://appcenter.intuit.com/connect/oauth2"
@frappe.whitelist()
def get_authorization_url():
	token = frappe.cache().get("quickbooks_access_token")
	if token:
		response = {"authenticated": True}
	else:
		response = {
			"authenticated": False,
			"url": oauth.authorization_url(authorization_endpoint)[0],
		}
	return response

@frappe.whitelist()
def callback(*args, **kwargs):
	frappe.respond_as_web_page("Quickbooks Authentication", html="<script>window.close()</script>")
	frappe.cache().set("quickbooks_code", kwargs.get("code"))
	company_id = kwargs.get("realmId")
	frappe.cache().set("quickbooks_company_id", company_id)
	get_access_token()
	fetch()

@frappe.whitelist()
def fetch_accounts():
	company_id = frappe.cache().get("quickbooks_company_id").decode()
	make_custom_fields()
	make_root_accounts()
	fetch_all_entries(entity="Account", company_id=company_id)

@frappe.whitelist()
def fetch():
	company_id = frappe.cache().get("quickbooks_company_id").decode()
	make_custom_fields()
	relevant_entities = ["Customer", "Item", "Vendor", "JournalEntry", "Invoice", "Payment", "Bill", "BillPayment"]
	for entity in relevant_entities:
		print(entity)
		fetch_all_entries(entity=entity, company_id=company_id)

def publish(*args, **kwargs):
	frappe.publish_realtime("quickbooks_progress_update", *args, **kwargs)

token_endpoint = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
def get_access_token():
	code = frappe.cache().get("quickbooks_code").decode()
	token = oauth.fetch_token(token_endpoint, client_secret=client_secret, code=code)
	frappe.cache().set("quickbooks_access_token", token["access_token"])
	frappe.cache().set("quickbooks_refresh_token", token["refresh_token"])

def make_root_accounts():
	roots = ["Asset", "Equity", "Expense", "Liability", "Income"]
	for root in roots:
		try:
			if not frappe.db.exists("Account", encode_company_abbr("{} - QB".format(root), company)):
				frappe.get_doc({
					"doctype": "Account",
					"account_name": "{} - QB".format(root),
					"root_type": root,
					"is_group": "1",
					"company": company,
				}).insert(ignore_permissions=True, ignore_mandatory=True)
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
		if not frappe.db.exists({"doctype": "Account", "quickbooks_id": account["Id"]}):
			frappe.get_doc({
				"doctype": "Account",
				"quickbooks_id": account["Id"],
				"account_name": "{} - QB".format(account["Name"]),
				"root_type": mapping[account["AccountType"]],
				"parent_account": encode_company_abbr("{} - QB".format(mapping[account["AccountType"]]), company),
				"is_group": "0",
				"company": company,
			}).insert(ignore_permissions=True, ignore_mandatory=True)
	except:
		pass

def save_customer(customer):
	try:
		if not frappe.db.exists({"doctype": "Customer", "quickbooks_id": customer["Id"]}):
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
		if not frappe.db.exists({"doctype": "Item", "quickbooks_id": item["Id"]}):
			frappe.get_doc({
				"doctype": "Item",
				"quickbooks_id": item["Id"],
				"item_code" : item["Name"],
				"stock_uom": "Unit",
				"item_group": "All Item Groups",
				"item_defaults": [{"company": company}]
			}).insert(ignore_permissions=True)
	except:
		pass

def save_vendor(vendor):
	try:
		if not frappe.db.exists({"doctype": "Supplier", "quickbooks_id": vendor["Id"]}):
			erpsupplier = frappe.get_doc({
				"doctype": "Supplier",
				"quickbooks_id": vendor["Id"],
				"supplier_name" : vendor["DisplayName"],
				"supplier_group" : _("All Supplier Groups"),
			}).insert(ignore_permissions=True)
			if "BillAddr" in vendor:
				create_address(erpsupplier, "Supplier", vendor["BillAddr"], "Billing")
			if "ShipAddr" in vendor:
				create_address(erpsupplier, "Supplier",vendor["ShipAddr"], "Shipping")
	except:
		pass

def save_invoice(invoice):
	try:
		if not frappe.db.exists({"doctype": "Sales Invoice", "quickbooks_id": invoice["Id"]}):
			frappe.get_doc({
				"doctype": "Sales Invoice",
				"quickbooks_id": invoice["Id"],
				"naming_series": "SINV-",

				# Quickbooks uses ISO 4217 Code
				# of course this gonna come back to bite me
				"currency": invoice["CurrencyRef"]["value"],

				# Need to check with someone as to what exactly this field represents
				# And whether it is equivalent to posting_date
				"posting_date": invoice["TxnDate"],

				# Due Date should be calculated from SalesTerm if not provided.
				# For Now Just setting a default to suppress mandatory errors.
				"due_date": invoice.get("DueDate", "2020-01-01"),

				# Shouldn't default to Current Bank Account
				# Decide using AccountRef from TxnRef
				# And one more thing, While creating accounts set account_type
				"debit_to": receivable_account,

				"customer": frappe.get_all("Customer",
					filters={
						"quickbooks_id": invoice["CustomerRef"]["value"]
					})[0]["name"],
				"items": get_items(invoice["Line"]),
				"taxes": get_taxes(invoice["TxnTaxDetail"]["TaxLine"]),

				# Do not change posting_date upon submission
				"set_posting_time": 1
			}).insert().submit()
			frappe.db.commit()
	except:
		import traceback
		traceback.print_exc()

def save_journal_entry(journal_entry):
	try:
		if not frappe.db.exists({"doctype": "Journal Entry", "quickbooks_id": journal_entry["Id"]}):
			frappe.get_doc({
				"doctype": "Journal Entry",
				"quickbooks_id": journal_entry["Id"],
				"naming_series": "JV-",
				"company": company,
				"posting_date": journal_entry["TxnDate"],
				"accounts": get_accounts(journal_entry["Line"]),
			}).insert().submit()
			frappe.db.commit()
	except:
		import traceback
		traceback.print_exc()

def save_bill(bill):
	try:
		if not frappe.db.exists({"doctype": "Purchase Invoice", "quickbooks_id": bill["Id"]}):
			frappe.get_doc({
				"doctype": "Purchase Invoice",
				"quickbooks_id": bill["Id"],
				"naming_series": "PINV-",
				"currency": bill["CurrencyRef"]["value"],
				"posting_date": bill["TxnDate"],
				"due_date": bill.get("DueDate", "2020-01-01"),
				"credit_to": frappe.get_all("Account",
					filters={
						"quickbooks_id": bill["APAccountRef"]["value"]
					})[0]["name"],
				"supplier": frappe.get_all("Supplier",
					filters={
						"quickbooks_id": bill["VendorRef"]["value"]
					})[0]["name"],
				"items": get_pi_items(bill["Line"]),
				"taxes": get_taxes(bill["TxnTaxDetail"]["TaxLine"]),
				"set_posting_time": 1
			}).insert().submit()
			frappe.db.commit()
	except:
		import traceback
		traceback.print_exc()

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
def save_payment(payment):
	try:
		if not frappe.db.exists({"doctype": "Payment Entry", "quickbooks_id": payment["Id"]}):
			# Check if Payment is Linked to an Invoice
			if payment["Line"][0]["LinkedTxn"][0]["TxnType"] == "Invoice":
				sales_invoice = frappe.get_all("Sales Invoice",
					filters={
						"quickbooks_id": payment["Line"][0]["LinkedTxn"][0]["TxnId"]
					})[0]["name"]
				erp_pe = get_payment_entry("Sales Invoice", sales_invoice)
				erp_pe.quickbooks_id = "Payment - {}".format(payment["Id"])
				erp_pe.reference_no = "Reference No"
				erp_pe.reference_date = payment["TxnDate"]
				erp_pe.insert().submit()
				frappe.db.commit()
	except:
		import traceback
		traceback.print_exc()

def save_bill_payment(bill_payment):
	try:
		if not frappe.db.exists({"doctype": "Payment Entry", "quickbooks_id": bill_payment["Id"]}):
			# Check if Payment is Linked to an Invoice
			if bill_payment["Line"][0]["LinkedTxn"][0]["TxnType"] == "Bill":
				purchase_invoice = frappe.get_all("Purchase Invoice",
					filters={
						"quickbooks_id": bill_payment["Line"][0]["LinkedTxn"][0]["TxnId"]
					})[0]["name"]
				erp_pe = get_payment_entry("Purchase Invoice", purchase_invoice)
				erp_pe.quickbooks_id = "BillPayment - {}".format(bill_payment["Id"])
				erp_pe.reference_no = "Reference No"
				erp_pe.reference_date = bill_payment["TxnDate"]
				erp_pe.insert().submit()
				frappe.db.commit()
	except:
		import traceback
		traceback.print_exc()

posting_type_field_mapping = {
	"Credit": "credit_in_account_currency",
	"Debit": "debit_in_account_currency",
}
def get_accounts(lines):
	accounts = []
	for line in lines:
		if line["DetailType"] == "JournalEntryLineDetail":
			account_name = frappe.db.get_all("Account",
				filters={
					"quickbooks_id": line["JournalEntryLineDetail"]["AccountRef"]["value"]
				},
			)[0]["name"]
			posting_type = line["JournalEntryLineDetail"]["PostingType"]
			accounts.append({
				"account": account_name,
					posting_type_field_mapping[posting_type]: line["Amount"],
			})
	return accounts

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
				"item_code": item["name"],
				"conversion_factor": 1,
				"income_account": income_account,
				"uom": item["stock_uom"],
				"description": line.get("Description", line["SalesItemLineDetail"]["ItemRef"]["name"]),
				"qty": line["SalesItemLineDetail"]["Qty"],
				"price_list_rate": line["SalesItemLineDetail"]["UnitPrice"],
			})
		elif line["DetailType"] == "DescriptionOnly":
			items[-1].update({
				"margin_type": "Percentage",
				"margin_rate_or_amount": int(line["Description"].split("%")[0]),
			})
	return items

def get_pi_items(lines):
	items = []
	for line in lines:
		if line["DetailType"] == "ItemBasedExpenseLineDetail":
			item = frappe.db.get_all("Item",
				filters={
					"quickbooks_id": line["ItemBasedExpenseLineDetail"]["ItemRef"]["value"]
				},
				fields=["name", "stock_uom"]
			)[0]
			items.append({
				"item_code": item["name"],
				"conversion_factor": 1,
				"expense_account": expense_account,
				"uom": item["stock_uom"],
				"description": line.get("Description", line["ItemBasedExpenseLineDetail"]["ItemRef"]["name"]),
				"qty": line["ItemBasedExpenseLineDetail"]["Qty"],
				"price_list_rate": line["ItemBasedExpenseLineDetail"]["UnitPrice"],
			})
		elif line["DetailType"] == "AccountBasedExpenseLineDetail":
			items.append({
				"item_name": line.get("Description", line["AccountBasedExpenseLineDetail"]["AccountRef"]["name"]),
				"conversion_factor": 1,
				"expense_account": frappe.db.get_all("Account",
						filters={
							"quickbooks_id": line["AccountBasedExpenseLineDetail"]["AccountRef"]["value"]
						},
					)[0]["name"],
				"uom": "Unit",
				"description": line.get("Description", line["AccountBasedExpenseLineDetail"]["AccountRef"]["name"]),
				"qty": 1,
				"price_list_rate": line["Amount"],
			})
	return items

def get_taxes(lines):
	taxes = []
	for line in lines:
		taxes.append({
			"charge_type": "Actual",

			# This is wrong will fix later
			"account_head": "TDS Payable - QB - SA",

			# description c/sould be fetched from TaxLineDetail.TaxRateRef.Description and Name
			"description": "Added total amount from Invoice",
			"tax_amount": line["Amount"],
		})
	return taxes

def create_address(entity, doctype, address, address_type):
	try :
		if not frappe.db.exists({"doctype": "Address", "quickbooks_id": address["Id"]}):
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
	relevant_doctypes = ["Account", "Customer", "Address", "Item", "Supplier", "Sales Invoice", "Journal Entry", "Purchase Invoice", "Payment Entry"]
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
	"Vendor": save_vendor,
	"Invoice": save_invoice,
	"JournalEntry": save_journal_entry,
	"Bill": save_bill,
	"Payment": save_payment,
	"BillPayment": save_bill_payment,
}

def save_entries(doctype, entries):
	total = len(entries)
	save = save_methods[doctype]
	for index, entry in enumerate(entries):
		publish({"event": "save", "doctype": doctype, "count": index, "total": total})
		save(entry)

# A quickbooks api contraint
MAX_RESULT_COUNT = 1000
BASE_QUERY_URL = "https://sandbox-quickbooks.api.intuit.com/v3/company/{}/{}"

def get(*args, **kwargs):
	refresh_tokens()
	token = frappe.cache().get("quickbooks_access_token").decode()
	kwargs["headers"] = get_headers(token)
	response = requests.get(*args, **kwargs)
	if response.status_code == 401:
		refresh_tokens()
		get(*args, **kwargs)
	return response

def refresh_tokens():
	refresh_token = frappe.cache().get("quickbooks_refresh_token").decode()
	code = frappe.cache().get("quickbooks_code").decode()
	token = oauth.refresh_token(token_endpoint, client_id=client_id, refresh_token=refresh_token, client_secret=client_secret, code=code)
	frappe.cache().set("quickbooks_refresh_token", token["refresh_token"])
	frappe.cache().set("quickbooks_access_token", token["access_token"])

def fetch_all_entries(entity="", company_id=1):
	query_uri = BASE_QUERY_URL.format(company_id, "query")

	# Count number of entries
	entry_count = get(query_uri,
		params={
			"query": """SELECT COUNT(*) FROM {}""".format(entity)
		}
	).json()["QueryResponse"]["totalCount"]

	# fetch pages and accumulate
	entries = []
	for start_position in range(1, entry_count + 1, MAX_RESULT_COUNT):
		publish({"event": "fetch", "doctype": entity, "count": start_position, "total": entry_count, "des":entry_count})
		response = get(query_uri,
			params={
				"query": """SELECT * FROM {} STARTPOSITION {} MAXRESULTS {}""".format(entity, start_position, MAX_RESULT_COUNT)
			}
		).json()["QueryResponse"][entity]
		entries.extend(response)
	publish({"event": "finish"})
	save_entries(entity, entries)
	publish({"event": "finish"})
	publish({"event": "message", "message": "Fetched {}".format(entity)})

def get_headers(token):
	return {"Accept": "application/json",
	"Authorization": "Bearer {}".format(token)}

class QuickBooksMigrator(Document):
	pass
