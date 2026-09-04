# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import (
	auto_reconcile_vouchers,
	get_bank_transactions,
	get_linked_payments,
)
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestBankReconciliationTool(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.clear_old_entries()
		bank_dt = qb.DocType("Bank")
		qb.from_(bank_dt).delete().where(bank_dt.name == "HDFC").run()
		self.create_bank_account()

	def tearDown(self):
		frappe.db.rollback()

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
					"bank": bank,
					"is_company_account": True,
					"account": self.bank,  # account from Chart of Accounts
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
<<<<<<< HEAD
=======

	def make_bank_transaction(self, date, deposit=100, withdrawal=0):
		return (
			frappe.get_doc(
				{
					"doctype": "Bank Transaction",
					"date": date,
					"deposit": deposit,
					"withdrawal": withdrawal,
					"bank_account": self.bank_account,
					"currency": "INR",
				}
			)
			.save()
			.submit()
		)

	def get_matching_payment_entries(self, bank_transaction, exact_match=False):
		document_types = ["payment_entry", "exact_match"] if exact_match else ["payment_entry"]
		vouchers = get_linked_payments(
			bank_transaction,
			document_types,
			from_date=add_days(today(), -1),
			to_date=today(),
		)
		return [v for v in vouchers if v.get("doctype") == "Payment Entry"]

	def test_get_bank_transactions_excludes_dates_after_to_date(self):
		self.make_bank_transaction(date=today())
		names = [t.name for t in get_bank_transactions(self.bank_account, to_date=add_days(today(), -1))]
		self.assertEqual(names, [])

	def test_deposit_matches_amount_received_in_bank_account(self):
		# money leaves another bank account and lands here minus a charge, so the two sides differ
		payment = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"payment_type": "Internal Transfer",
				"company": self.company,
				"posting_date": today(),
				"paid_from": "_Test Bank - _TC",
				"paid_to": self.bank,
				"paid_amount": 3537.64,
				"received_amount": 3460.52,
				"reference_no": "TRF-001",
				"reference_date": today(),
			}
		)
		payment.set_missing_values()
		payment.set_exchange_rate()
		payment.set_amounts()
		payment.deductions[-1].account = "_Test Exchange Gain/Loss - _TC"
		payment.deductions[-1].cost_center = "_Test Cost Center - _TC"
		payment = payment.save().submit()

		transaction = self.make_bank_transaction(date=today(), deposit=3460.52)

		# the received side is what reached this bank account, so that is what is shown
		matches = self.get_matching_payment_entries(transaction.name)
		self.assertEqual([m["name"] for m in matches], [payment.name])
		self.assertEqual(matches[0]["paid_amount"], 3460.52)

		# and what the exact match compares against
		exact_matches = self.get_matching_payment_entries(transaction.name, exact_match=True)
		self.assertEqual([m["name"] for m in exact_matches], [payment.name])

	def test_withdrawal_matches_amount_paid_from_bank_account(self):
		payment = create_payment_entry(
			company=self.company,
			payment_type="Pay",
			party_type="Supplier",
			party="_Test Supplier",
			paid_from=self.bank,
			paid_to="Creditors - _TC",
			paid_amount=1250,
		)
		payment = payment.save().submit()

		transaction = self.make_bank_transaction(date=today(), deposit=0, withdrawal=1250)

		exact_matches = self.get_matching_payment_entries(transaction.name, exact_match=True)
		self.assertEqual([m["name"] for m in exact_matches], [payment.name])
		self.assertEqual(exact_matches[0]["paid_amount"], 1250)

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
>>>>>>> 154c6fb (fix(bank reconciliation): match Payment Entries on the bank-side amount (#57740))
