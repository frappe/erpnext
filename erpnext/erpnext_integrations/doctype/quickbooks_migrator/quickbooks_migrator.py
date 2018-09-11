# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from requests_oauthlib import OAuth2Session
import json, requests
from erpnext import encode_company_abbr
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.model.naming import append_number_if_name_exists


client_id = frappe.db.get_value("Quickbooks Migrator", None, "client_id")
client_secret = frappe.db.get_value("Quickbooks Migrator", None, "client_secret")
scope = frappe.db.get_value("Quickbooks Migrator", None, "scope")
redirect_uri = frappe.db.get_value("Quickbooks Migrator", None, "redirect_url")
company = frappe.db.get_value("Quickbooks Migrator", None, "company")
default_cost_center = frappe.db.get_value('Company', company, 'cost_center')

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

authorization_endpoint = "https://appcenter.intuit.com/connect/oauth2"
@frappe.whitelist()
def get_authorization_url():
	return {"url": oauth.authorization_url(authorization_endpoint)[0]}

@frappe.whitelist()
def is_authenticated():
	return frappe.cache().exists("quickbooks_refresh_token") and frappe.cache().exists("quickbooks_access_token")

@frappe.whitelist()
def are_accounts_synced():
    # Check if there is any existing Account with Quickbooks ID
	return bool(frappe.get_all("Account",
		filters=[["quickbooks_id", "not like", ""]],
		fields=["count(name) as count"]
	)[0]["count"])

@frappe.whitelist()
def callback(*args, **kwargs):
	frappe.respond_as_web_page("Quickbooks Authentication", html="<script>window.close()</script>")
	frappe.cache().set("quickbooks_code", kwargs.get("code"))
	company_id = kwargs.get("realmId")
	frappe.cache().set("quickbooks_company_id", company_id)
	get_access_token()
	frappe.publish_realtime("quickbooks_authenticated")

def fetch_accounts():
	company_id = frappe.cache().get("quickbooks_company_id").decode()
	make_custom_fields()
	make_root_accounts()
	fetch_all_entries(entity="Account", company_id=company_id)
	fetch_all_entries(entity="TaxRate", company_id=company_id)
	fetch_all_entries(entity="TaxCode", company_id=company_id)
	frappe.clear_messages()
	frappe.publish_realtime("quickbooks_accounts_synced")

@frappe.whitelist()
def fetch_data():
	fetch_accounts()
	company_id = frappe.cache().get("quickbooks_company_id").decode()
	make_custom_fields()
	fetch_general_ledger(company_id=company_id)
	relevant_entities = ["Customer", "Item", "Vendor", "JournalEntry", "Preferences", "Invoice", "Payment", "Bill", "BillPayment", "Purchase", "Deposit", "VendorCredit", "CreditMemo", "SalesReceipt"]
	for entity in relevant_entities:
		fetch_all_entries(entity=entity, company_id=company_id)
	relevant_entities = ["Advance Payment", "Tax Payment", "Sales Tax Payment", "Purchase Tax Payment"]
	for entity in relevant_entities:
		fetch_all_entries_from_gl(entity=entity, company_id=company_id)
	frappe.clear_messages()

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
			if not frappe.db.exists({"doctype": "Account", "name": encode_company_abbr("{} - QB".format(root), company), "company": company}):
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
		if not frappe.db.exists({"doctype": "Account", "quickbooks_id": account["Id"], "company": company}):
			is_child = account["SubAccount"]
			is_group = is_group_account(account["Id"])
			# Create Two Accounts for every Group Account
			if is_group:
				account_id = "Group - {}".format(account["Id"])
			else:
				account_id = account["Id"]

			if is_child:
				parent_account = get_account_name_by_id("Group - {}".format(account["ParentRef"]["value"]))
			else:
				parent_account = encode_company_abbr("{} - QB".format(mapping[account["AccountType"]]), company)

			frappe.get_doc({
				"doctype": "Account",
				"quickbooks_id": account_id,
				"account_name": get_unique_account_name(account["Name"]),
				"root_type": mapping[account["AccountType"]],
				"account_type": get_account_type(account),
				"account_currency": account["CurrencyRef"]["value"],
				"parent_account": parent_account,
				"is_group": is_group,
				"company": company,
			}).insert(ignore_permissions=True, ignore_mandatory=True)

			if is_group:
				# Create a Leaf account corresponding to the group account
				frappe.get_doc({
					"doctype": "Account",
					"quickbooks_id": account["Id"],
					"account_name": get_unique_account_name(account["Name"]),
					"root_type": mapping[account["AccountType"]],
					"account_type": get_account_type(account),
					"account_currency": account["CurrencyRef"]["value"],
					"parent_account": get_account_name_by_id(account_id),
					"is_group": 0,
					"company": company,
				}).insert(ignore_permissions=True, ignore_mandatory=True)
			if account["AccountSubType"] == "UndepositedFunds":
				frappe.cache().set("quickbooks-cached-undeposited-funds-account-id", account["Id"])
	except:
		import traceback
		traceback.print_exc()

def get_account_type(account):
	account_subtype_mapping = {"UndepositedFunds": "Cash"}
	account_type = account_subtype_mapping.get(account["AccountSubType"])
	if account_type is None:
		account_type_mapping = {"Accounts Payable": "Payable", "Accounts Receivable": "Receivable", "Bank": "Bank", "Credit Card": "Bank"}
		account_type = account_type_mapping.get(account["AccountType"])
	return account_type

def save_tax_rate(tax_rate):
	try:
		if not frappe.db.exists({"doctype": "Account", "quickbooks_id": "TaxRate - {}".format(tax_rate["Id"]), "company": company}):
			frappe.get_doc({
				"doctype": "Account",
				"quickbooks_id": "TaxRate - {}".format(tax_rate["Id"]),
				"account_name": "{} - QB".format(tax_rate["Name"]),
				"root_type": "Liability",
				"parent_account": encode_company_abbr("{} - QB".format("Liability"), company),
				"is_group": "0",
				"company": company,
			}).insert(ignore_permissions=True, ignore_mandatory=True)
	except:
		import traceback
		traceback.print_exc()

def save_tax_code(tax_code):
	pass

def save_customer(customer):
	try:
		if not frappe.db.exists({"doctype": "Customer", "quickbooks_id": customer["Id"], "company": company}):
			receivable_account = frappe.get_all("Account", filters={
				"account_type": "Receivable",
				"account_currency": customer["CurrencyRef"]["value"],
				"company": company,
			})[0]["name"]
			erpcustomer = frappe.get_doc({
				"doctype": "Customer",
				"quickbooks_id": customer["Id"],
				"customer_name" : encode_company_abbr(customer["DisplayName"], company),
				"customer_type" : _("Individual"),
				"customer_group" : _("Commercial"),
				"default_currency": customer["CurrencyRef"]["value"],
				"accounts": [{"company": company, "account": receivable_account}],
				"territory" : _("All Territories"),
				"company": company,
			}).insert(ignore_permissions=True)
			if "BillAddr" in customer:
				create_address(erpcustomer, "Customer", customer["BillAddr"], "Billing")
			if "ShipAddr" in customer:
				create_address(erpcustomer, "Customer", customer["ShipAddr"], "Shipping")
	except:
		import traceback
		traceback.print_exc()

def save_item(item):
	try:
		if not frappe.db.exists({"doctype": "Item", "quickbooks_id": item["Id"], "company": company}):
			if item["Type"] in ("Service", "Inventory"):
				item_dict = {
					"doctype": "Item",
					"quickbooks_id": item["Id"],
					"item_code" : encode_company_abbr(item["Name"], company),
					"stock_uom": "Unit",
					"is_stock_item": 0,
					"item_group": "All Item Groups",
					"company": company,
					"item_defaults": [{"company": company}]
				}
				if "ExpenseAccountRef" in item:
					expense_account = get_account_name_by_id(item["ExpenseAccountRef"]["value"])
					item_dict["item_defaults"][0]["expense_account"] = expense_account
				if "IncomeAccountRef" in item:
					income_account = get_account_name_by_id(item["IncomeAccountRef"]["value"])
					item_dict["item_defaults"][0]["income_account"] = income_account
				frappe.get_doc(item_dict).insert(ignore_permissions=True)
	except:
		import traceback
		traceback.print_exc()

def save_vendor(vendor):
	try:
		if not frappe.db.exists({"doctype": "Supplier", "quickbooks_id": vendor["Id"], "company": company}):
			erpsupplier = frappe.get_doc({
				"doctype": "Supplier",
				"quickbooks_id": vendor["Id"],
				"supplier_name" : encode_company_abbr(vendor["DisplayName"], company),
				"supplier_group" : _("All Supplier Groups"),
				"company": company,
			}).insert(ignore_permissions=True)
			if "BillAddr" in vendor:
				create_address(erpsupplier, "Supplier", vendor["BillAddr"], "Billing")
			if "ShipAddr" in vendor:
				create_address(erpsupplier, "Supplier",vendor["ShipAddr"], "Shipping")
	except:
		import traceback
		traceback.print_exc()

def save_preference(preference):
	try:
		if preference["SalesFormsPrefs"]["AllowShipping"]:
			shipping_account_id = preference["SalesFormsPrefs"]["DefaultShippingAccount"]
			frappe.cache().set("quickbooks-cached-shipping-account-id", shipping_account_id)
	except:
		import traceback
		traceback.print_exc()

def save_invoice(invoice):
	try:
		if not frappe.db.exists({"doctype": "Sales Invoice", "quickbooks_id": invoice["Id"], "company": company}):
			if any(linked["TxnType"] in ("StatementCharge", "ReimburseCharge") for linked in invoice["LinkedTxn"]):
				save_invoice_as_journal_entry(invoice)
			else:
				invoice_dict = {
					"doctype": "Sales Invoice",
					"quickbooks_id": invoice["Id"],
					"naming_series": "SINV-",

					# Quickbooks uses ISO 4217 Code
					# of course this gonna come back to bite me
					"currency": invoice["CurrencyRef"]["value"],
					"conversion_rate": invoice.get("ExchangeRate", 1),

					# Need to check with someone as to what exactly this field represents
					# And whether it is equivalent to posting_date
					"posting_date": invoice["TxnDate"],

					# Due Date should be calculated from SalesTerm if not provided.
					# For Now Just setting a default to suppress mandatory errors.
					"due_date": invoice.get("DueDate", "2020-01-01"),
					"customer": frappe.get_all("Customer",
						filters={
							"quickbooks_id": invoice["CustomerRef"]["value"],
							"company": company,
						})[0]["name"],
					"items": get_items(invoice),
					"taxes": get_taxes(invoice),

					# Do not change posting_date upon submission
					"set_posting_time": 1,
					"disable_rounded_total": 1,
					"company": company,
				}
				discount = get_discount(invoice["Line"])
				if discount:
					if invoice["ApplyTaxAfterDiscount"]:
						invoice_dict["apply_discount_on"] = "Net Total"
					else:
						invoice_dict["apply_discount_on"] = "Grand Total"
					invoice_dict["discount_amount"] = discount["Amount"]
				frappe.get_doc(invoice_dict).insert().submit()
	except:
		import traceback
		traceback.print_exc()

def get_discount(lines):
	for line in lines:
		if line["DetailType"] == "DiscountLineDetail":
			return line


def save_invoice_as_journal_entry(invoice):
	if not frappe.db.exists({"doctype": "Journal Entry", "quickbooks_id": "Invoice - {}".format(invoice["Id"]), "company": company}):
		accounts = []
		for line in get_general_ledger()["Invoice"][invoice["Id"]]["lines"]:
			print(line)
			account_line = {"account": line["account"]}
			if line["debit"]:
				account_line["debit_in_account_currency"] = line["debit"]
				account_line["party_type"] = "Customer"
				account_line["party"] = frappe.get_all("Customer",
					filters={"quickbooks_id": invoice["CustomerRef"]["value"], "company": company}
				)[0]["name"]
			elif line["credit"]:
				account_line["credit_in_account_currency"] = line["credit"]
			accounts.append(account_line)
		frappe.get_doc({
			"doctype": "Journal Entry",
			"quickbooks_id": "Invoice - {}".format(invoice["Id"]),
			"naming_series": "JV-",
			"company": company,
			"posting_date": invoice["TxnDate"],
			"accounts": accounts,
		}).insert().submit()

def save_credit_memo(credit_memo):
	try:
		if not frappe.db.exists({"doctype": "Sales Invoice", "quickbooks_id": "Credit Memo - {}".format(credit_memo["Id"]), "company": company}):
			frappe.get_doc({
				"doctype": "Sales Invoice",
				"quickbooks_id": "Credit Memo - {}".format(credit_memo["Id"]),
				"naming_series": "SINV-",
				"currency": credit_memo["CurrencyRef"]["value"],
				"conversion_rate": credit_memo.get("ExchangeRate", 1),
				"posting_date": credit_memo["TxnDate"],
				"due_date": credit_memo.get("DueDate", "2020-01-01"),
				"customer": frappe.get_all("Customer",
					filters={
						"quickbooks_id": credit_memo["CustomerRef"]["value"],
						"company": company,
					})[0]["name"],
				"items": get_items(credit_memo, is_return=True),
				"taxes": get_taxes(credit_memo),
				"set_posting_time": 1,
				"disable_rounded_total": 1,
				"is_return": 1,
				"company": company,
			}).insert().submit()
	except:
		import traceback
		traceback.print_exc()

def save_journal_entry(journal_entry):
	try:
		if not frappe.db.exists({"doctype": "Journal Entry", "quickbooks_id": journal_entry["Id"], "company": company}):
			frappe.get_doc({
				"doctype": "Journal Entry",
				"quickbooks_id": journal_entry["Id"],
				"naming_series": "JV-",
				"company": company,
				"posting_date": journal_entry["TxnDate"],
				"accounts": get_accounts(journal_entry["Line"]),
			}).insert().submit()
	except:
		import traceback
		traceback.print_exc()

def save_bill(bill):
	try:
		if not frappe.db.exists({"doctype": "Purchase Invoice", "quickbooks_id": bill["Id"], "company": company}):
			credit_to_account = get_account_name_by_id(bill["APAccountRef"]["value"])
			frappe.get_doc({
				"doctype": "Purchase Invoice",
				"quickbooks_id": bill["Id"],
				"naming_series": "PINV-",
				"currency": bill["CurrencyRef"]["value"],
				"conversion_rate": bill.get("ExchangeRate", 1),
				"posting_date": bill["TxnDate"],
				"due_date":  bill["TxnDate"],
				"credit_to": credit_to_account,
				"supplier": frappe.get_all("Supplier",
					filters={
						"quickbooks_id": bill["VendorRef"]["value"],
						"company": company,
					})[0]["name"],
				"items": get_pi_items(bill),
				"taxes": get_taxes(bill),
				"set_posting_time": 1,
				"disable_rounded_total": 1,
			}).insert().submit()
	except:
		import traceback
		traceback.print_exc()

def save_vendor_credit(vendor_credit):
	try:
		if not frappe.db.exists({"doctype": "Purchase Invoice", "quickbooks_id": "Vendor Credit - {}".format(vendor_credit["Id"]), "company": company}):
			credit_to_account = get_account_name_by_id(vendor_credit["APAccountRef"]["value"])
			frappe.get_doc({
				"doctype": "Purchase Invoice",
				"quickbooks_id": "Vendor Credit - {}".format(vendor_credit["Id"]),
				"naming_series": "PINV-",
				"currency": vendor_credit["CurrencyRef"]["value"],
				"conversion_rate": vendor_credit.get("ExchangeRate", 1),
				"posting_date": vendor_credit["TxnDate"],
				"due_date":  vendor_credit["TxnDate"],
				"credit_to": credit_to_account,
				"supplier": frappe.get_all("Supplier",
					filters={
						"quickbooks_id": vendor_credit["VendorRef"]["value"],
						"company": company,
					})[0]["name"],
				"items": get_pi_items(vendor_credit, is_return=True),
				"taxes": get_taxes(vendor_credit),
				"set_posting_time": 1,
				"disable_rounded_total": 1,
				"company": company,
				"is_return": 1
			}).insert().submit()
	except:
		import traceback
		traceback.print_exc()


def save_payment(payment):
	try:
		if not frappe.db.exists({"doctype": "Payment Entry", "quickbooks_id": "Payment - {}".format(payment["Id"]), "company": company}):
			# Check if Payment is Linked to an Invoice
			if payment["Line"][0]["LinkedTxn"][0]["TxnType"] == "Invoice":
				sales_invoice = frappe.get_all("Sales Invoice",
					filters={
						"quickbooks_id": payment["Line"][0]["LinkedTxn"][0]["TxnId"],
						"company": company,
					})[0]["name"]
				deposit_account = get_account_name_by_id(payment["DepositToAccountRef"]["value"])
				erp_pe = get_payment_entry("Sales Invoice", sales_invoice, bank_account=deposit_account)
				erp_pe.quickbooks_id = "Payment - {}".format(payment["Id"])
				erp_pe.reference_no = "Reference No"
				erp_pe.posting_date = payment["TxnDate"]
				erp_pe.reference_date = payment["TxnDate"]
				erp_pe.insert().submit()
	except:
		import traceback
		traceback.print_exc()

def save_bill_payment(bill_payment):
	try:
		if not frappe.db.exists({"doctype": "Payment Entry", "quickbooks_id": "BillPayment - {}".format(bill_payment["Id"]), "company": company}):
			# Check if Payment is Linked to an Invoice
			if bill_payment["Line"][0]["LinkedTxn"][0]["TxnType"] == "Bill":
				purchase_invoice = frappe.get_all("Purchase Invoice",
					filters={
						"quickbooks_id": bill_payment["Line"][0]["LinkedTxn"][0]["TxnId"],
						"company": company,
					})[0]["name"]
				if bill_payment["PayType"] == "Check":
					bank_account = get_account_name_by_id(bill_payment["CheckPayment"]["BankAccountRef"]["value"])
				elif bill_payment["PayType"] == "CreditCard":
					bank_account = get_account_name_by_id(bill_payment["CreditCardPayment"]["CCAccountRef"]["value"])
				else:
					bank_account = None
				erp_pe = get_payment_entry("Purchase Invoice", purchase_invoice,
					bank_account=bank_account,
				)
				erp_pe.quickbooks_id = "BillPayment - {}".format(bill_payment["Id"])
				erp_pe.reference_no = "Reference No"
				erp_pe.paid_mount = bill_payment["TotalAmt"]
				erp_pe.posting_date = bill_payment["TxnDate"]
				erp_pe.reference_date = bill_payment["TxnDate"]
				erp_pe.insert().submit()
	except:
		import traceback
		traceback.print_exc()

def save_purchase(purchase):
	try:
		if not frappe.db.exists({"doctype": "Journal Entry", "quickbooks_id": "Purchase - {}".format(purchase["Id"]), "company": company}):
			# Credit Bank Account
			accounts = [{
					"account": get_account_name_by_id(purchase["AccountRef"]["value"]),
					"credit_in_account_currency": purchase["TotalAmt"],
				}]

			# Debit Mentioned Accounts
			for line in purchase["Line"]:
				if line["DetailType"] == "AccountBasedExpenseLineDetail":
					account = get_account_name_by_id(line["AccountBasedExpenseLineDetail"]["AccountRef"]["value"])
				elif line["DetailType"] == "ItemBasedExpenseLineDetail":
					account = frappe.get_doc("Item",
						{"quickbooks_id": line["ItemBasedExpenseLineDetail"]["ItemRef"]["value"], "company": company}
					).item_defaults[0].expense_account
				accounts.append({
					"account": account,
					"debit_in_account_currency": line["Amount"],
				})

			# Debit Tax Accounts
			if "TxnTaxDetail" in purchase:
				for line in purchase["TxnTaxDetail"]["TaxLine"]:
					accounts.append({
						"account": get_account_name_by_id("TaxRate - {}".format(line["TaxLineDetail"]["TaxRateRef"]["value"])),
						"debit_in_account_currency": line["Amount"],
					})

			if purchase.get("Credit"):
				for account in accounts:
					if "debit_in_account_currency" in account:
						account["credit_in_account_currency"] = account["debit_in_account_currency"]
						del account["debit_in_account_currency"]
					else:
						account["debit_in_account_currency"] = account["credit_in_account_currency"]
						del account["credit_in_account_currency"]

			# Create and Submit Journal Entry
			frappe.get_doc({
				"doctype": "Journal Entry",
				"quickbooks_id": "Purchase - {}".format(purchase["Id"]),
				"naming_series": "JV-",
				"company": company,
				"posting_date": purchase["TxnDate"],
				"accounts": accounts,
			}).insert().submit()
	except:
		import traceback
		traceback.print_exc()

def save_deposit(deposit):
	try:
		if not frappe.db.exists({"doctype": "Journal Entry", "quickbooks_id": "Deposit - {}".format(deposit["Id"]), "company": company}):
			# Debit Bank Account
			accounts = [{
					"account": get_account_name_by_id(deposit["DepositToAccountRef"]["value"]),
					"debit_in_account_currency": deposit["TotalAmt"],
				}]

			# Credit Mentioned Accounts
			for line in deposit["Line"]:
				if "LinkedTxn" in line:
					accounts.append({
						"account": get_undeposited_funds_account(),
						"credit_in_account_currency": line["Amount"],
					})
				else:
					accounts.append({
						"account": get_account_name_by_id(line["DepositLineDetail"]["AccountRef"]["value"]),
						"credit_in_account_currency": line["Amount"],
					})

			# Debit Cashback if mentioned
			if "CashBack" in deposit:
				accounts.append({
					"account": get_account_name_by_id(deposit["CashBack"]["AccountRef"]["value"]),
					"debit_in_account_currency": deposit["CashBack"]["Amount"],
				})

			# Create and Submit Journal Entry
			frappe.get_doc({
				"doctype": "Journal Entry",
				"quickbooks_id": "Deposit - {}".format(deposit["Id"]),
				"naming_series": "JV-",
				"company": company,
				"posting_date": deposit["TxnDate"],
				"accounts": accounts,
			}).insert().submit()
	except:
		import traceback
		traceback.print_exc()

def save_sales_receipt(sales_receipt):
	try:
		if not frappe.db.exists({"doctype": "Sales Invoice", "quickbooks_id": "Sales Receipt - {}".format(sales_receipt["Id"]), "company": company}):
			invoice = frappe.get_doc({
				"doctype": "Sales Invoice",
				"quickbooks_id": "Sales Receipt - {}".format(sales_receipt["Id"]),
				"naming_series": "SINV-",
				"currency": sales_receipt["CurrencyRef"]["value"],
				"conversion_rate": sales_receipt.get("ExchangeRate", 1),
				"posting_date": sales_receipt["TxnDate"],
				"due_date": sales_receipt.get("DueDate", "2020-01-01"),
				"customer": frappe.get_all("Customer",
					filters={
						"quickbooks_id": sales_receipt["CustomerRef"]["value"],
						"company": company,
					})[0]["name"],
				"items": get_items(sales_receipt),
				"taxes": get_taxes(sales_receipt),
				"set_posting_time": 1,
				"disable_rounded_total": 1,
				"is_pos": 1,
				"company": company,
				"payments": [{
					"mode_of_payment": "Cash",
					"account": get_account_name_by_id(sales_receipt["DepositToAccountRef"]["value"]),
					"amount": 0
				}]
			}).insert()
			invoice.payments[0].amount = invoice.grand_total
			invoice.submit()
	except:
		import traceback
		traceback.print_exc()

def save_advance_payment(advance_payment):
	try:
		if not frappe.db.exists({"doctype": "Journal Entry", "quickbooks_id": "Advance Payment - {}".format(advance_payment["id"]), "company": company}):
			accounts = []
			for line in advance_payment["lines"]:
				account_line = {"account": line["account"]}
				if line["credit"]:
					account_line["credit_in_account_currency"] = line["credit"]
				else:
					account_line["debit_in_account_currency"] = line["debit"]
				accounts.append(account_line)

			frappe.get_doc({
				"doctype": "Journal Entry",
				"quickbooks_id": "Advance Payment - {}".format(advance_payment["id"]),
				"naming_series": "JV-",
				"company": company,
				"posting_date": advance_payment["date"],
				"accounts": accounts,
			}).insert().submit()
	except:
		import traceback
		traceback.print_exc()

def save_tax_payment(tax_payment):
	try:
		if not frappe.db.exists({"doctype": "Journal Entry", "quickbooks_id": "Tax Payment - {}".format(tax_payment["id"]), "company": company}):
			accounts = []
			for line in tax_payment["lines"]:
				account_line = {"account": line["account"]}
				if line["credit"]:
					account_line["credit_in_account_currency"] = line["credit"]
				else:
					account_line["debit_in_account_currency"] = line["debit"]
				accounts.append(account_line)

			frappe.get_doc({
				"doctype": "Journal Entry",
				"quickbooks_id": "Tax Payment - {}".format(tax_payment["id"]),
				"naming_series": "JV-",
				"company": company,
				"posting_date": tax_payment["date"],
				"accounts": accounts,
			}).insert().submit()
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
			account_name = get_account_name_by_id(line["JournalEntryLineDetail"]["AccountRef"]["value"])
			posting_type = line["JournalEntryLineDetail"]["PostingType"]
			accounts.append({
				"account": account_name,
				posting_type_field_mapping[posting_type]: line["Amount"],
			})
	return accounts

def get_items(invoice, is_return=False):
	items = []
	for line in invoice["Line"]:
		if line["DetailType"] == "SalesItemLineDetail":
			if line["SalesItemLineDetail"]["TaxCodeRef"]["value"] != "TAX":
				tax_code = line["SalesItemLineDetail"]["TaxCodeRef"]["value"]
			else:
				if "TxnTaxCodeRef" in invoice["TxnTaxDetail"]:
					tax_code = invoice["TxnTaxDetail"]["TxnTaxCodeRef"]["value"]
				else:
					tax_code = "NON"
			if line["SalesItemLineDetail"]["ItemRef"]["value"] != "SHIPPING_ITEM_ID":
				item = frappe.db.get_all("Item",
					filters={
						"quickbooks_id": line["SalesItemLineDetail"]["ItemRef"]["value"],
						"company": company,
					},
					fields=["name", "stock_uom"]
				)[0]
				items.append({
					"item_code": item["name"],
					"conversion_factor": 1,
					"uom": item["stock_uom"],
					"description": line.get("Description", line["SalesItemLineDetail"]["ItemRef"]["name"]),
					"qty": line["SalesItemLineDetail"]["Qty"],
					"price_list_rate": line["SalesItemLineDetail"]["UnitPrice"],
					"cost_center": default_cost_center,
					"item_tax_rate": json.dumps(get_item_taxes(tax_code))
				})
			else:
				items.append({
					"item_name": "Shipping",
					"conversion_factor": 1,
					"expense_account": get_account_name_by_id("TaxRate - {}".format(line["SalesItemLineDetail"]["TaxCodeRef"]["value"])),
					"uom": "Unit",
					"description": "Shipping",
					"income_account": get_shipping_account(),
					"qty": 1,
					"price_list_rate": line["Amount"],
					"cost_center": default_cost_center,
					"item_tax_rate": json.dumps(get_item_taxes(tax_code))
				})
			if is_return:
				items[-1]["qty"] *= -1
		elif line["DetailType"] == "DescriptionOnly":
			items[-1].update({
				"margin_type": "Percentage",
				"margin_rate_or_amount": int(line["Description"].split("%")[0]),
			})
	return items

def get_pi_items(purchase_invoice, is_return=False):
	items = []
	for line in purchase_invoice["Line"]:
		if line["DetailType"] == "ItemBasedExpenseLineDetail":
			if line["ItemBasedExpenseLineDetail"]["TaxCodeRef"]["value"] != "TAX":
				tax_code = line["ItemBasedExpenseLineDetail"]["TaxCodeRef"]["value"]
			else:
				if "TxnTaxCodeRef" in purchase_invoice["TxnTaxDetail"]:
					tax_code = purchase_invoice["TxnTaxDetail"]["TxnTaxCodeRef"]["value"]
				else:
					tax_code = "NON"
			item = frappe.db.get_all("Item",
				filters={
					"quickbooks_id": line["ItemBasedExpenseLineDetail"]["ItemRef"]["value"],
					"company": company
				},
				fields=["name", "stock_uom"]
			)[0]
			items.append({
				"item_code": item["name"],
				"conversion_factor": 1,
				"uom": item["stock_uom"],
				"description": line.get("Description", line["ItemBasedExpenseLineDetail"]["ItemRef"]["name"]),
				"qty": line["ItemBasedExpenseLineDetail"]["Qty"],
				"price_list_rate": line["ItemBasedExpenseLineDetail"]["UnitPrice"],
				"cost_center": default_cost_center,
				"item_tax_rate": json.dumps(get_item_taxes(tax_code)),
			})
		elif line["DetailType"] == "AccountBasedExpenseLineDetail":
			if line["AccountBasedExpenseLineDetail"]["TaxCodeRef"]["value"] != "TAX":
				tax_code = line["AccountBasedExpenseLineDetail"]["TaxCodeRef"]["value"]
			else:
				if "TxnTaxCodeRef" in purchase_invoice["TxnTaxDetail"]:
					tax_code = purchase_invoice["TxnTaxDetail"]["TxnTaxCodeRef"]["value"]
				else:
					tax_code = "NON"
			items.append({
				"item_name": line.get("Description", line["AccountBasedExpenseLineDetail"]["AccountRef"]["name"]),
				"conversion_factor": 1,
				"expense_account": get_account_name_by_id(line["AccountBasedExpenseLineDetail"]["AccountRef"]["value"]),
				"uom": "Unit",
				"description": line.get("Description", line["AccountBasedExpenseLineDetail"]["AccountRef"]["name"]),
				"qty": 1,
				"price_list_rate": line["Amount"],
				"cost_center": default_cost_center,
				"item_tax_rate": json.dumps(get_item_taxes(tax_code)),
			})
		if is_return:
			items[-1]["qty"] *= -1
	return items

def get_item_taxes(tax_code):
	tax_rates = get_tax_rate()
	item_taxes = {}
	if tax_code != "NON":
		tax_code = get_tax_code()[tax_code]
		for rate_list_type in ("SalesTaxRateList", "PurchaseTaxRateList"):
			if rate_list_type in tax_code:
				for tax_rate_detail in tax_code[rate_list_type]["TaxRateDetail"]:
					if tax_rate_detail["TaxTypeApplicable"] == "TaxOnAmount":
						tax_head = get_account_name_by_id("TaxRate - {}".format(tax_rate_detail["TaxRateRef"]["value"]))
						tax_rate = tax_rates[tax_rate_detail["TaxRateRef"]["value"]]
						item_taxes[tax_head] = tax_rate["RateValue"]
	return item_taxes

def get_taxes(entry):
	taxes = []
	if "TxnTaxDetail" not in entry or "TaxLine" not in entry["TxnTaxDetail"]:
		return taxes
	for line in entry["TxnTaxDetail"]["TaxLine"]:
		tax_rate = line["TaxLineDetail"]["TaxRateRef"]["value"]
		account_head = get_account_name_by_id("TaxRate - {}".format(tax_rate))
		tax_type_applicable = get_tax_type(tax_rate)
		if tax_type_applicable == "TaxOnAmount":
			taxes.append({
				"charge_type": "On Net Total",
				"account_head": account_head,
				"description": account_head,
				"cost_center": default_cost_center,
				"rate": 0,
 			})
		else:
			parent_tax_rate = get_parent_tax_rate(tax_rate)
			parent_row_id = get_parent_row_id(parent_tax_rate, taxes)
			taxes.append({
				"charge_type": "On Previous Row Amount",
				"row_id": parent_row_id,
				"account_head": account_head,
				"description": account_head,
				"cost_center": default_cost_center,
				"rate": line["TaxLineDetail"]["TaxPercent"],
			})
	return taxes

def get_tax_type(tax_rate):
	for tax_code in get_tax_code().values():
		for rate_list_type in ("SalesTaxRateList", "PurchaseTaxRateList"):
			if rate_list_type in tax_code:
				for tax_rate_detail in tax_code[rate_list_type]["TaxRateDetail"]:
					if tax_rate_detail["TaxRateRef"]["value"] == tax_rate:
						return tax_rate_detail["TaxTypeApplicable"]

def get_parent_tax_rate(tax_rate):
	parent = None
	for tax_code in get_tax_code().values():
		for rate_list_type in ("SalesTaxRateList", "PurchaseTaxRateList"):
			if rate_list_type in tax_code:
				for tax_rate_detail in tax_code[rate_list_type]["TaxRateDetail"]:
					if tax_rate_detail["TaxRateRef"]["value"] == tax_rate:
						parent = tax_rate_detail["TaxOnTaxOrder"]
				if parent:
					for tax_rate_detail in tax_code[rate_list_type]["TaxRateDetail"]:
						if tax_rate_detail["TaxOrder"] == parent:
							return tax_rate_detail["TaxRateRef"]["value"]

def get_parent_row_id(tax_rate, taxes):
	tax_account = get_account_name_by_id("TaxRate - {}".format(tax_rate))
	for index, tax in enumerate(taxes):
		if tax["account_head"] == tax_account:
			return index + 1

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
		import traceback
		traceback.print_exc()

def make_custom_fields():
	relevant_doctypes = ["Account", "Customer", "Address", "Item", "Supplier", "Sales Invoice", "Journal Entry", "Purchase Invoice", "Payment Entry"]
	for doctype in relevant_doctypes:
		make_custom_quickbooks_id_field(doctype)

	relevant_doctypes = ["Customer", "Item", "Supplier"]
	for doctype in relevant_doctypes:
		make_custom_company_field(doctype)

def make_custom_quickbooks_id_field(doctype):
	if not frappe.get_meta(doctype).has_field("quickbooks_id"):
		frappe.get_doc({
			"doctype": "Custom Field",
			"label": "QuickBooks ID",
			"dt": doctype,
			"fieldname": "quickbooks_id",
			"fieldtype": "Data",
		}).insert(ignore_permissions=True)

def make_custom_company_field(doctype):
	if not frappe.get_meta(doctype).has_field("company"):
		frappe.get_doc({
			"doctype": "Custom Field",
			"label": "Company",
			"dt": doctype,
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
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
	"TaxRate": save_tax_rate,
	"TaxCode": save_tax_code,
	"Purchase": save_purchase,
	"Deposit": save_deposit,
	"VendorCredit": save_vendor_credit,
	"CreditMemo": save_credit_memo,
	"SalesReceipt": save_sales_receipt,
	"Advance Payment": save_advance_payment,
	"Preferences": save_preference,
	"Tax Payment": save_tax_payment,
	"Sales Tax Payment": save_tax_payment,
	"Purchase Tax Payment": save_tax_payment,
}

def save_entries(doctype, entries):
	total = len(entries)
	save = save_methods[doctype]
	for index, entry in enumerate(entries):
		publish({"event": "save", "doctype": doctype, "count": index, "total": total})
		save(entry)
	frappe.db.commit()

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

	cache_key = "quickbooks-cached-{}".format(entity)
	if not frappe.cache().exists(cache_key):
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
		frappe.cache().set(cache_key, json.dumps(entries))
		publish({"event": "finish"})
	entries = json.loads(frappe.cache().get(cache_key).decode())
	save_entries(entity, entries)
	publish({"event": "finish"})
	publish({"event": "message", "message": "Fetched {}".format(entity)})

def fetch_all_entries_from_gl(company_id=None, entity=None):
	general_ledger = get_general_ledger()
	if entity in general_ledger:
		save_entries(entity, general_ledger[entity].values())
		publish({"event": "finish"})
		publish({"event": "message", "message": "Fetched {}".format(entity)})

def get_headers(token):
	return {"Accept": "application/json",
	"Authorization": "Bearer {}".format(token)}

class QuickBooksMigrator(Document):
	pass

def get_account_name_by_id(quickbooks_id):
	return frappe.get_all("Account", filters={"quickbooks_id": quickbooks_id, "company": company})[0]["name"]

def zen():
	rise()
	frappe.db.sql("""DELETE from tabAccount where name like "%QB%" """)
	frappe.db.commit()

def rise():
	for doctype in ["Payment Entry", "Journal Entry", "Purchase Invoice", "Sales Invoice"]:
		for doc in frappe.get_all(doctype, filters=[["quickbooks_id", "not like", ""]]):
			try: frappe.get_doc(doctype, doc["name"]).cancel()
			except: pass
			try: frappe.delete_doc(doctype, doc["name"])
			except: pass

	for doctype in ["Customer", "Supplier", "Item"]:
		for doc in frappe.get_all(doctype, filters=[["quickbooks_id", "not like", ""]]):
			try:frappe.delete_doc(doctype, doc["name"])
			except: pass
	frappe.db.commit()

def get_tax_code():
	tax_codes = json.loads(frappe.cache().get("quickbooks-cached-TaxCode").decode())
	return {tax_code["Id"]: tax_code for tax_code in tax_codes}

def get_tax_rate():
	tax_rates = json.loads(frappe.cache().get("quickbooks-cached-TaxRate").decode())
	return {tax_rate["Id"]: tax_rate for tax_rate in tax_rates}

def get_shipping_account():
	shipping_account_id = frappe.cache().get("quickbooks-cached-shipping-account-id").decode()
	return get_account_name_by_id(shipping_account_id)

def get_undeposited_funds_account():
	undeposited_funds_account_id = frappe.cache().get("quickbooks-cached-undeposited-funds-account-id").decode()
	return get_account_name_by_id(undeposited_funds_account_id)

def is_group_account(account_id):
	accounts = json.loads(frappe.cache().get("quickbooks-cached-Account").decode())
	return any(account["SubAccount"] and account["ParentRef"]["value"] == account_id for account in accounts)

def get_unique_account_name(quickbooks_name, number=0):
	if number:
		quickbooks_account_name = "{} - {} - QB".format(quickbooks_name, number)
	else:
		quickbooks_account_name = "{} - QB".format(quickbooks_name)
	company_encoded_account_name = encode_company_abbr(quickbooks_account_name, company)
	if frappe.db.exists({"doctype": "Account", "name": company_encoded_account_name, "company": company}):
		unique_account_name = get_unique_account_name(quickbooks_name, number + 1)
	else:
		unique_account_name = quickbooks_account_name
	return unique_account_name


gl_entries = {}
def get_gl_entries_from_section(section, account=None):
	if "Header" in section and "id" in section["Header"]["ColData"][0]:
		account = get_account_name_by_id(section["Header"]["ColData"][0].get("id", 38))
	entries = []
	for row in section["Rows"]["Row"]:
		if row["type"] == "Data":
			data = row["ColData"]
			entries.append({
				"account": account,
				"date": data[0]["value"],
				"type": data[1]["value"],
				"id": data[1]["id"],
				"credit": frappe.utils.flt(data[2]["value"]),
				"debit": frappe.utils.flt(data[3]["value"]),
				"amount": frappe.utils.flt(data[4]["value"]),
			})
		if row["type"] == "Section":
			get_gl_entries_from_section(row, account)
	gl_entries.setdefault(account, []).extend(entries)

def fetch_general_ledger(company_id):
	if not frappe.cache().exists("quickbooks-cached-General-Ledger"):
		general_ledger = get((BASE_QUERY_URL + "/{}").format(company_id, "reports", "GeneralLedger"), params={
			"columns": ",".join(["tx_date", "txn_type", "credit_amt", "debt_amt" , "subt_nat_amount"]),
			"date_macro": "All",
			"minorversion": 3,
		}).json()
		for section in general_ledger["Rows"]["Row"]:
			if section["type"] == "Section":
				get_gl_entries_from_section(section)
		general_ledger = {}
		for account in gl_entries.values():
			for line in account:
				type_dict = general_ledger.setdefault(line["type"], {})
				if line["id"] not in type_dict:
					type_dict[line["id"]] = {
						"id": line["id"],
						"date": line["date"],
						"lines": [],
					}
				type_dict[line["id"]]["lines"].append(line)
		frappe.cache().set("quickbooks-cached-General-Ledger", json.dumps(general_ledger))

def get_general_ledger():
	return json.loads(frappe.cache().get("quickbooks-cached-General-Ledger").decode())
