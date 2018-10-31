# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
from erpnext.erpnext_integrations.doctype.plaid_settings.plaid_connector import PlaidConnector
from frappe.utils import getdate, formatdate, today, add_months

class PlaidSettings(Document):
	pass

@frappe.whitelist()
def plaid_configuration():
	return {"plaid_public_key": frappe.conf.get("plaid_public_key") or None, "plaid_env": frappe.conf.get("plaid_env") or None, "client_name": frappe.local.site }


@frappe.whitelist()
def add_institution(token, response):
	response = json.loads(response)
	frappe.log_error(response)

	plaid = PlaidConnector()
	access_token = plaid.get_access_token(token)

	if not frappe.db.exists("Bank", response["institution"]["name"]):
		try:
			bank = frappe.get_doc({
				"doctype": "Bank",
				"bank_name": response["institution"]["name"],
				"plaid_access_token": access_token
			})
			bank.insert()
		except Exception:
			frappe.throw(frappe.get_traceback())

	else:
		bank = frappe.get_doc("Bank", response["institution"]["name"])
		bank.plaid_access_token = access_token
		bank.save()

	return bank

@frappe.whitelist()
def add_bank_accounts(response, bank):
	response = json.loads(response)
	bank = json.loads(bank)
	company = "Dokos"
	result = []
	default_gl_account = get_default_bank_cash_account(company, "Bank")

	for account in response["accounts"]:
		acc_type = frappe.db.get_value("Account Type", account["type"])
		if not acc_type:
			add_account_type(account["type"])

		acc_subtype = frappe.db.get_value("Account Subtype", account["subtype"])
		if not acc_subtype:
			add_account_subtype(account["subtype"])

		if not frappe.db.exists("Bank Account", dict(integration_id=account["id"])):
			try:
				new_account = frappe.get_doc({
					"doctype": "Bank Account",
					"bank": bank["bank_name"],
					"account": default_gl_account.account,
					"account_name": account["name"],
					"account_type": account["type"] or "",
					"account_subtype": account["subtype"] or "",
					"mask": account["mask"] or "",
					"integration_id": account["id"],
					"is_company_account": 1,
					"company": company
				})
				new_account.insert()

				result.append(new_account.name)

			except Exception:
				frappe.throw(frappe.get_traceback())

		else:
			result.append(frappe.db.get_value("Bank Account", dict(integration_id=account["id"]), "name"))

	return result

def add_account_type(account_type):
	try:
		frappe.get_doc({
			"doctype": "Account Type",
			"account_type": account_type
		}).insert()
	except:
		frappe.throw(frappe.get_traceback())


def add_account_subtype(account_subtype):
	try:
		frappe.get_doc({
			"doctype": "Account Subtype",
			"account_subtype": account_subtype
		}).insert()
	except:
		frappe.throw(frappe.get_traceback())

@frappe.whitelist()
def sync_transactions(bank, bank_account=None):

	last_sync_date = frappe.db.get_value("Plaid Settings", None, "last_sync_date")
	if last_sync_date:
		start_date = formatdate(last_sync_date, "YYYY-MM-dd")
	else:
		start_date = formatdate(add_months(today(), -12), "YYYY-MM-dd")
	end_date = formatdate(today(), "YYYY-MM-dd")

	try:
		transactions = get_transactions(bank=bank, bank_account=bank_account, start_date=start_date, end_date=end_date)
		result = []
		if transactions:
			for transaction in transactions:
				result.append(new_bank_transaction(transaction))

		frappe.db.set_value("Plaid Settings", None, "last_sync_date", getdate(end_date))

		return result
	except Exception:
		frappe.log_error(frappe.get_traceback(), _("Plaid transactions sync error"))


def get_transactions(bank, bank_account=None, start_date=None, end_date=None):
	access_token = None

	if bank_account:
		related_bank = frappe.db.get_values("Bank Account", dict(account_name=bank_account), ["bank", "integration_id"], as_dict=True)
		access_token = frappe.db.get_value("Bank", related_bank[0].bank, "plaid_access_token")
		account_id = related_bank[0].integration_id

	else:
		access_token = frappe.db.get_value("Bank", bank, "plaid_access_token")
		account_id = None

	plaid = PlaidConnector(access_token)
	transactions = plaid.get_transactions(start_date=start_date, end_date=end_date, account_id=account_id)

	return transactions

def new_bank_transaction(transaction):
	result = []

	bank_account = frappe.db.get_value("Bank Account", dict(integration_id=transaction["account_id"]))

	if float(transaction["amount"]) >= 0:
		debit = float(transaction["amount"])
		credit = 0
	else:
		debit = 0
		credit = abs(float(transaction["amount"]))

	status = "Pending" if transaction["pending"] == "True" else "Settled"

	if not frappe.db.exists("Bank Transaction", dict(transaction_id=transaction["transaction_id"])):
		try:
			new_transaction = frappe.get_doc({
				"doctype": "Bank Transaction",
				"date": getdate(transaction["date"]),
				"status": status,
				"bank_account": bank_account,
				"debit": debit,
				"credit": credit,
				"currency": transaction["iso_currency_code"],
				"description": transaction["name"]
			})
			new_transaction.insert()

			result.append(new_transaction.name)

		except Exception:
			frappe.throw(frappe.get_traceback())

	return result
