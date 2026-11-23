# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from unittest.mock import patch

import frappe

from erpnext.accounts.default_accounts import (
	BANK,
	COST_OF_GOODS_SOLD,
	DEFAULT_ACCOUNT_PURPOSES,
	EXCHANGE_GAIN,
	EXCHANGE_GAIN_LOSS,
	EXCHANGE_LOSS,
	PAYABLE,
	PURCHASE_EXPENSE,
	RECEIVABLE,
	WRITE_OFF,
	DefaultAccountPurpose,
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
	def test_registry(self):
		company_meta = frappe.get_meta("Company")
		self.assertFalse(company_meta.get("fields", {"fieldtype": "Link", "options": "Account"}))

		fieldnames = [purpose.fieldname for purpose in DEFAULT_ACCOUNT_PURPOSES]
		self.assertEqual(len(fieldnames), len(set(fieldnames)))
		for purpose in DEFAULT_ACCOUNT_PURPOSES:
			self.assertEqual(purpose.key, purpose.key.upper())
			if purpose.fallback:
				self.assertIn(purpose.fallback, get_purposes())

	def test_get_and_set_default_account(self):
		receivable = frappe.db.get_value(
			"Account", {"company": COMPANY, "account_type": "Receivable", "is_group": 0}
		)
		set_default_account(COMPANY, RECEIVABLE, receivable)

		row_filters = {"parenttype": "Company", "parent": COMPANY, "purpose": RECEIVABLE}
		self.assertEqual(frappe.db.get_value("Company Default Account", row_filters, "account"), receivable)
		self.assertEqual(get_default_account(COMPANY, RECEIVABLE), receivable)

		set_default_account(COMPANY, RECEIVABLE, None)
		self.assertFalse(frappe.db.exists("Company Default Account", row_filters))
		self.assertIsNone(get_default_account(COMPANY, RECEIVABLE))

		set_default_account(COMPANY, RECEIVABLE, receivable)
		self.assertEqual(frappe.db.count("Company Default Account", row_filters), 1)
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
		account = company.get_default_account(COST_OF_GOODS_SOLD)
		company.set_default_account(PURCHASE_EXPENSE, None)
		company.set_default_account(PURCHASE_EXPENSE, account)

		self.assertEqual(company.get_default_account_row(PURCHASE_EXPENSE).account, account)
		self.assertEqual(company.get_default_account(PURCHASE_EXPENSE), account)

		company.set_default_account(PURCHASE_EXPENSE, None)
		self.assertIsNone(company.get_default_account_row(PURCHASE_EXPENSE))

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
				"description": None,
			},
		)

	def test_purposes_from_hook(self):
		get_hooks = frappe.get_hooks

		def get_hooks_with_test_purpose(hook=None, *args, **kwargs):
			hooks = get_hooks(hook, *args, **kwargs)
			if hook == "company_default_accounts":
				return [*hooks, "erpnext.accounts.test.test_default_accounts.get_test_purposes"]
			return hooks

		write_off_account = get_default_account(COMPANY, WRITE_OFF)
		with patch("frappe.get_hooks", side_effect=get_hooks_with_test_purpose):
			self.assertEqual(get_purpose("TEST_PURPOSE").label, "Test Purpose Account")
			self.assertEqual(list(get_purposes())[-1], "TEST_PURPOSE")

			company = frappe.get_doc("Company", COMPANY)
			company.set_default_account("TEST_PURPOSE", write_off_account)
			company.save()
			self.assertEqual(get_default_account(COMPANY, "TEST_PURPOSE"), write_off_account)
			self.assertEqual(company.default_accounts[-1].purpose, "TEST_PURPOSE")

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

	def test_validation(self):
		company = frappe.get_doc("Company", COMPANY)
		company.append("default_accounts", {"purpose": "NO_SUCH_PURPOSE", "account": "Cash - _TC"})
		with self.assertRaisesRegex(frappe.ValidationError, "not a valid default account purpose"):
			company.save()

		company = frappe.get_doc("Company", COMPANY)
		company.append(
			"default_accounts",
			{"purpose": WRITE_OFF, "account": get_default_account(COMPANY, WRITE_OFF)},
		)
		with self.assertRaisesRegex(frappe.ValidationError, "more than once"):
			company.save()

		company = frappe.get_doc("Company", COMPANY)
		company.set_default_account(RECEIVABLE, get_default_account(COMPANY, PAYABLE))
		with self.assertRaisesRegex(frappe.ValidationError, "invalid root_type"):
			company.save()

	def test_rows_follow_registry_order(self):
		company = frappe.get_doc("Company", COMPANY)
		company.set_default_account(BANK, None)
		company.set_default_account(
			BANK, frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Bank", "is_group": 0})
		)
		company.save()

		order = {purpose.key: index for index, purpose in enumerate(DEFAULT_ACCOUNT_PURPOSES)}
		purposes = [row.purpose for row in company.default_accounts]
		self.assertEqual(purposes, sorted(purposes, key=order.get))
		self.assertEqual([row.idx for row in company.default_accounts], list(range(1, len(purposes) + 1)))

	def test_get_company_default_maps_removed_fields(self):
		from erpnext.accounts.utils import get_company_default

		with self.assertWarns(Warning):
			account = get_company_default(COMPANY, "write_off_account")  # nosemgrep

		self.assertEqual(account, get_default_account(COMPANY, WRITE_OFF))
		self.assertEqual(
			get_company_default(COMPANY, "cost_center"),
			frappe.get_cached_value("Company", COMPANY, "cost_center"),
		)


def get_test_purposes():
	"""Purposes of a fictional app, registered by `test_purposes_from_hook`."""
	return {
		"TEST_PURPOSE": DefaultAccountPurpose(
			key="TEST_PURPOSE",
			label="Test Purpose Account",
			filters={"root_type": "Expense"},
		)
	}
