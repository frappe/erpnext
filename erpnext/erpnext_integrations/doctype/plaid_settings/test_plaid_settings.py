# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import unittest
import frappe
from erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings import plaid_configuration, add_account_type, add_account_subtype, new_bank_transaction, get_transactions, add_bank_accounts
import json
from frappe.utils.response import json_handler
from erpnext.accounts.doctype.journal_entry.journal_entry import get_default_bank_cash_account

class TestPlaidSettings(unittest.TestCase):
	def setUp(self):
		pass

	def tearDown(self):
		for bt in frappe.get_all("Bank Transaction"):
			doc = frappe.get_doc("Bank Transaction", bt.name)
			doc.cancel()
			doc.delete()

		for ba in frappe.get_all("Bank Account"):
			frappe.get_doc("Bank Account", ba.name).delete()

		for at in frappe.get_all("Account Type"):
			frappe.get_doc("Account Type", at.name).delete()

		for ast in frappe.get_all("Account Subtype"):
			frappe.get_doc("Account Subtype", ast.name).delete()

	def test_plaid_disabled(self):
		frappe.db.set_value("Plaid Settings", None, "enabled", 0)
		self.assertTrue(plaid_configuration() == "disabled")

	def test_add_account_type(self):
		add_account_type("brokerage")
		self.assertEqual(frappe.get_doc("Account Type", "brokerage").name, "brokerage")

	def test_add_account_subtype(self):
		add_account_subtype("loan")
		self.assertEqual(frappe.get_doc("Account Subtype", "loan").name, "loan")

	def test_default_bank_account(self):
		if not frappe.db.exists("Bank", "Citi"):
			frappe.get_doc({
				"doctype": "Bank",
				"bank_name": "Citi"
			}).insert()

		bank_accounts = {
			'account': {
				'subtype': 'checking',
				'mask': '0000',
				'type': 'depository',
				'id': '6GbM6RRQgdfy3lAqGz4JUnpmR948WZFg8DjQK',
				'name': 'Plaid Checking'
			},
			'account_id': '6GbM6RRQgdfy3lAqGz4JUnpmR948WZFg8DjQK',
			'link_session_id': 'db673d75-61aa-442a-864f-9b3f174f3725',
			'accounts': [{
				'type': 'depository',
				'subtype': 'checking',
				'mask': '0000',
				'id': '6GbM6RRQgdfy3lAqGz4JUnpmR948WZFg8DjQK',
				'name': 'Plaid Checking'
				}],
			'institution': {
				'institution_id': 'ins_6',
				'name': 'Citi'
			}
		}

		bank = json.dumps(frappe.get_doc("Bank", "Citi").as_dict(), default=json_handler)
		company = frappe.db.get_single_value('Global Defaults', 'default_company')
		frappe.db.set_value("Company", company, "default_bank_account", None)

		self.assertRaises(frappe.ValidationError, add_bank_accounts, response=bank_accounts, bank=bank, company=company)

	def test_new_transaction(self):
		if not frappe.db.exists("Bank", "Citi"):
			frappe.get_doc({
				"doctype": "Bank",
				"bank_name": "Citi"
			}).insert()

		bank_accounts = {
			'account': {
				'subtype': 'checking',
				'mask': '0000',
				'type': 'depository',
				'id': '6GbM6RRQgdfy3lAqGz4JUnpmR948WZFg8DjQK',
				'name': 'Plaid Checking'
			},
			'account_id': '6GbM6RRQgdfy3lAqGz4JUnpmR948WZFg8DjQK',
			'link_session_id': 'db673d75-61aa-442a-864f-9b3f174f3725',
			'accounts': [{
				'type': 'depository',
				'subtype': 'checking',
				'mask': '0000',
				'id': '6GbM6RRQgdfy3lAqGz4JUnpmR948WZFg8DjQK',
				'name': 'Plaid Checking'
				}],
			'institution': {
				'institution_id': 'ins_6',
				'name': 'Citi'
			}
		}

		bank = json.dumps(frappe.get_doc("Bank", "Citi").as_dict(), default=json_handler)
		company = frappe.db.get_single_value('Global Defaults', 'default_company')

		if frappe.db.get_value("Company", company, "default_bank_account") is None:
			frappe.db.set_value("Company", company, "default_bank_account", get_default_bank_cash_account(company, "Cash").get("account"))

		add_bank_accounts(bank_accounts, bank, company)

		transactions = {
			'account_owner': None,
			'category': ['Food and Drink', 'Restaurants'],
			'account_id': 'b4Jkp1LJDZiPgojpr1ansXJrj5Q6w9fVmv6ov',
			'pending_transaction_id': None,
			'transaction_id': 'x374xPa7DvUewqlR5mjNIeGK8r8rl3Sn647LM',
			'unofficial_currency_code': None,
			'name': 'INTRST PYMNT',
			'transaction_type': 'place',
			'amount': -4.22,
			'location': {
				'city': None,
				'zip': None,
				'store_number': None,
				'lon': None,
				'state': None,
				'address': None,
				'lat': None
			},
			'payment_meta': {
				'reference_number': None,
				'payer': None,
				'payment_method': None,
				'reason': None,
				'payee': None,
				'ppd_id': None,
				'payment_processor': None,
				'by_order_of': None
			},
			'date': '2017-12-22',
			'category_id': '13005000',
			'pending': False,
			'iso_currency_code': 'USD'
		}

		new_bank_transaction(transactions)

		self.assertTrue(len(frappe.get_all("Bank Transaction")) == 1)


	



	