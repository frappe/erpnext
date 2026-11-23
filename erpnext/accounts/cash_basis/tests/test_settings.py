# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe

import erpnext.accounts.cash_basis as cash_basis
from erpnext.accounts.cash_basis import (
	ACCRUAL,
	CASH,
	get_accounting_method,
	get_accounting_method_advisories,
	get_accounting_method_messages,
	get_core_notice,
	is_cash_basis,
	is_cash_method_available,
)
from erpnext.accounts.cash_basis.settings import get_or_create_unapplied_account, get_unapplied_settings
from erpnext.accounts.cash_basis.tests.fixtures import (
	US_ABBR,
	US_COMPANY,
	get_or_create_company,
	put_test_countries_in_scope,
	set_company_method,
)
from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
from erpnext.tests.utils import ERPNextTestSuite

OUTSIDE_COMPANY = "_Test Cash Basis Canada"
OUTSIDE_ABBR = "_TCBC"
MOVER_COMPANY = "_Test Cash Basis Mover"
MOVER_ABBR = "_TCBM"
GROUP_COMPANY = "_Test Cash Basis Group"
CHILD_COMPANY = "_Test Cash Basis Child"


class TestAccountingMethodSettings(ERPNextTestSuite):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		put_test_countries_in_scope(cls)
		get_or_create_company(US_COMPANY, US_ABBR)
		get_or_create_company(OUTSIDE_COMPANY, OUTSIDE_ABBR, country="Canada", currency="CAD")
		get_or_create_company(MOVER_COMPANY, MOVER_ABBR)
		get_or_create_company(GROUP_COMPANY, "_TCBG", is_group=1)
		get_or_create_company(CHILD_COMPANY, "_TCBK", parent=GROUP_COMPANY)

	def test_default_method_is_accrual(self):
		self.assertEqual(frappe.db.get_value("Company", US_COMPANY, "accounting_method"), ACCRUAL)
		self.assertEqual(get_accounting_method({"company": US_COMPANY}), ACCRUAL)
		self.assertEqual(get_accounting_method({}), ACCRUAL)
		self.assertEqual(get_accounting_method(None), ACCRUAL)
		self.assertFalse(is_cash_basis({"company": US_COMPANY}))

	def test_filter_overrides_company_default(self):
		set_company_method(US_COMPANY, CASH)
		self.assertEqual(get_accounting_method({"company": US_COMPANY}), CASH)
		self.assertEqual(
			get_accounting_method({"company": US_COMPANY, "accounting_method": ACCRUAL}), ACCRUAL
		)

		set_company_method(US_COMPANY, ACCRUAL)
		self.assertEqual(get_accounting_method({"company": US_COMPANY, "accounting_method": CASH}), CASH)
		self.assertTrue(is_cash_basis({"company": US_COMPANY, "accounting_method": CASH}))

	def test_outside_company_always_gets_accrual(self):
		self.assertTrue(is_cash_method_available(US_COMPANY))
		self.assertFalse(is_cash_method_available(OUTSIDE_COMPANY))
		# A caller can send Cash through the API. The helper still returns Accrual.
		self.assertEqual(
			get_accounting_method({"company": OUTSIDE_COMPANY, "accounting_method": CASH}), ACCRUAL
		)
		self.assertEqual(get_accounting_method({"accounting_method": CASH}), ACCRUAL)

	def test_invalid_method_is_refused(self):
		self.assertRaises(
			frappe.ValidationError, get_accounting_method, {"company": US_COMPANY, "accounting_method": "Tax"}
		)

	def test_company_outside_scope_cannot_select_cash(self):
		company = frappe.get_doc("Company", OUTSIDE_COMPANY)
		company.accounting_method = CASH
		with self.assertRaises(frappe.ValidationError) as context:
			company.save()
		self.assertIn("United States", str(context.exception))
		self.assertIn("Accrual", str(context.exception))

	def test_cash_creates_unapplied_accounts(self):
		company = set_company_method(US_COMPANY, CASH)
		expected = {
			"unapplied_cash_receipts_account": ("Unapplied Cash Receipts - " + US_ABBR, "Income"),
			"unapplied_cash_payments_account": ("Unapplied Cash Payments - " + US_ABBR, "Expense"),
		}
		for fieldname, (account, root_type) in expected.items():
			self.assertEqual(company.get(fieldname), account)
			details = frappe.db.get_value(
				"Account", account, ["root_type", "is_group", "company"], as_dict=True
			)
			self.assertEqual(details.root_type, root_type)
			self.assertEqual(details.is_group, 0)
			self.assertEqual(details.company, US_COMPANY)

		# A second save reuses the accounts.
		set_company_method(US_COMPANY, ACCRUAL)
		company = set_company_method(US_COMPANY, CASH)
		self.assertEqual(
			company.unapplied_cash_receipts_account, expected["unapplied_cash_receipts_account"][0]
		)
		self.assertEqual(
			frappe.db.count("Account", {"company": US_COMPANY, "account_name": "Unapplied Cash Receipts"}), 1
		)

	def test_unapplied_settings_for_the_calculation(self):
		set_company_method(US_COMPANY, CASH)
		self.assertEqual(
			get_unapplied_settings(US_COMPANY),
			{
				"unapplied_treatment": "Income and Expense",
				"unapplied_accounts": {
					"Customer": "Unapplied Cash Receipts - " + US_ABBR,
					"Supplier": "Unapplied Cash Payments - " + US_ABBR,
				},
			},
		)

	def test_balance_sheet_treatment_needs_no_accounts(self):
		company = set_company_method(US_COMPANY, CASH, treatment="Balance Sheet")
		self.assertFalse(company.unapplied_cash_receipts_account)
		self.assertFalse(company.unapplied_cash_payments_account)
		self.assertFalse(
			frappe.db.exists("Account", {"company": US_COMPANY, "account_name": "Unapplied Cash Receipts"})
		)

	def test_unapplied_account_must_have_correct_root_type(self):
		company = set_company_method(US_COMPANY, CASH)
		company.unapplied_cash_receipts_account = "Cost of Goods Sold - " + US_ABBR
		self.assertRaises(frappe.ValidationError, company.save)

	def test_unapplied_account_must_not_be_a_default_account(self):
		company = set_company_method(US_COMPANY, CASH)
		company.unapplied_cash_receipts_account = company.default_income_account
		with self.assertRaises(frappe.ValidationError) as context:
			company.save()
		self.assertIn("Default Income Account", str(context.exception))

	def test_default_account_cannot_be_an_unapplied_account(self):
		company = set_company_method(US_COMPANY, CASH)
		company.default_expense_account = company.unapplied_cash_payments_account
		with self.assertRaises(frappe.ValidationError) as context:
			company.save()
		self.assertIn("Default Cost of Goods Sold Account", str(context.exception))

	def test_unapplied_account_must_have_no_postings(self):
		used_account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Used Expense",
				"parent_account": "Indirect Expenses - " + US_ABBR,
				"company": US_COMPANY,
			}
		).insert()
		make_journal_entry(
			used_account.name,
			"Cash - " + US_ABBR,
			100,
			cost_center="Main - " + US_ABBR,
			company=US_COMPANY,
			posting_date="2026-03-01",
			submit=True,
		)
		company = set_company_method(US_COMPANY, CASH)
		company.unapplied_cash_payments_account = used_account.name
		with self.assertRaises(frappe.ValidationError) as context:
			company.save()
		self.assertIn("has postings", str(context.exception))

	def test_old_account_with_standard_name_and_postings_is_refused(self):
		old_account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Unapplied Cash Receipts",
				"parent_account": "Income - " + US_ABBR,
				"company": US_COMPANY,
			}
		).insert()
		make_journal_entry(
			old_account.name,
			"Cash - " + US_ABBR,
			100,
			cost_center="Main - " + US_ABBR,
			company=US_COMPANY,
			posting_date="2026-03-01",
			submit=True,
		)
		with self.assertRaises(frappe.ValidationError) as context:
			set_company_method(US_COMPANY, CASH)
		self.assertIn("has postings", str(context.exception))

	def test_disabled_account_with_standard_name_is_refused(self):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Unapplied Cash Payments",
				"parent_account": "Expenses - " + US_ABBR,
				"company": US_COMPANY,
				"disabled": 1,
			}
		).insert()
		with self.assertRaises(frappe.ValidationError) as context:
			set_company_method(US_COMPANY, CASH)
		self.assertIn("not an enabled ledger account", str(context.exception))

	def test_group_account_with_standard_name_is_refused(self):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Unapplied Cash Receipts",
				"parent_account": "Income - " + US_ABBR,
				"company": US_COMPANY,
				"is_group": 1,
			}
		).insert()
		with self.assertRaises(frappe.ValidationError) as context:
			set_company_method(US_COMPANY, CASH)
		self.assertIn("not an enabled ledger account", str(context.exception))

	def test_child_company_needs_accounts_in_root_company(self):
		with self.assertRaises(frappe.ValidationError) as context:
			set_company_method(CHILD_COMPANY, CASH)
		self.assertIn("Create the account", str(context.exception))
		self.assertIn(GROUP_COMPANY, str(context.exception))

		# The root company makes the accounts, and Account copies them to the child.
		set_company_method(GROUP_COMPANY, CASH)
		child = set_company_method(CHILD_COMPANY, CASH)
		self.assertEqual(child.unapplied_cash_receipts_account, "Unapplied Cash Receipts - _TCBK")
		self.assertEqual(child.unapplied_cash_payments_account, "Unapplied Cash Payments - _TCBK")

	def test_new_company_with_cash_gets_accounts(self):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": "_Test Cash Basis New",
				"abbr": "_TCBN",
				"country": "United States",
				"default_currency": "USD",
				"create_chart_of_accounts_based_on": "Standard Template",
				"chart_of_accounts": "Standard",
				"accounting_method": CASH,
			}
		).insert()
		values = frappe.db.get_value(
			"Company",
			company.name,
			["unapplied_cash_receipts_account", "unapplied_cash_payments_account"],
			as_dict=True,
		)
		self.assertEqual(values.unapplied_cash_receipts_account, "Unapplied Cash Receipts - _TCBN")
		self.assertEqual(values.unapplied_cash_payments_account, "Unapplied Cash Payments - _TCBN")

	def test_account_setup_restores_root_company_flag(self):
		frappe.local.flags.ignore_root_company_validation = None
		company = frappe.get_doc("Company", CHILD_COMPANY)
		account = get_or_create_unapplied_account(
			company, "Unapplied Cash Receipts", "Income", in_company_insert=True
		)
		self.assertEqual(account, "Unapplied Cash Receipts - _TCBK")
		self.assertIsNone(frappe.local.flags.ignore_root_company_validation)

	def test_country_change_sets_method_to_accrual(self):
		company = set_company_method(MOVER_COMPANY, CASH)
		company.country = "Canada"
		company.save()
		self.assertEqual(company.accounting_method, ACCRUAL)
		self.assertEqual(frappe.db.get_value("Company", company.name, "accounting_method"), ACCRUAL)

	def test_no_voucher_can_post_to_unapplied_account(self):
		company = set_company_method(US_COMPANY, CASH)
		for account in (company.unapplied_cash_receipts_account, company.unapplied_cash_payments_account):
			with self.assertRaises(frappe.ValidationError) as context:
				make_journal_entry(
					account,
					"Cash - " + US_ABBR,
					100,
					cost_center="Main - " + US_ABBR,
					company=US_COMPANY,
					posting_date="2026-03-01",
					submit=True,
				)
			self.assertIn("unapplied cash account", str(context.exception))

		# The guard stays after a change back to Accrual, because the account keeps its role.
		set_company_method(US_COMPANY, ACCRUAL)
		self.assertRaises(
			frappe.ValidationError,
			make_journal_entry,
			company.unapplied_cash_receipts_account,
			"Cash - " + US_ABBR,
			100,
			cost_center="Main - " + US_ABBR,
			company=US_COMPANY,
			posting_date="2026-03-01",
			submit=True,
		)

	def test_other_accounts_still_post(self):
		set_company_method(US_COMPANY, CASH)
		journal_entry = make_journal_entry(
			"Sales - " + US_ABBR,
			"Cash - " + US_ABBR,
			100,
			cost_center="Main - " + US_ABBR,
			company=US_COMPANY,
			posting_date="2026-03-01",
			submit=True,
		)
		self.assertEqual(journal_entry.docstatus, 1)

	def test_core_advisories_and_notice(self):
		self.assertEqual(get_accounting_method_advisories(US_COMPANY), [])
		messages = get_accounting_method_messages(US_COMPANY)
		self.assertEqual(messages["notice"], get_core_notice())
		self.assertEqual(messages["advisories"], [])
		self.assertIn("accrual basis", messages["notice"])
		# A new company has no name yet. It gets only the notice.
		self.assertEqual(get_accounting_method_messages()["advisories"], [])

	def test_messages_need_read_permission(self):
		user = "test-cash-basis-guest@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc({"doctype": "User", "email": user, "first_name": "Cash Basis Guest"}).insert()
		with self.set_user(user):
			self.assertRaises(frappe.PermissionError, get_accounting_method_messages, US_COMPANY)

	def test_empty_rollout_turns_the_feature_off(self):
		# No country in scope turns the feature off everywhere.
		from erpnext.startup.boot import boot_session

		with patch.object(cash_basis, "CASH_METHOD_COUNTRIES", ()):
			self.assertFalse(is_cash_method_available(US_COMPANY))
			self.assertEqual(
				get_accounting_method({"company": US_COMPANY, "accounting_method": CASH}), ACCRUAL
			)
			bootinfo = frappe._dict(sysdefaults=frappe._dict(), docs=[], page_info={})
			boot_session(bootinfo)
			self.assertEqual(tuple(bootinfo.sysdefaults.cash_method_countries), ())
			with self.assertRaisesRegex(frappe.ValidationError, "Cash is not available"):
				set_company_method(US_COMPANY, CASH)

	def test_boot_has_rollout_countries(self):
		from erpnext.startup.boot import boot_session

		bootinfo = frappe._dict(sysdefaults=frappe._dict(), docs=[], page_info={})
		boot_session(bootinfo)
		self.assertEqual(tuple(bootinfo.sysdefaults.cash_method_countries), ("United States",))
		company = next(doc for doc in bootinfo.docs if doc.get("name") == US_COMPANY)
		self.assertEqual(company.accounting_method, ACCRUAL)
