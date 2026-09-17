# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from unittest.mock import patch

import frappe
from frappe import qb
from frappe.utils import add_days, today

from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import (
	auto_reconcile_vouchers,
	create_bulk_payment_entry_and_reconcile,
	create_payment_entry_and_reconcile,
	get_auto_reconcile_message,
	get_bank_transactions,
	get_linked_payments,
)
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite

RATE_METHOD = "erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_exchange_rate"


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

	def test_get_linked_payments_without_document_types(self):
		bank_transaction = self.make_bank_transaction(date=today())
		self.assertEqual(get_linked_payments(bank_transaction.name), [])

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

	def test_multi_currency_pay_converts_and_balances(self):
		# withdrawal from an INR bank paying a USD supplier; rate 3.0 makes 100/3 non-exact
		self.enable_multi_currency_setup()
		pe = self.reconcile_new_payment(
			self.make_multi_currency_txn(withdrawal=100),
			payment_type="Pay",
			party_type="Supplier",
			party=self.supplier,
			party_account=self.creditors_usd,
			paid_from=self.bank,
			paid_to=self.creditors_usd,
			rate=3.0,
		)
		self.assertEqual(pe.docstatus, 1)  # submits despite the rounding residual
		self.assertEqual((pe.source_exchange_rate, pe.target_exchange_rate), (1.0, 3.0))
		self.assertEqual((pe.paid_amount, pe.received_amount), (100, 33.33))  # bank side kept, 100/3
		self.assertEqual(pe.difference_amount, 0)
		# Payment Entry auto-books the rounding residual to Exchange Gain/Loss
		self.assertTrue(pe.deductions[0].is_exchange_gain_loss)
		self.assertEqual(pe.deductions[0].amount, 0.01)  # 100 - 33.33 * 3

	def test_multi_currency_receive_converts_and_balances(self):
		# deposit into an INR bank from a USD customer; the party side must convert
		self.enable_multi_currency_setup()
		pe = self.reconcile_new_payment(
			self.make_multi_currency_txn(deposit=100),
			payment_type="Receive",
			party_type="Customer",
			party=self.customer,
			party_account=self.debtors_usd,
			paid_from=self.debtors_usd,
			paid_to=self.bank,
			rate=3.0,
		)
		self.assertEqual(pe.docstatus, 1)
		self.assertEqual((pe.source_exchange_rate, pe.target_exchange_rate), (3.0, 1.0))
		self.assertEqual((pe.received_amount, pe.paid_amount), (100, 33.33))  # bank side kept, 100/3
		self.assertEqual(pe.difference_amount, 0)

	def test_multi_currency_bulk_pay_converts_and_balances(self):
		# the bulk path builds the Payment Entry itself, so it must convert too
		self.enable_multi_currency_setup()
		txn = self.make_multi_currency_txn(withdrawal=100)
		with patch(RATE_METHOD, return_value=3.0):
			result = create_bulk_payment_entry_and_reconcile(
				[txn.name], "Supplier", self.supplier, self.creditors_usd
			)

		pe = frappe.get_doc("Payment Entry", result[0]["payment_entry"].name)
		self.assertEqual(pe.docstatus, 1)
		self.assertEqual(pe.target_exchange_rate, 3.0)
		self.assertEqual((pe.paid_amount, pe.received_amount), (100, 33.33))
		self.assertEqual(pe.difference_amount, 0)

	def enable_multi_currency_setup(self):
		# USD party/accounts + a company gain/loss account to absorb rounding residuals
		self.company_abbr = "_TC"
		self.create_supplier(supplier_name="_Test Supplier USD", currency="USD")
		self.create_customer(customer_name="_Test Customer USD", currency="USD")
		self.create_usd_payable_account()
		self.create_usd_receivable_account()
		self.set_party_account("Supplier", self.supplier, self.creditors_usd)
		if not frappe.db.get_value("Company", self.company, "exchange_gain_loss_account"):
			frappe.db.set_value(
				"Company", self.company, "exchange_gain_loss_account", "Exchange Gain/Loss - _TC"
			)

	def set_party_account(self, party_type, party, account):
		doc = frappe.get_doc(party_type, party)
		if not any(row.company == self.company for row in doc.accounts):
			doc.append("accounts", {"company": self.company, "account": account})
			doc.save()

	def make_multi_currency_txn(self, withdrawal=0, deposit=0):
		return (
			frappe.get_doc(
				{
					"doctype": "Bank Transaction",
					"date": today(),
					"withdrawal": withdrawal,
					"deposit": deposit,
					"bank_account": self.bank_account,
					"currency": "INR",
					"reference_number": "TEST-FX-REF",
				}
			)
			.save()
			.submit()
		)

	def reconcile_new_payment(
		self, txn, *, payment_type, party_type, party, party_account, paid_from, paid_to, rate
	):
		# mimics the /banking frontend, which sends a hardcoded 1:1 rate
		payment_entry_doc = {
			"payment_type": payment_type,
			"company": self.company,
			"party_type": party_type,
			"party": party,
			"party_account": party_account,
			"paid_from": paid_from,
			"paid_to": paid_to,
			"paid_amount": txn.unallocated_amount,
			"received_amount": txn.unallocated_amount,
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"posting_date": today(),
			"reference_no": f"TEST-FX-{payment_type}",
			"reference_date": today(),
		}
		with patch(RATE_METHOD, return_value=rate):
			result = create_payment_entry_and_reconcile(txn.name, payment_entry_doc)
		return frappe.get_doc("Payment Entry", result["payment_entry"].name)
