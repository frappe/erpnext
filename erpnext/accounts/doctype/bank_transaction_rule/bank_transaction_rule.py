# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document

from erpnext.accounts.doctype.bank_transaction.bank_transaction import BankTransaction


class BankTransactionRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.bank_transaction_rule_accounts.bank_transaction_rule_accounts import (
			BankTransactionRuleAccounts,
		)
		from erpnext.accounts.doctype.bank_transaction_rule_description_conditions.bank_transaction_rule_description_conditions import (
			BankTransactionRuleDescriptionConditions,
		)

		account: DF.Link | None
		accounts: DF.Table[BankTransactionRuleAccounts]
		bank_entry_type: DF.Literal["Single Account", "Multiple Accounts"]
		classify_as: DF.Literal["Bank Entry", "Payment Entry", "Transfer"]
		company: DF.Link
		description_rules: DF.Table[BankTransactionRuleDescriptionConditions]
		max_amount: DF.Currency
		min_amount: DF.Currency
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		priority: DF.Int
		rule_description: DF.SmallText | None
		rule_name: DF.Data
		transaction_type: DF.Literal["Any", "Withdrawal", "Deposit"]
	# end: auto-generated types

	def before_insert(self):
		"""Assign the next priority number for the new rule"""
		if not self.priority:
			# Get the highest priority for rules in the same company
			highest_priority = frappe.db.get_value(
				"Bank Transaction Rule",
				filters={"company": self.company},
				fieldname="priority",
				order_by="priority DESC",
			)

			# Set priority to 1 if no rules exist, otherwise increment by 1
			self.priority = (highest_priority or 0) + 1

	def validate(self):
		if self.min_amount and self.max_amount:
			if self.min_amount > self.max_amount:
				frappe.throw(_("Min amount cannot be greater than max amount."))

		if self.classify_as == "Payment Entry":
			if not self.party_type:
				frappe.throw(_("Party type is required to create a payment entry."))

			if not self.party:
				frappe.throw(_("Party is required create a payment entry."))

			if not self.account:
				frappe.throw(_("Party account is required to create a payment entry."))

		if self.classify_as == "Bank Entry":
			if not self.bank_entry_type or self.bank_entry_type == "Single Account":
				if not self.account:
					frappe.throw(_("Please add an account for the Bank Entry rule."))
			elif self.bank_entry_type == "Multiple Accounts":
				if not self.accounts:
					frappe.throw(_("Please configure accounts for the Bank Entry rule."))

				# Last row should not have any debit or credit set, since it will be computed via formula
				for index, account in enumerate(self.accounts):
					if index == len(self.accounts) - 1:
						if account.debit or account.credit:
							frappe.throw(
								_("The last account row must not have any debit or credit amounts set.")
							)

		# Validate regex
		for rule in self.description_rules:
			if rule.check == "Regex":
				try:
					re.compile(rule.value)
				except re.error:
					frappe.throw(_("Invalid regex pattern."))

		if self.bank_entry_type == "Single Account":
			account_company = frappe.get_cached_value("Account", self.account, "company")
			if account_company != self.company:
				frappe.throw(_("Account company does not match with the rule company."))

		if self.bank_entry_type == "Multiple Accounts":
			for account in self.accounts:
				account_company = frappe.get_cached_value("Account", account.account, "company")
				if account_company != self.company:
					frappe.throw(_("Account company does not match with the rule company."))

	def on_trash(self):
		"""
		Delete the matched rule from the bank transaction
		"""
		try:
			frappe.db.set_value(
				"Bank Transaction", {"matched_transaction_rule": self.name}, "matched_transaction_rule", None
			)
		except Exception:
			pass

	def after_delete(self):
		"""
		Rearrange the priorities of the rules
		"""
		rules = frappe.get_all(
			"Bank Transaction Rule",
			filters={"company": self.company, "name": ["!=", self.name]},
			order_by="priority asc",
		)
		for i, rule in enumerate(rules):
			frappe.db.set_value("Bank Transaction Rule", rule.name, "priority", i + 1)

	def evaluate_rule(self, transaction: BankTransaction) -> bool:
		"""
		Helper function to evaluate the rule for a given transaction
		"""
		if self.company != transaction.company:
			return False

		# Transaction type rule
		if self.transaction_type == "Withdrawal":
			if transaction.withdrawal == 0.0:
				return False

		if self.transaction_type == "Deposit":
			if transaction.deposit == 0.0:
				return False

		# Checking transaction amount limits
		transaction_amount = transaction.withdrawal or transaction.deposit

		if self.min_amount and transaction_amount < self.min_amount:
			return False

		if self.max_amount and transaction_amount > self.max_amount:
			return False

		# Checking description rules
		for rule_desc_rule in self.description_rules:
			desc = (transaction.description or "").lower()
			value = (rule_desc_rule.value or "").lower()

			if rule_desc_rule.check == "Contains":
				if value in desc:
					return True

			if rule_desc_rule.check == "Starts With":
				if desc.startswith(value):
					return True

			if rule_desc_rule.check == "Ends With":
				if desc.endswith(value):
					return True

			if rule_desc_rule.check == "Regex":
				if re.search(value, desc):
					return True

		return False


def scheduler_run_rule_evaluation():
	automatically_run_rules_on_unreconciled_transactions = frappe.db.get_single_value(
		"Accounts Settings", "automatically_run_rules_on_unreconciled_transactions"
	)

	if automatically_run_rules_on_unreconciled_transactions:
		_run_rule_evaluation(force_evaluate=False)


@frappe.whitelist(methods=["POST"])
def run_rule_evaluation(force_evaluate: bool = False):
	frappe.has_permission("Bank Transaction", ptype="read", throw=True)
	frappe.enqueue(method=_run_rule_evaluation, force_evaluate=force_evaluate)


def _run_rule_evaluation(force_evaluate=False):
	"""
	Run the rule evaluation for all bank transactions

	If force evaluate is set to True, then transactions that were previously evaluated will be evaluated again.
	"""
	rules = frappe.get_all("Bank Transaction Rule", fields=["name"], order_by="priority asc")

	if not rules:
		return

	filters = {"status": "Unreconciled", "docstatus": 1}

	if not force_evaluate:
		filters["is_rule_evaluated"] = 0

	unreconciled_transactions = frappe.get_all(
		"Bank Transaction",
		filters=filters,
		fields=[
			"name",
			"bank_account",
			"company",
			"date",
			"withdrawal",
			"deposit",
			"description",
			"reference_number",
		],
	)

	if not unreconciled_transactions:
		return

	rule_docs = []

	for rule in rules:
		rule_doc = frappe.get_doc("Bank Transaction Rule", rule.name)
		rule_docs.append(rule_doc)

	# Run evaluation for each transaction
	for transaction in unreconciled_transactions:
		matched_rule = None

		for rule in rule_docs:
			if rule.evaluate_rule(transaction):
				matched_rule = rule
				break

		frappe.db.set_value(
			"Bank Transaction",
			transaction.name,
			{"is_rule_evaluated": 1, "matched_transaction_rule": matched_rule.name if matched_rule else None},
		)
