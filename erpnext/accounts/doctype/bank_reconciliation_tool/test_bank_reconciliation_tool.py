# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe import qb
from frappe.utils import add_days, today

from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import (
	auto_reconcile_vouchers,
	get_auto_reconcile_message,
	get_bank_transactions,
)
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestBankReconciliationTool(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.company = "_Test Company"
		self.customer = "_Test Customer"
		self.bank = "HDFC - _TC"
		self.debit_to = "Debtors - _TC"
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
					"account": self.bank,  # account from Chart of Accounts
					"company": self.company,
				}
			)
			.insert()
			.name
		)

	def test_auto_reconcile(self):
		# make payment
		from_date = add_days(today(), -1)
		to_date = today()
		payment = create_payment_entry(
			company=self.company,
			posting_date=from_date,
			payment_type="Receive",
			party_type="Customer",
			party=self.customer,
			paid_from=self.debit_to,
			paid_to=self.bank,
			paid_amount=100,
		).save()
		payment.reference_no = "123"
		payment = payment.save().submit()

		# make bank transaction
		bank_transaction = (
			frappe.get_doc(
				{
					"doctype": "Bank Transaction",
					"date": to_date,
					"deposit": 100,
					"bank_account": self.bank_account,
					"reference_number": "123",
					"currency": "INR",
				}
			)
			.save()
			.submit()
		)

		# assert API output pre reconciliation
		transactions = get_bank_transactions(self.bank_account, from_date, to_date)
		self.assertEqual(len(transactions), 1)
		self.assertEqual(transactions[0].name, bank_transaction.name)

		# auto reconcile
		auto_reconcile_vouchers(
			bank_account=self.bank_account,
			from_date=from_date,
			to_date=to_date,
			filter_by_reference_date=False,
		)

		# assert API output post reconciliation
		transactions = get_bank_transactions(self.bank_account, from_date, to_date)
		self.assertEqual(len(transactions), 0)

	def make_bank_transaction(self, date, deposit=100):
		return (
			frappe.get_doc(
				{
					"doctype": "Bank Transaction",
					"date": date,
					"deposit": deposit,
					"bank_account": self.bank_account,
					"currency": "INR",
				}
			)
			.save()
			.submit()
		)

	def test_get_bank_transactions_excludes_dates_after_to_date(self):
		self.make_bank_transaction(date=today())
		names = [t.name for t in get_bank_transactions(self.bank_account, to_date=add_days(today(), -1))]
		self.assertEqual(names, [])

	def test_auto_reconcile_message_for_no_matches(self):
		message, indicator = get_auto_reconcile_message([], [])
		self.assertEqual(indicator, "blue")
		self.assertIn("No matches", message)

	def test_auto_reconcile_message_counts_and_pluralizes(self):
		# reconciled count is reported and the indicator turns green
		message, indicator = get_auto_reconcile_message([], ["t1", "t2"])
		self.assertEqual(indicator, "green")
		self.assertIn("2 Transaction(s) Reconciled", message)

		# partially-reconciled label is singular for one, plural for many
		singular, _ = get_auto_reconcile_message(["p1"], [])
		self.assertIn("1 Transaction Partially Reconciled", singular)
		plural, _ = get_auto_reconcile_message(["p1", "p2"], [])
		self.assertIn("2 Transactions Partially Reconciled", plural)
