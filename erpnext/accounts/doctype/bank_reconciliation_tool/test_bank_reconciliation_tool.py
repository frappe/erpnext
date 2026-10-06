# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
from unittest.mock import patch

import frappe
from frappe import qb
from frappe.utils import add_days, today

from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import (
	auto_reconcile_vouchers,
	create_bank_entry_and_reconcile,
	create_bulk_bank_entry_and_reconcile,
	create_bulk_internal_transfer,
	create_bulk_payment_entry_and_reconcile,
	create_internal_transfer,
	create_journal_entry_bts,
	create_payment_entry_and_reconcile,
	create_payment_entry_bts,
	get_auto_reconcile_message,
	get_bank_transactions,
	get_linked_payments,
	reconcile_vouchers,
	update_clearance_date,
)
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.permission_test_utils import (
	OTHER_COMPANY,
	as_user,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	make_bank_transaction,
	make_company_fenced_user,
	make_fenced_user,
	make_other_company_bank_account,
)
from erpnext.tests.utils import ERPNextTestSuite

RATE_METHOD = "erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_exchange_rate"
FENCED_USER = "_test_brt_fenced_user@example.com"
ACCOUNTS_USER = "_test_brt_accounts_user@example.com"
FENCED_COST_CENTER = "Main - _TC"
OTHER_COST_CENTER = "_Test Cost Center 2 - _TC"
OTHER_CUSTOMER = "_Test Customer 1"


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

	def test_rejects_reversed_date_ranges(self):
		from_date, to_date = today(), add_days(today(), -1)
		with self.assertRaisesRegex(frappe.ValidationError, "From Date cannot be greater than To Date"):
			get_bank_transactions(self.bank_account, from_date, to_date)

		with self.assertRaisesRegex(
			frappe.ValidationError, "From Reference Date cannot be greater than To Reference Date"
		):
			auto_reconcile_vouchers(
				self.bank_account,
				filter_by_reference_date=True,
				from_reference_date=from_date,
				to_reference_date=to_date,
			)

		transaction = self.make_bank_transaction(date=today())
		with self.assertRaisesRegex(
			frappe.ValidationError, "From Reference Date cannot be greater than To Reference Date"
		):
			get_linked_payments(
				transaction.name,
				["payment_entry"],
				filter_by_reference_date=True,
				from_reference_date=from_date,
				to_reference_date=to_date,
			)

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

	def make_payment(self, amount, cost_center, reference_no):
		payment = create_payment_entry(
			company=self.company,
			payment_type="Receive",
			party_type="Customer",
			party=self.customer,
			paid_from=self.debit_to,
			paid_to=self.bank,
			paid_amount=amount,
		)
		payment.cost_center = cost_center
		payment.reference_no = reference_no
		return payment.save().submit()

	def voucher_json(self, payment_doctype, payment_name, amount):
		return json.dumps(
			[{"payment_doctype": payment_doctype, "payment_name": payment_name, "amount": amount}]
		)

	def journal_entry_kwargs(self, **kwargs):
		values = {
			"reference_number": "UP-JE",
			"reference_date": today(),
			"posting_date": today(),
			"entry_type": "Bank Entry",
			"second_account": "_Test Cash - _TC",
			"allow_edit": 1,
		}
		values.update(kwargs)
		return values

	def payment_entry_kwargs(self, **kwargs):
		values = {
			"reference_number": "UP-PE",
			"reference_date": today(),
			"party_type": "Customer",
			"party": self.customer,
			"posting_date": today(),
			"allow_edit": 1,
		}
		values.update(kwargs)
		return values

	def bank_entry_rows(self, party, amount):
		return [
			{"account": self.bank, "bank_account": self.bank_account, "debit": amount},
			{"account": self.debit_to, "party_type": "Customer", "party": party, "credit": amount},
		]

	def payment_entry_doc(self, party, amount):
		return {
			"payment_type": "Receive",
			"company": self.company,
			"party_type": "Customer",
			"party": party,
			"paid_from": self.debit_to,
			"paid_to": self.bank,
			"paid_amount": amount,
			"received_amount": amount,
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"posting_date": today(),
			"reference_no": "UP-PED",
			"reference_date": today(),
		}

	def transfer_kwargs(self, paid_from, **kwargs):
		values = {
			"posting_date": today(),
			"reference_date": today(),
			"reference_no": "UP-IT",
			"paid_from": paid_from,
			"paid_to": self.bank,
		}
		values.update(kwargs)
		return values

	def transaction_links(self, transaction_name):
		company, bank_account = frappe.db.get_value(
			"Bank Transaction", transaction_name, ["company", "bank_account"]
		)
		return [company, bank_account]

	def party_links(self, party):
		customer_group, territory = frappe.db.get_value("Customer", party, ["customer_group", "territory"])
		return [customer_group, territory]

	def test_reconcile_vouchers_refuses_voucher_outside_cost_center_fence(self):
		inside = self.make_payment(61, FENCED_COST_CENTER, "UP-REC-IN")
		outside = self.make_payment(62, OTHER_COST_CENTER, "UP-REC-OUT")
		transaction = make_bank_transaction(self.bank_account, deposit=62)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Cost Center", FENCED_COST_CENTER)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def for_voucher(payment_name):
			return {
				"bank_transaction_name": transaction.name,
				"vouchers": self.voucher_json("Payment Entry", payment_name, 62),
			}

		def for_transaction(transaction_name):
			return {
				"bank_transaction_name": transaction_name,
				"vouchers": self.voucher_json("Payment Entry", inside.name, 61),
			}

		with as_user(fenced):
			assert_refused_without(self, [OTHER_COST_CENTER], reconcile_vouchers, **for_voucher(outside.name))
			assert_refused_for_names(self, reconcile_vouchers, for_voucher, [], caller_supplied=True)
			assert_refused_for_names(
				self, reconcile_vouchers, for_transaction, [], type_gated=True, caller_supplied=True
			)
			with self.assertRaises(frappe.PermissionError):
				reconcile_vouchers(transaction.name, self.voucher_json("User", "Administrator", 62))
			reconciled = reconcile_vouchers(
				make_bank_transaction(self.bank_account, deposit=61).name,
				self.voucher_json("Payment Entry", inside.name, 61),
			)
		self.assertEqual(reconciled.status, "Reconciled")
		self.assertEqual(reconciled.payment_entries[0].payment_entry, inside.name)

		with as_user(accounts_user):
			reconciled = reconcile_vouchers(
				transaction.name, self.voucher_json("Payment Entry", outside.name, 62)
			)
		self.assertEqual(reconciled.status, "Reconciled")

	def test_create_journal_entry_bts_refuses_transaction_outside_company_fence(self):
		outside = make_bank_transaction(make_other_company_bank_account(), deposit=70)
		inside = make_bank_transaction(self.bank_account, deposit=70)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Company", self.company)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def for_transaction(name):
			return self.journal_entry_kwargs(bank_transaction_name=name)

		with as_user(fenced):
			assert_refused_without(
				self,
				self.transaction_links(outside.name),
				create_journal_entry_bts,
				**for_transaction(outside.name),
			)
			assert_refused_for_names(
				self, create_journal_entry_bts, for_transaction, [], type_gated=True, caller_supplied=True
			)
			journal_entry = create_journal_entry_bts(inside.name, **self.journal_entry_kwargs())
		self.assertEqual(journal_entry.company, self.company)

		with as_user(accounts_user):
			journal_entry = create_journal_entry_bts(
				outside.name, **self.journal_entry_kwargs(second_account="Cash - _TC3")
			)
		self.assertEqual(journal_entry.company, OTHER_COMPANY)

	def test_create_journal_entry_bts_refuses_party_outside_customer_fence(self):
		transaction = make_bank_transaction(self.bank_account, deposit=75)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Customer", self.customer)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def for_party(party):
			return self.journal_entry_kwargs(
				bank_transaction_name=transaction.name,
				second_account=self.debit_to,
				party_type="Customer",
				party=party,
			)

		with as_user(fenced):
			assert_refused_without(
				self, self.party_links(OTHER_CUSTOMER), create_journal_entry_bts, **for_party(OTHER_CUSTOMER)
			)
			assert_refused_for_names(
				self, create_journal_entry_bts, for_party, [], type_gated=True, caller_supplied=True
			)
			assert_refused(
				self,
				create_journal_entry_bts,
				transaction.name,
				**self.journal_entry_kwargs(party_type="User", party="Administrator"),
			)
			journal_entry = create_journal_entry_bts(**for_party(self.customer))
		self.assertEqual(journal_entry.accounts[0].party, self.customer)

		with as_user(accounts_user):
			journal_entry = create_journal_entry_bts(**for_party(OTHER_CUSTOMER))
		self.assertEqual(journal_entry.accounts[0].party, OTHER_CUSTOMER)

	def test_create_payment_entry_bts_refuses_transaction_outside_company_fence(self):
		outside = make_bank_transaction(make_other_company_bank_account(), deposit=80)
		inside = make_bank_transaction(self.bank_account, deposit=80)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Company", self.company)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def for_transaction(name):
			return self.payment_entry_kwargs(bank_transaction_name=name)

		with as_user(fenced):
			assert_refused_without(
				self,
				self.transaction_links(outside.name),
				create_payment_entry_bts,
				**for_transaction(outside.name),
			)
			assert_refused_for_names(
				self, create_payment_entry_bts, for_transaction, [], type_gated=True, caller_supplied=True
			)
			payment_entry = create_payment_entry_bts(inside.name, **self.payment_entry_kwargs())
		self.assertEqual(payment_entry.company, self.company)

		with as_user(accounts_user):
			payment_entry = create_payment_entry_bts(outside.name, **self.payment_entry_kwargs())
		self.assertEqual(payment_entry.company, OTHER_COMPANY)

	def test_create_payment_entry_bts_refuses_party_outside_customer_fence(self):
		transaction = make_bank_transaction(self.bank_account, deposit=85)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Customer", self.customer)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def for_party(party):
			return self.payment_entry_kwargs(bank_transaction_name=transaction.name, party=party)

		with as_user(fenced):
			assert_refused_without(
				self, self.party_links(OTHER_CUSTOMER), create_payment_entry_bts, **for_party(OTHER_CUSTOMER)
			)
			assert_refused_for_names(
				self, create_payment_entry_bts, for_party, [], type_gated=True, caller_supplied=True
			)
			assert_refused(
				self,
				create_payment_entry_bts,
				transaction.name,
				**self.payment_entry_kwargs(party_type="User", party="Administrator"),
			)
			payment_entry = create_payment_entry_bts(**for_party(self.customer))
		self.assertEqual(payment_entry.party, self.customer)

		with as_user(accounts_user):
			payment_entry = create_payment_entry_bts(**for_party(OTHER_CUSTOMER))
		self.assertEqual(payment_entry.party, OTHER_CUSTOMER)

	def test_create_bank_entry_and_reconcile_refuses_party_outside_customer_fence(self):
		transaction = make_bank_transaction(self.bank_account, deposit=300)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Customer", self.customer)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def bank_entry_kwargs(name, party):
			return {
				"bank_transaction_name": name,
				"cheque_date": today(),
				"posting_date": today(),
				"cheque_no": "UP-BE",
				"entries": self.bank_entry_rows(party, 300),
			}

		def for_party(party):
			return bank_entry_kwargs(transaction.name, party)

		def for_transaction(name):
			return bank_entry_kwargs(name, self.customer)

		with as_user(fenced):
			assert_refused_without(
				self,
				self.party_links(OTHER_CUSTOMER),
				create_bank_entry_and_reconcile,
				**for_party(OTHER_CUSTOMER),
			)
			assert_refused_for_names(
				self, create_bank_entry_and_reconcile, for_party, [], caller_supplied=True
			)
			assert_refused_for_names(
				self,
				create_bank_entry_and_reconcile,
				for_transaction,
				[],
				type_gated=True,
				caller_supplied=True,
			)
			result = create_bank_entry_and_reconcile(**for_party(self.customer))
		self.assertEqual(result["transaction"].status, "Reconciled")
		self.assertEqual(result["journal_entry"].accounts[1].party, self.customer)

		with as_user(accounts_user):
			result = create_bank_entry_and_reconcile(
				**bank_entry_kwargs(
					make_bank_transaction(self.bank_account, deposit=300).name, OTHER_CUSTOMER
				)
			)
		self.assertEqual(result["journal_entry"].accounts[1].party, OTHER_CUSTOMER)

	def test_create_bulk_payment_entry_and_reconcile_refuses_party_outside_customer_fence(self):
		transaction = make_bank_transaction(self.bank_account, deposit=91)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Customer", self.customer)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def bulk_kwargs(name, party):
			return {
				"bank_transaction_names": [name],
				"party_type": "Customer",
				"party": party,
				"account": self.debit_to,
			}

		def for_party(party):
			return bulk_kwargs(transaction.name, party)

		def for_transaction(name):
			return bulk_kwargs(name, self.customer)

		with as_user(fenced):
			assert_refused_without(
				self,
				self.party_links(OTHER_CUSTOMER),
				create_bulk_payment_entry_and_reconcile,
				**for_party(OTHER_CUSTOMER),
			)
			assert_refused_for_names(
				self,
				create_bulk_payment_entry_and_reconcile,
				for_party,
				[],
				type_gated=True,
				caller_supplied=True,
			)
			assert_refused_for_names(
				self,
				create_bulk_payment_entry_and_reconcile,
				for_transaction,
				[],
				type_gated=True,
				caller_supplied=True,
			)
			result = create_bulk_payment_entry_and_reconcile(**for_party(self.customer))
		self.assertEqual(result[0]["transaction"].status, "Reconciled")
		self.assertEqual(result[0]["payment_entry"].party, self.customer)

		with as_user(accounts_user):
			result = create_bulk_payment_entry_and_reconcile(
				**bulk_kwargs(make_bank_transaction(self.bank_account, deposit=91).name, OTHER_CUSTOMER)
			)
		self.assertEqual(result[0]["payment_entry"].party, OTHER_CUSTOMER)

	def test_create_payment_entry_and_reconcile_refuses_party_outside_customer_fence(self):
		transaction = make_bank_transaction(self.bank_account, deposit=200)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Customer", self.customer)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def for_party(party):
			return {
				"bank_transaction_name": transaction.name,
				"payment_entry_doc": self.payment_entry_doc(party, 200),
			}

		def for_transaction(name):
			return {
				"bank_transaction_name": name,
				"payment_entry_doc": self.payment_entry_doc(self.customer, 200),
			}

		with as_user(fenced):
			assert_refused_without(
				self,
				self.party_links(OTHER_CUSTOMER),
				create_payment_entry_and_reconcile,
				**for_party(OTHER_CUSTOMER),
			)
			assert_refused_for_names(
				self, create_payment_entry_and_reconcile, for_party, [], caller_supplied=True
			)
			assert_refused_for_names(
				self,
				create_payment_entry_and_reconcile,
				for_transaction,
				[],
				type_gated=True,
				caller_supplied=True,
			)
			result = create_payment_entry_and_reconcile(**for_party(self.customer))
		self.assertEqual(result["transaction"].status, "Reconciled")
		self.assertEqual(result["payment_entry"].party, self.customer)

		with as_user(accounts_user):
			result = create_payment_entry_and_reconcile(
				make_bank_transaction(self.bank_account, deposit=200).name,
				self.payment_entry_doc(OTHER_CUSTOMER, 200),
			)
		self.assertEqual(result["payment_entry"].party, OTHER_CUSTOMER)

	def test_create_bulk_bank_entry_and_reconcile_refuses_transaction_outside_company_fence(self):
		outside = make_bank_transaction(make_other_company_bank_account(), deposit=84)
		inside = make_bank_transaction(self.bank_account, deposit=84)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Company", self.company)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def for_transaction(name):
			return {"bank_transactions": [name], "account": "_Test Cash - _TC"}

		with as_user(fenced):
			assert_refused_without(
				self,
				self.transaction_links(outside.name),
				create_bulk_bank_entry_and_reconcile,
				**for_transaction(outside.name),
			)
			assert_refused_for_names(
				self,
				create_bulk_bank_entry_and_reconcile,
				for_transaction,
				[],
				type_gated=True,
				caller_supplied=True,
			)
			result = create_bulk_bank_entry_and_reconcile(**for_transaction(inside.name))
		self.assertEqual(result[0]["transaction"].status, "Reconciled")
		self.assertEqual(result[0]["journal_entry"].company, self.company)

		with as_user(accounts_user):
			result = create_bulk_bank_entry_and_reconcile([outside.name], "Cash - _TC3")
		self.assertEqual(result[0]["journal_entry"].company, OTHER_COMPANY)

	def test_create_bulk_internal_transfer_refuses_transaction_outside_company_fence(self):
		outside = make_bank_transaction(make_other_company_bank_account(), deposit=83)
		inside = make_bank_transaction(self.bank_account, deposit=83)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Company", self.company)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def for_transaction(name):
			return {"bank_transaction_names": [name], "bank_account": "_Test Bank - _TC"}

		with as_user(fenced):
			assert_refused_without(
				self,
				self.transaction_links(outside.name),
				create_bulk_internal_transfer,
				**for_transaction(outside.name),
			)
			assert_refused_for_names(
				self,
				create_bulk_internal_transfer,
				for_transaction,
				[],
				type_gated=True,
				caller_supplied=True,
			)
			result = create_bulk_internal_transfer(**for_transaction(inside.name))
		self.assertEqual(result[0]["payment_entry"].paid_from, "_Test Bank - _TC")
		self.assertEqual(result[0]["transaction"].status, "Reconciled")

		with as_user(accounts_user):
			result = create_bulk_internal_transfer([outside.name], "Cash - _TC3")
		self.assertEqual(result[0]["payment_entry"].company, OTHER_COMPANY)

	def test_create_internal_transfer_refuses_counterpart_outside_account_fence(self):
		transaction = make_bank_transaction(self.bank_account, deposit=305)
		fenced = make_fenced_user(
			FENCED_USER, ["Accounts User"], [("Account", self.bank), ("Account", "_Test Cash - _TC")]
		)
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])
		forbidden_parent = frappe.db.get_value("Account", "_Test Bank - _TC", "parent_account")

		def for_paid_from(paid_from):
			return self.transfer_kwargs(paid_from, bank_transaction_name=transaction.name)

		def for_transaction(name):
			return self.transfer_kwargs("_Test Cash - _TC", bank_transaction_name=name)

		with as_user(fenced):
			assert_refused_without(
				self, [forbidden_parent], create_internal_transfer, **for_paid_from("_Test Bank - _TC")
			)
			assert_refused_for_names(
				self, create_internal_transfer, for_paid_from, [], type_gated=True, caller_supplied=True
			)
			assert_refused_for_names(
				self, create_internal_transfer, for_transaction, [], type_gated=True, caller_supplied=True
			)
			result = create_internal_transfer(**for_transaction(transaction.name))
		self.assertEqual(result["payment_entry"].paid_from, "_Test Cash - _TC")
		self.assertEqual(result["transaction"].status, "Reconciled")

		with as_user(accounts_user):
			result = create_internal_transfer(
				make_bank_transaction(self.bank_account, deposit=305).name,
				**self.transfer_kwargs("_Test Bank - _TC"),
			)
		self.assertEqual(result["payment_entry"].paid_from, "_Test Bank - _TC")

	def test_create_internal_transfer_refuses_counterpart_outside_company_fence(self):
		transaction = make_bank_transaction(self.bank_account, deposit=303)
		outside = make_bank_transaction(make_other_company_bank_account(), deposit=303)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Company", self.company)])

		with as_user(fenced):
			assert_refused_without(
				self,
				[OTHER_COMPANY],
				create_internal_transfer,
				transaction.name,
				**self.transfer_kwargs("Cash - _TC3"),
			)
			assert_refused_without(
				self,
				self.transaction_links(outside.name),
				create_internal_transfer,
				outside.name,
				**self.transfer_kwargs("_Test Cash - _TC"),
			)
			result = create_internal_transfer(transaction.name, **self.transfer_kwargs("_Test Cash - _TC"))
		self.assertEqual(result["payment_entry"].company, self.company)

	def test_create_internal_transfer_refuses_non_dimension_fields(self):
		transaction = make_bank_transaction(self.bank_account, deposit=311)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Customer", self.customer)])

		with as_user(fenced):
			for dimensions in (
				{"payment_type": "Receive", "party_type": "Customer", "party": OTHER_CUSTOMER},
				{"party": OTHER_CUSTOMER},
				{"cost_center": FENCED_COST_CENTER, "payment_type": "Receive"},
			):
				assert_refused(
					self,
					create_internal_transfer,
					transaction.name,
					**self.transfer_kwargs(self.debit_to, dimensions=dimensions),
				)
			result = create_internal_transfer(
				transaction.name,
				**self.transfer_kwargs(
					"_Test Cash - _TC", dimensions={"cost_center": FENCED_COST_CENTER, "project": None}
				),
			)
		self.assertEqual(result["payment_entry"].payment_type, "Internal Transfer")
		self.assertEqual(result["payment_entry"].cost_center, FENCED_COST_CENTER)
		self.assertFalse(result["payment_entry"].party)

	def test_update_clearance_date_refuses_voucher_outside_cost_center_fence(self):
		inside = self.make_payment(51, FENCED_COST_CENTER, "UP-CLR-IN")
		outside = self.make_payment(52, OTHER_COST_CENTER, "UP-CLR-OUT")
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Cost Center", FENCED_COST_CENTER)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def for_voucher(name):
			return {
				"payment_document": "Payment Entry",
				"payment_entry": name,
				"account": self.bank,
				"clearance_date": today(),
			}

		with as_user(fenced):
			assert_refused_without(
				self, [OTHER_COST_CENTER], update_clearance_date, **for_voucher(outside.name)
			)
			assert_refused_for_names(
				self, update_clearance_date, for_voucher, [], type_gated=True, caller_supplied=True
			)
			with self.assertRaises(frappe.PermissionError):
				update_clearance_date("User", "Administrator", self.bank, today())
		self.assertIsNone(frappe.db.get_value("Payment Entry", outside.name, "clearance_date"))

		with as_user(fenced):
			update_clearance_date("Payment Entry", inside.name, self.bank, today())
		self.assertEqual(str(frappe.db.get_value("Payment Entry", inside.name, "clearance_date")), today())

		with as_user(accounts_user):
			update_clearance_date("Payment Entry", outside.name, self.bank, today())
		self.assertEqual(str(frappe.db.get_value("Payment Entry", outside.name, "clearance_date")), today())

	def test_get_linked_payments_refuses_transaction_outside_company_fence(self):
		payment = self.make_payment(4321.17, FENCED_COST_CENTER, "UP-LNK")
		inside = make_bank_transaction(self.bank_account, deposit=4321.17)
		outside = make_bank_transaction(make_other_company_bank_account(), deposit=4321.17)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Company", self.company)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def for_transaction(name):
			return {"bank_transaction_name": name, "document_types": ["payment_entry"]}

		with as_user(fenced):
			assert_refused_without(
				self,
				self.transaction_links(outside.name),
				get_linked_payments,
				**for_transaction(outside.name),
			)
			assert_refused_for_names(
				self, get_linked_payments, for_transaction, [], type_gated=True, caller_supplied=True
			)
			matches = get_linked_payments(
				inside.name, ["payment_entry"], from_date=add_days(today(), -1), to_date=today()
			)
		names = []
		for match in matches:
			names.append(match.get("name"))
		self.assertIn(payment.name, names)

		with as_user(accounts_user):
			self.assertIsInstance(get_linked_payments(outside.name, ["payment_entry"]), list)

	def test_auto_reconcile_skips_voucher_outside_cost_center_fence(self):
		inside = self.make_payment(4011.13, FENCED_COST_CENTER, "UP-AR-IN")
		outside = self.make_payment(4012.29, OTHER_COST_CENTER, "UP-AR-OUT")
		inside_transaction = make_bank_transaction(
			self.bank_account, deposit=4011.13, reference_number="UP-AR-IN"
		)
		outside_transaction = make_bank_transaction(
			self.bank_account, deposit=4012.29, reference_number="UP-AR-OUT"
		)
		fenced = make_fenced_user(FENCED_USER, ["Accounts User"], [("Cost Center", FENCED_COST_CENTER)])
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])

		def for_bank_account(name):
			return {"bank_account": name, "from_date": add_days(today(), -1), "to_date": today()}

		with patch("frappe.enqueue") as enqueue:
			with as_user(fenced):
				assert_refused_for_names(
					self, auto_reconcile_vouchers, for_bank_account, [], type_gated=True, caller_supplied=True
				)
				frappe.local.message_log = []
				result = auto_reconcile_vouchers(**for_bank_account(self.bank_account))
				response = str(result)
				for message in frappe.local.message_log:
					response += str(message)
			self.assertNotIn(outside.name, response)
			self.assertEqual(
				frappe.db.get_value("Bank Transaction", inside_transaction.name, "status"), "Reconciled"
			)
			self.assertEqual(
				frappe.db.get_value("Bank Transaction", outside_transaction.name, "status"), "Unreconciled"
			)
			self.assertFalse(frappe.db.exists("Bank Transaction Payments", {"payment_entry": outside.name}))
			self.assertTrue(frappe.db.exists("Bank Transaction Payments", {"payment_entry": inside.name}))

			with as_user(accounts_user):
				auto_reconcile_vouchers(**for_bank_account(self.bank_account))
			self.assertEqual(
				frappe.db.get_value("Bank Transaction", outside_transaction.name, "status"), "Reconciled"
			)
			enqueue.assert_not_called()

	def reconcile_state(self, transaction_name, payment_name):
		return (
			frappe.db.get_value("Payment Entry", payment_name, "clearance_date"),
			frappe.db.get_value(
				"Bank Transaction", transaction_name, ["status", "allocated_amount", "unallocated_amount"]
			),
			frappe.db.count("Bank Transaction Payments", {"parent": transaction_name}),
			frappe.db.count("Bank Transaction Payments", {"payment_entry": payment_name}),
		)

	def assert_reconcile_unchanged(self, transaction_name, payment_name):
		self.assertEqual(
			self.reconcile_state(transaction_name, payment_name),
			(None, ("Unreconciled", 0, 63), 0, 0),
		)

	def test_reconcile_vouchers_refuses_falsy_and_unknown_voucher_names(self):
		payment = self.make_payment(63, FENCED_COST_CENTER, "UP-REC-FALSY")
		transaction = make_bank_transaction(self.bank_account, deposit=63)
		accounts_user = make_fenced_user(ACCOUNTS_USER, ["Accounts User"])
		self.assert_reconcile_unchanged(transaction.name, payment.name)

		with as_user(accounts_user):
			for payment_name in ("", None):
				assert_refused(
					self,
					reconcile_vouchers,
					transaction.name,
					self.voucher_json("Payment Entry", payment_name, 63),
				)
				self.assert_reconcile_unchanged(transaction.name, payment.name)
			for payment_name in (0, False, {"name": payment.name, "owner": accounts_user}, [payment.name]):
				with self.assertRaises(frappe.DoesNotExistError):
					reconcile_vouchers(transaction.name, self.voucher_json("Payment Entry", payment_name, 63))
				self.assert_reconcile_unchanged(transaction.name, payment.name)

	def test_reconcile_vouchers_dict_name_changes_nothing_for_administrator(self):
		payment = self.make_payment(63, FENCED_COST_CENTER, "UP-REC-ADMIN")
		transaction = make_bank_transaction(self.bank_account, deposit=63)
		self.assertEqual(frappe.session.user, "Administrator")

		with self.assertRaises(frappe.ValidationError):
			reconcile_vouchers(
				transaction.name, self.voucher_json("Payment Entry", {"name": payment.name}, 63)
			)
		self.assert_reconcile_unchanged(transaction.name, payment.name)
