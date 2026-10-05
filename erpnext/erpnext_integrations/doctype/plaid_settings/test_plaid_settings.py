# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.utils.response import json_handler

from erpnext.erpnext_integrations.doctype.plaid_settings.plaid_connector import PlaidConnector
from erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings import (
	add_account_subtype,
	add_account_type,
	add_bank_accounts,
	enqueue_synchronization,
	get_plaid_configuration,
	new_bank_transaction,
	sync_transactions,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestPlaidSettings(ERPNextTestSuite):
	def test_plaid_disabled(self):
		frappe.db.set_single_value("Plaid Settings", "enabled", 0)
		self.assertEqual(get_plaid_configuration(), "disabled")

	def test_add_account_type(self):
		add_account_type("brokerage")
		self.assertEqual(frappe.get_doc("Bank Account Type", "brokerage").name, "brokerage")

	def test_add_account_subtype(self):
		add_account_subtype("loan")
		self.assertEqual(frappe.get_doc("Bank Account Subtype", "loan").name, "loan")

	def test_new_transaction(self):
		if not frappe.db.exists("Bank", "Citi"):
			frappe.get_doc({"doctype": "Bank", "bank_name": "Citi"}).insert()

		bank_accounts = {
			"account": {
				"subtype": "checking",
				"mask": "0000",
				"type": "depository",
				"id": "6GbM6RRQgdfy3lAqGz4JUnpmR948WZFg8DjQK",
				"name": "Plaid Checking",
			},
			"account_id": "6GbM6RRQgdfy3lAqGz4JUnpmR948WZFg8DjQK",
			"link_session_id": "db673d75-61aa-442a-864f-9b3f174f3725",
			"accounts": [
				{
					"type": "depository",
					"subtype": "checking",
					"mask": "0000",
					"id": "6GbM6RRQgdfy3lAqGz4JUnpmR948WZFg8DjQK",
					"name": "Plaid Checking",
				}
			],
			"institution": {"institution_id": "ins_6", "name": "Citi"},
		}

		bank = json.dumps(frappe.get_doc("Bank", "Citi").as_dict(), default=json_handler)
		company = "_Test Company"

		add_bank_accounts(bank_accounts, bank, company)

		transactions = {
			"account_owner": None,
			"category": ["Food and Drink", "Restaurants"],
			"account_id": "b4Jkp1LJDZiPgojpr1ansXJrj5Q6w9fVmv6ov",
			"pending_transaction_id": None,
			"transaction_id": "x374xPa7DvUewqlR5mjNIeGK8r8rl3Sn647LM",
			"unofficial_currency_code": None,
			"name": "INTRST PYMNT",
			"transaction_type": "place",
			"transaction_code": "direct debit",
			"check_number": "3456789",
			"amount": -4.22,
			"location": {
				"city": None,
				"zip": None,
				"store_number": None,
				"lon": None,
				"state": None,
				"address": None,
				"lat": None,
			},
			"payment_meta": {
				"reference_number": None,
				"payer": None,
				"payment_method": None,
				"reason": None,
				"payee": None,
				"ppd_id": None,
				"payment_processor": None,
				"by_order_of": None,
			},
			"date": "2017-12-22",
			"category_id": "13005000",
			"pending": False,
			"iso_currency_code": "USD",
		}

		new_bank_transaction(transactions)

		self.assertEqual(len(frappe.get_all("Bank Transaction")), 1)

	def test_get_transactions_keeps_the_account_filter_on_every_page(self):
		rows = {
			account_id: [
				{"account_id": account_id, "transaction_id": f"{account_id}-{n}"} for n in range(150)
			]
			for account_id in ("acc-1", "acc-2")
		}

		def get_page(access_token, start_date, end_date, account_ids=None, offset=0):
			matching = [row for account_id in account_ids or rows for row in rows[account_id]]
			return {"transactions": matching[offset : offset + 100], "total_transactions": len(matching)}

		connector = PlaidConnector.__new__(PlaidConnector)
		connector.access_token = "access-test"
		connector.client = MagicMock()
		connector.client.Transactions.get.side_effect = get_page

		transactions = connector.get_transactions("2026-01-01", "2026-06-30", account_id="acc-1")
		self.assertEqual(transactions, rows["acc-1"])

	def test_sync_skips_a_failing_transaction(self):
		bank_account = link_test_bank_account("plaid-sync-test")
		rows = [
			make_plaid_transaction("plaid-sync-test", f"plaid-sync-test-{n}", currency)
			for n, currency in enumerate(["INR", "INR", "USD"])
		]

		with (
			patch(f"{PLAID_SETTINGS}.get_transactions", return_value=rows),
			patch("frappe.log_error") as log_error,
		):
			sync_transactions("Citi", bank_account)

		imported = frappe.get_all("Bank Transaction", {"bank_account": bank_account}, pluck="transaction_id")
		self.assertCountEqual(imported, ["plaid-sync-test-0", "plaid-sync-test-1"])
		log_error.assert_called_once()

	def test_linking_does_not_take_over_a_party_bank_account(self):
		if not frappe.db.exists("Bank", "Citi"):
			frappe.get_doc({"doctype": "Bank", "bank_name": "Citi"}).insert()
		party_account = frappe.get_doc(
			{
				"doctype": "Bank Account",
				"account_name": "Plaid plaid-link-test",
				"bank": "Citi",
				"party_type": "Customer",
				"party": "_Test Customer",
			}
		).insert()

		bank_account = link_test_bank_account("plaid-link-test")

		self.assertNotEqual(bank_account, party_account.name)
		self.assertEqual(frappe.db.get_value("Bank Account", bank_account, "company"), "_Test Company")
		self.assertFalse(frappe.db.get_value("Bank Account", party_account.name, "integration_id"))

	def test_scheduled_sync_skips_disabled_accounts(self):
		active_account = link_test_bank_account("plaid-active-test")
		disabled_account = link_test_bank_account("plaid-disabled-test")
		frappe.db.set_value("Bank Account", disabled_account, "disabled", 1)

		with patch("frappe.enqueue") as enqueue:
			enqueue_synchronization()

		synced = [call.kwargs["bank_account"] for call in enqueue.call_args_list]
		self.assertIn(active_account, synced)
		self.assertNotIn(disabled_account, synced)


PLAID_SETTINGS = "erpnext.erpnext_integrations.doctype.plaid_settings.plaid_settings"


def link_test_bank_account(account_id: str) -> str:
	"""Link a Plaid account of the Citi bank to _Test Company and return its Bank Account."""
	if not frappe.db.exists("Bank", "Citi"):
		frappe.get_doc({"doctype": "Bank", "bank_name": "Citi"}).insert()

	account = {"id": account_id, "name": f"Plaid {account_id}", "type": "depository", "subtype": "checking"}
	response = {"accounts": [account], "institution": {"institution_id": "ins_6", "name": "Citi"}}
	bank = json.dumps(frappe.get_doc("Bank", "Citi").as_dict(), default=json_handler)
	return add_bank_accounts(response, bank, "_Test Company")[0]


def make_plaid_transaction(account_id: str, transaction_id: str, currency: str) -> dict:
	return {
		"account_id": account_id,
		"transaction_id": transaction_id,
		"amount": 10.0,
		"date": "2026-01-15",
		"iso_currency_code": currency,
		"pending": False,
		"category": None,
		"name": transaction_id,
		"transaction_code": None,
		"check_number": None,
		"payment_meta": {"payment_method": None, "reference_number": None},
	}
