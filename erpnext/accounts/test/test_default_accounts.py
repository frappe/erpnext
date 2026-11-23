# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.default_accounts import (
	DEFAULT_ACCOUNT_PURPOSES,
	EXCHANGE_GAIN,
	EXCHANGE_GAIN_LOSS,
	EXCHANGE_LOSS,
	PURCHASE_EXPENSE,
	RECEIVABLE,
	get_default_account,
	get_purpose,
	get_purpose_options,
	get_purposes,
	set_default_account,
)
from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.tests.utils import ERPNextTestSuite

COMPANY = "_Test Company"


class TestDefaultAccounts(ERPNextTestSuite):
	def test_registry_matches_company_account_fields(self):
		company_json = frappe.get_file_json(
			frappe.get_app_path("erpnext", "setup", "doctype", "company", "company.json")
		)
		account_fields = {
			df["fieldname"]: df["label"]
			for df in company_json["fields"]
			if df["fieldtype"] == "Link" and df.get("options") == "Account"
		}
		registry_fields = {purpose.fieldname: purpose.label for purpose in DEFAULT_ACCOUNT_PURPOSES}

		self.assertEqual(registry_fields, account_fields)
		for purpose in DEFAULT_ACCOUNT_PURPOSES:
			self.assertEqual(purpose.key, purpose.key.upper())
			if purpose.fallback:
				self.assertIn(purpose.fallback, get_purposes())

	def test_get_and_set_default_account(self):
		receivable = frappe.db.get_value(
			"Account", {"company": COMPANY, "account_type": "Receivable", "is_group": 0}
		)
		set_default_account(COMPANY, RECEIVABLE, receivable)

		self.assertEqual(
			frappe.db.get_value("Company", COMPANY, "default_receivable_account"),
			receivable,
		)
		self.assertEqual(get_default_account(COMPANY, RECEIVABLE), receivable)

	def test_fallback_and_required(self):
		gain_loss = frappe.db.get_value("Account", {"company": COMPANY, "root_type": "Income", "is_group": 0})
		set_default_account(COMPANY, EXCHANGE_GAIN_LOSS, gain_loss)
		set_default_account(COMPANY, EXCHANGE_GAIN, None)
		set_default_account(COMPANY, EXCHANGE_LOSS, None)

		self.assertEqual(get_default_account(COMPANY, EXCHANGE_GAIN), gain_loss)
		self.assertEqual(get_default_account(COMPANY, EXCHANGE_LOSS, required=True), gain_loss)

		set_default_account(COMPANY, EXCHANGE_GAIN_LOSS, None)
		self.assertIsNone(get_default_account(COMPANY, EXCHANGE_GAIN))
		with self.assertRaises(frappe.ValidationError):
			get_default_account(COMPANY, EXCHANGE_GAIN, required=True)

	def test_no_company(self):
		self.assertIsNone(get_default_account(None, RECEIVABLE))
		self.assertIsNone(get_default_account("", RECEIVABLE))

	def test_company_methods_work_in_memory(self):
		company = frappe.get_doc("Company", COMPANY)
		account = company.default_expense_account
		company.set_default_account(PURCHASE_EXPENSE, account)

		self.assertEqual(company.purchase_expense_account, account)
		self.assertEqual(company.get_default_account(PURCHASE_EXPENSE), account)

	def test_unknown_purpose(self):
		with self.assertRaises(frappe.ValidationError):
			get_purpose("NO_SUCH_PURPOSE")

	def test_get_purpose_options(self):
		options = {option["value"]: option for option in get_purpose_options()}

		self.assertEqual(list(options), [purpose.key for purpose in DEFAULT_ACCOUNT_PURPOSES])
		self.assertEqual(
			options[RECEIVABLE],
			{
				"value": RECEIVABLE,
				"label": "Default Receivable Account",
				"filters": {"root_type": "Asset", "account_type": "Receivable"},
				"fieldname": "default_receivable_account",
			},
		)

	def test_purposes_from_hook(self):
		hook_entry = {
			"key": "TEST_PURPOSE",
			"label": "Test Purpose Account",
			"filters": {"root_type": "Expense"},
			"fieldname": "write_off_account",
		}
		get_hooks = frappe.get_hooks

		def get_hooks_with_test_purpose(hook=None, *args, **kwargs):
			if hook == "company_default_accounts":
				return [hook_entry]
			return get_hooks(hook, *args, **kwargs)

		with patch("frappe.get_hooks", side_effect=get_hooks_with_test_purpose):
			self.assertEqual(get_purpose("TEST_PURPOSE").label, "Test Purpose Account")
			self.assertEqual(list(get_purposes())[-1], "TEST_PURPOSE")
			self.assertEqual(
				get_default_account(COMPANY, "TEST_PURPOSE"),
				frappe.db.get_value("Company", COMPANY, "write_off_account"),
			)

	def test_account_used_as_default_cannot_be_disabled(self):
		account = create_account(
			account_name="_Test Default Purchase Expense",
			parent_account="Indirect Expenses - _TC",
			company=COMPANY,
		)
		company = frappe.get_doc("Company", COMPANY)
		company.set_default_account(PURCHASE_EXPENSE, account)
		company.save()

		account_doc = frappe.get_doc("Account", account)
		account_doc.disabled = 1
		with self.assertRaisesRegex(frappe.ValidationError, "Purchase Expense Account"):
			account_doc.save()
