# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account
from erpnext.erpnext_integrations.doctype.plaid_settings.plaid_connector import PlaidConnector
from frappe import _
from frappe.desk.doctype.tag.tag import add_tag
from frappe.model.document import Document
from frappe.utils import add_months, formatdate, getdate, today

from plaid.errors import ItemError

class PlaidSettings(Document):
	@staticmethod
	@frappe.whitelist()
	def get_link_token():
		plaid = PlaidConnector()
		return plaid.get_link_token()


@frappe.whitelist()
def get_plaid_configuration():
	if frappe.db.get_single_value("Plaid Settings", "enabled"):
		plaid_settings = frappe.get_single("Plaid Settings")
		return {
			"plaid_env": plaid_settings.plaid_env,
			"link_token": plaid_settings.get_link_token(),
			"client_name": frappe.local.site
		}

	return "disabled"


@frappe.whitelist()
def add_institution(token, response):
	response = json.loads(response)

	plaid = PlaidConnector()
	access_token = plaid.get_access_token(token)
	bank = None

	if not frappe.db.exists("Bank", response["institution"]["name"]):
		try:
			bank = frappe.get_doc({
				"doctype": "Bank",
				"bank_name": response["institution"]["name"],
				"plaid_access_token": access_token
			})
			bank.insert()
		except Exception:
			frappe.log_error(frappe.get_traceback(), title=_('Plaid Link Error'))
	else:
		bank = frappe.get_doc("Bank", response["institution"]["name"])
		bank.plaid_access_token = access_token
		bank.save()

	return bank


@frappe.whitelist()
def add_bank_accounts(response, bank, company):
	try:
		response = json.loads(response)
	except TypeError:
		pass

	bank = json.loads(bank)
	result = []

	default_gl_account = get_default_bank_cash_account(company, "Bank")
	if not default_gl_account:
		frappe.throw(_("Please setup a default bank account for company {0}").format(company))

	for account in response["accounts"]:
		acc_type = frappe.db.get_value("Bank Account Type", account["type"])
		if not acc_type:
			add_account_type(account["type"])

		acc_subtype = frappe.db.get_value("Bank Account Subtype", account["subtype"])
		if not acc_subtype:
			add_account_subtype(account["subtype"])

		existing_bank_account = frappe.db.exists("Bank Account", {
			'account_name': account["name"],
			'bank': bank["bank_name"]
		})

		if not existing_bank_account:
			try:
				new_account = frappe.get_doc({
					"doctype": "Bank Account",
					"bank": bank["bank_name"],
					"account": default_gl_account.account,
					"account_name": account["name"],
					"account_type": account.get("type", ""),
					"account_subtype": account.get("subtype", ""),
					"mask": account.get("mask", ""),
					"integration_id": account["id"],
					"is_company_account": 1,
					"company": company
				})
				new_account.insert()

				result.append(new_account.name)
			except frappe.UniqueValidationError:
				frappe.msgprint(_("Bank account {0} already exists and could not be created again").format(account["name"]))
			except Exception:
				frappe.log_error(frappe.get_traceback(), title=_("Plaid Link Error"))
				frappe.throw(_("There was an error creating Bank Account while linking with Plaid."), 
					title=_("Plaid Link Failed"))

		else:
			try:
				existing_account = frappe.get_doc('Bank Account', existing_bank_account)
				existing_account.update({
					"bank": bank["bank_name"],
					"account_name": account["name"],
					"account_type": account.get("type", ""),
					"account_subtype": account.get("subtype", ""),
					"mask": account.get("mask", ""),
					"integration_id": account["id"]
				})
				existing_account.save()
				result.append(existing_bank_account)
			except Exception:
				frappe.log_error(frappe.get_traceback(), title=_("Plaid Link Error"))
				frappe.throw(_("There was an error updating Bank Account {} while linking with Plaid.").format(
					existing_bank_account), title=_("Plaid Link Failed"))

	return result


def add_account_type(account_type):
	try:
		frappe.get_doc({
			"doctype": "Bank Account Type",
			"account_type": account_type
		}).insert()
	except Exception:
		frappe.throw(frappe.get_traceback())


def add_account_subtype(account_subtype):
	try:
		frappe.get_doc({
			"doctype": "Bank Account Subtype",
			"account_subtype": account_subtype
		}).insert()
	except Exception:
		frappe.throw(frappe.get_traceback())


@frappe.whitelist()
def sync_transactions(bank, bank_account):
	"""Sync transactions based on the last integration date as the start date, after sync is completed
	add the transaction date of the oldest transaction as the last integration date."""
	last_transaction_date = frappe.db.get_value("Bank Account", bank_account, "last_integration_date")
	if last_transaction_date:
		start_date = formatdate(last_transaction_date, "YYYY-MM-dd")
	else:
		start_date = formatdate(add_months(today(), -12), "YYYY-MM-dd")
	end_date = formatdate(today(), "YYYY-MM-dd")

	try:
		transactions = get_transactions(bank=bank, bank_account=bank_account, start_date=start_date, end_date=end_date)

		result = []
		for transaction in reversed(transactions):
			result += new_bank_transaction(transaction)

		if result:
			last_transaction_date = frappe.db.get_value('Bank Transaction', result.pop(), 'date')

			frappe.logger().info("Plaid added {} new Bank Transactions from '{}' between {} and {}".format(
				len(result), bank_account, start_date, end_date))

			frappe.db.set_value("Bank Account", bank_account, "last_integration_date", last_transaction_date)
	except Exception:
		frappe.log_error(frappe.get_traceback(), _("Plaid transactions sync error"))


def get_transactions(bank, bank_account=None, start_date=None, end_date=None):
	access_token = None

	if bank_account:
		related_bank = frappe.db.get_values("Bank Account", bank_account, ["bank", "integration_id"], as_dict=True)
		access_token = frappe.db.get_value("Bank", related_bank[0].bank, "plaid_access_token")
		account_id = related_bank[0].integration_id
	else:
		access_token = frappe.db.get_value("Bank", bank, "plaid_access_token")
		account_id = None

	plaid = PlaidConnector(access_token)

	try:
		transactions = plaid.get_transactions(start_date=start_date, end_date=end_date, account_id=account_id)
	except ItemError as e:
		if e.code == "ITEM_LOGIN_REQUIRED":
			msg = _("There was an error syncing transactions.") + " "
			msg += _("Please refresh or reset the Plaid linking of the Bank {}.").format(bank) + " "
			frappe.log_error(msg, title=_("Plaid Link Refresh Required"))

	return transactions or []


def new_bank_transaction(transaction):
	result = []

	bank_account = frappe.db.get_value("Bank Account", dict(integration_id=transaction["account_id"]))

	if float(transaction["amount"]) >= 0:
		debit = 0
		credit = float(transaction["amount"])
	else:
		debit = abs(float(transaction["amount"]))
		credit = 0

	status = "Pending" if transaction["pending"] == "True" else "Settled"

	tags = []
	try:
		tags += transaction["category"]
		tags += ["Plaid Cat. {}".format(transaction["category_id"])]
	except KeyError:
		pass

	if not frappe.db.exists("Bank Transaction", dict(transaction_id=transaction["transaction_id"])):
		try:
			new_transaction = frappe.get_doc({
				"doctype": "Bank Transaction",
				"date": getdate(transaction["date"]),
				"status": status,
				"bank_account": bank_account,
				"deposit": debit,
				"withdrawal": credit,
				"currency": transaction["iso_currency_code"],
				"transaction_id": transaction["transaction_id"],
				"reference_number": transaction["payment_meta"]["reference_number"],
				"description": transaction["name"]
			})
			new_transaction.insert()
			new_transaction.submit()

			for tag in tags:
				add_tag(tag, "Bank Transaction", new_transaction.name)

			result.append(new_transaction.name)

		except Exception:
			frappe.throw(title=_('Bank transaction creation error'))

	return result


def automatic_synchronization():
	settings = frappe.get_doc("Plaid Settings", "Plaid Settings")
	if settings.enabled == 1 and settings.automatic_sync == 1:
		enqueue_synchronization()

@frappe.whitelist()
def enqueue_synchronization():
	plaid_accounts = frappe.get_all("Bank Account",
		filters={"integration_id": ["!=", ""]},
		fields=["name", "bank"])

	for plaid_account in plaid_accounts:
		frappe.enqueue(
			"erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings.sync_transactions",
			bank=plaid_account.bank,
			bank_account=plaid_account.name
		)

@frappe.whitelist()
def get_link_token_for_update(access_token):
	plaid = PlaidConnector(access_token)
	return plaid.get_link_token(update_mode=True)
