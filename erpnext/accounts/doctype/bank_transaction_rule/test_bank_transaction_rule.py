# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe import qb
from frappe.exceptions import ValidationError

from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestBankTransactionRule(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.clear_old_entries()
		bank_dt = qb.DocType("Bank")
		qb.from_(bank_dt).delete().where(bank_dt.name == "HDFC").run()
		self.create_bank_account()

	def create_bank_account(self):
		bank = frappe.get_doc(
			{
				"doctype": "Bank",
				"bank_name": "HDFC",
			}
		).save()

		self.bank_account = (
			frappe.get_doc(
				{
					"doctype": "Bank Account",
					"account_name": "HDFC _current_",
					"bank": bank.name,
					"is_company_account": True,
					"account": self.bank,
					"company": self.company,
				}
			)
			.insert()
			.name
		)

	def _unique_rule_name(self, prefix: str) -> str:
		return f"{prefix}-{frappe.generate_hash(length=8)}"

	def _make_transaction(self, company=None, withdrawal=0, deposit=0, description=None):
		doc = frappe.new_doc("Bank Transaction")
		doc.company = company or self.company
		doc.withdrawal = withdrawal
		doc.deposit = deposit
		doc.description = description
		return doc

	def _make_rule_doc(self, rule_name, description_rules, **fields):
		data = {
			"doctype": "Bank Transaction Rule",
			"rule_name": rule_name,
			"company": self.company,
			"classify_as": "Bank Entry",
			"transaction_type": "Any",
			"account": self.bank,
			"description_rules": description_rules,
			**fields,
		}
		return frappe.get_doc(data)

	def _rule(self, prefix: str, description_rules, **fields):
		return self._make_rule_doc(self._unique_rule_name(prefix), description_rules, **fields)

	# --- evaluate_rule ---

	def test_evaluate_rule_company_mismatch(self):
		doc = self._rule("co", [{"check": "Contains", "value": "foo"}])
		tx = self._make_transaction(company="Nonexistent Company XYZ", deposit=1, description="foo")
		self.assertFalse(doc.evaluate_rule(tx))

	def test_evaluate_rule_withdrawal_type(self):
		doc = self._rule("wd", [{"check": "Contains", "value": "pay"}], transaction_type="Withdrawal")
		self.assertFalse(
			doc.evaluate_rule(self._make_transaction(withdrawal=0, deposit=100, description="payment"))
		)
		self.assertTrue(
			doc.evaluate_rule(self._make_transaction(withdrawal=50, deposit=0, description="payment"))
		)

	def test_evaluate_rule_deposit_type(self):
		doc = self._rule("dep", [{"check": "Contains", "value": "inc"}], transaction_type="Deposit")
		self.assertFalse(
			doc.evaluate_rule(self._make_transaction(withdrawal=50, deposit=0, description="income"))
		)
		self.assertTrue(
			doc.evaluate_rule(self._make_transaction(withdrawal=0, deposit=50, description="income"))
		)

	def test_evaluate_rule_min_max_amount(self):
		doc = self._rule("amt", [{"check": "Contains", "value": "x"}], min_amount=10, max_amount=100)
		self.assertFalse(doc.evaluate_rule(self._make_transaction(deposit=5, description="x")))
		self.assertTrue(doc.evaluate_rule(self._make_transaction(deposit=10, description="x")))
		self.assertTrue(doc.evaluate_rule(self._make_transaction(deposit=50, description="x")))
		self.assertTrue(doc.evaluate_rule(self._make_transaction(deposit=100, description="x")))
		self.assertFalse(doc.evaluate_rule(self._make_transaction(deposit=101, description="x")))
		doc_w = self._rule("amt_wd", [{"check": "Contains", "value": "x"}], min_amount=10, max_amount=100)
		self.assertTrue(doc_w.evaluate_rule(self._make_transaction(withdrawal=10, description="x")))

	def test_evaluate_rule_description_contains(self):
		doc = self._rule("ct", [{"check": "Contains", "value": "amazon"}])
		self.assertTrue(
			doc.evaluate_rule(self._make_transaction(deposit=1, description="AMAZON marketplace"))
		)
		self.assertFalse(doc.evaluate_rule(self._make_transaction(deposit=1, description="other vendor")))

	def test_evaluate_rule_description_starts_with(self):
		doc = self._rule("sw", [{"check": "Starts With", "value": "wire"}])
		self.assertTrue(doc.evaluate_rule(self._make_transaction(deposit=1, description="WIRE transfer in")))
		self.assertFalse(doc.evaluate_rule(self._make_transaction(deposit=1, description="in wire")))

	def test_evaluate_rule_description_ends_with(self):
		doc = self._rule("ew", [{"check": "Ends With", "value": "fee"}])
		self.assertTrue(doc.evaluate_rule(self._make_transaction(deposit=1, description="Bank monthly FEE")))
		self.assertFalse(doc.evaluate_rule(self._make_transaction(deposit=1, description="fee reversed")))

	def test_evaluate_rule_description_regex(self):
		doc = self._rule("rx", [{"check": "Regex", "value": r"inv-\d+"}])
		self.assertTrue(doc.evaluate_rule(self._make_transaction(deposit=1, description="INV-12345 payment")))
		self.assertFalse(doc.evaluate_rule(self._make_transaction(deposit=1, description="invoice abc")))

	def test_evaluate_rule_composite_fails_on_description(self):
		doc = self._rule(
			"cmp",
			[{"check": "Contains", "value": "target"}],
			transaction_type="Deposit",
			min_amount=10,
			max_amount=100,
		)
		self.assertFalse(doc.evaluate_rule(self._make_transaction(deposit=50, description="other merchant")))

	def test_evaluate_rule_empty_description_rules_returns_false(self):
		doc = frappe.get_doc(
			{
				"doctype": "Bank Transaction Rule",
				"rule_name": "tmp-empty",
				"company": self.company,
				"classify_as": "Bank Entry",
				"transaction_type": "Any",
				"account": self.bank,
				"description_rules": [],
			}
		)
		self.assertFalse(doc.evaluate_rule(self._make_transaction(deposit=10, description="anything")))

	# --- validate ---

	def test_validate_min_amount_greater_than_max(self):
		doc = self._rule("minmax", [{"check": "Contains", "value": "x"}], min_amount=200, max_amount=100)
		with self.assertRaises(ValidationError):
			doc.insert()

	def test_validate_payment_entry_requires_party_type(self):
		doc = self._rule(
			"pe_pt",
			[{"check": "Contains", "value": "x"}],
			classify_as="Payment Entry",
			party=self.customer,
			account=self.debit_to,
		)
		with self.assertRaises(ValidationError):
			doc.insert()

	def test_validate_payment_entry_requires_party(self):
		doc = self._rule(
			"pe_p",
			[{"check": "Contains", "value": "x"}],
			classify_as="Payment Entry",
			party_type="Customer",
			account=self.debit_to,
		)
		with self.assertRaises(ValidationError):
			doc.insert()

	def test_validate_payment_entry_requires_account(self):
		doc = self._rule(
			"pe_a",
			[{"check": "Contains", "value": "x"}],
			classify_as="Payment Entry",
			party_type="Customer",
			party=self.customer,
		)
		doc.account = None
		with self.assertRaises(ValidationError):
			doc.insert()

	def test_validate_bank_entry_single_requires_account(self):
		doc = self._rule(
			"be_acc",
			[{"check": "Contains", "value": "x"}],
			bank_entry_type="Single Account",
		)
		doc.account = None
		with self.assertRaises(ValidationError):
			doc.insert()

	def test_validate_bank_entry_multiple_requires_accounts(self):
		doc = self._rule(
			"be_ma",
			[{"check": "Contains", "value": "x"}],
			classify_as="Bank Entry",
			bank_entry_type="Multiple Accounts",
			accounts=[],
		)
		with self.assertRaises(ValidationError):
			doc.insert()

	def test_validate_bank_entry_multiple_last_row_must_not_have_debit_or_credit(self):
		doc = self._rule(
			"be_last",
			[{"check": "Contains", "value": "x"}],
			classify_as="Bank Entry",
			bank_entry_type="Multiple Accounts",
			accounts=[
				{"account": self.bank, "debit": "", "credit": ""},
				{"account": self.cash, "debit": "10", "credit": ""},
			],
		)
		with self.assertRaises(ValidationError):
			doc.insert()

	def test_validate_invalid_regex(self):
		doc = self._rule("bad_rx", [{"check": "Regex", "value": "["}])
		with self.assertRaises(ValidationError):
			doc.insert()
