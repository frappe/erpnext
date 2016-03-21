# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.setup.setup_wizard.setup_wizard import create_bank_account

def create_payment_gateway_and_account(doc, method):
	"""Called via hook on saving Paypal Settings of Paypal Integration app"""
	create_payment_gateway()
	create_payment_gateway_account()

def create_payment_gateway():
	# NOTE: we don't translate Payment Gateway name because it is an internal doctype
	if not frappe.db.exists("Payment Gateway", "PayPal"):
		payment_gateway = frappe.get_doc({
			"doctype": "Payment Gateway",
			"gateway": "PayPal"
		})
		payment_gateway.insert(ignore_permissions=True)

def create_payment_gateway_account():
	company = frappe.db.get_value("Global Defaults", None, "default_company")
	if not company:
		return

	# NOTE: we translate Payment Gateway account name because that is going to be used by the end user
	bank_account = frappe.db.get_value("Account", {"account_name": _("PayPal"), "company": company},
		["name", 'account_currency'], as_dict=1)

	if not bank_account:
		# check for untranslated one
		bank_account = frappe.db.get_value("Account", {"account_name": "PayPal", "company": company},
			["name", 'account_currency'], as_dict=1)

	if not bank_account:
		# try creating one
		bank_account = create_bank_account({"company_name": company, "bank_account": _("PayPal")})

	if not bank_account:
		frappe.msgprint(_("Payment Gateway Account not created, please create one manually."))
		return

	# if payment gateway account exists, return
	if frappe.db.exists("Payment Gateway Account",
		{"payment_gateway": "PayPal", "currency": bank_account.account_currency}):
		return

	try:
		frappe.get_doc({
			"doctype": "Payment Gateway Account",
			"is_default": 1,
			"payment_gateway": "PayPal",
			"payment_account": bank_account.name,
			"currency": bank_account.account_currency
		}).insert(ignore_permissions=True)

	except frappe.DuplicateEntryError:
		# already exists, due to a reinstall?
		pass
