# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


from unittest.mock import patch

import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import (
	auto_reconcile_vouchers,
	create_journal_entry_bts,
	create_payment_entry_bts,
	get_bank_transactions,
	get_linked_payments,
	reconcile_vouchers,
)
from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.permission_test_utils import (
	MISSING_NAME,
	OTHER_COMPANY,
	as_user,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	disable_mandatory_accounting_dimensions,
	make_company_fenced_user,
	make_fenced_user,
)


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

		transaction = (
			frappe.get_doc(
				{
					"doctype": "Bank Transaction",
					"date": today(),
					"deposit": 100,
					"bank_account": self.bank_account,
					"currency": "INR",
				}
			)
			.insert()
			.submit()
		)
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


class TestBankReconciliationToolPermissions(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		disable_mandatory_accounting_dimensions()
		self.create_company()
		self.create_customer()
		self.other_customer = "_Test Customer 1"
		if not frappe.db.exists("Customer", self.other_customer):
			self.create_customer(customer_name=self.other_customer)
		self.clear_old_entries()
		if not frappe.db.exists("Bank", "UP Bank"):
			frappe.get_doc({"doctype": "Bank", "bank_name": "UP Bank"}).insert()
		self.bank_account = (
			frappe.get_doc(
				{
					"doctype": "Bank Account",
					"account_name": "UP Current",
					"bank": "UP Bank",
					"is_company_account": True,
					"account": self.bank,
				}
			)
			.insert()
			.name
		)
		self.payment_a, self.transaction_a = self.make_matched_pair(self.customer, "UP-A")
		self.payment_b, self.transaction_b = self.make_matched_pair(self.other_customer, "UP-B")

	def tearDown(self):
		frappe.db.rollback()

	def make_matched_pair(self, customer, reference):
		payment = create_payment_entry(
			company=self.company,
			posting_date=add_days(today(), -1),
			payment_type="Receive",
			party_type="Customer",
			party=customer,
			paid_from=self.debit_to,
			paid_to=self.bank,
			paid_amount=100,
		)
		payment.reference_no = reference
		payment.reference_date = add_days(today(), -1)
		payment.save().submit()
		transaction = (
			frappe.get_doc(
				{
					"doctype": "Bank Transaction",
					"date": today(),
					"deposit": 100,
					"bank_account": self.bank_account,
					"reference_number": reference,
					"currency": "INR",
				}
			)
			.insert()
			.submit()
		)
		return payment.name, transaction.name

	def vouchers(self, payment):
		return frappe.as_json([{"payment_doctype": "Payment Entry", "payment_name": payment, "amount": 100}])

	def reconcile_kwargs(self, name):
		return {"bank_transaction_name": name, "vouchers": self.vouchers(self.payment_a)}

	def payment_entry_kwargs(self, name, party_type="Customer", party=None):
		return {
			"bank_transaction_name": name,
			"party_type": party_type,
			"party": party or self.customer,
			"reference_number": "UP",
			"reference_date": today(),
			"posting_date": today(),
			"allow_edit": 1,
		}

	def journal_entry_kwargs(self, party):
		return {
			"bank_transaction_name": self.transaction_a,
			"posting_date": today(),
			"entry_type": "Bank Entry",
			"second_account": self.debit_to,
			"party_type": "Customer",
			"party": party,
			"allow_edit": 1,
		}

	def auto_reconcile_kwargs(self, name):
		return {
			"bank_account": name,
			"from_date": add_days(today(), -30),
			"to_date": add_days(today(), 30),
			"filter_by_reference_date": False,
		}

	def linked_payments_kwargs(self, name):
		return {
			"bank_transaction_name": name,
			"document_types": ["payment_entry"],
			"from_date": add_days(today(), -30),
			"to_date": add_days(today(), 30),
		}

	def test_reconcile_vouchers_refuses_a_transaction_outside_the_company_fence(self):
		fenced = make_company_fenced_user("bank-rec-fenced@example.com", ["Accounts User"], OTHER_COMPANY)
		with as_user(fenced):
			assert_refused_for_names(
				self, reconcile_vouchers, self.reconcile_kwargs, [self.transaction_a], caller_supplied=True
			)
			assert_refused_without(
				self,
				["linked to", "'_Test Company'"],
				reconcile_vouchers,
				**self.reconcile_kwargs(self.transaction_a),
			)

	def test_reconcile_vouchers_refuses_a_voucher_the_user_cannot_write(self):
		fenced = make_fenced_user(
			"bank-rec-voucher@example.com", ["Accounts User"], [("Payment Entry", self.payment_a)]
		)
		with as_user(fenced):
			assert_refused(self, reconcile_vouchers, self.transaction_b, self.vouchers(self.payment_b))
			transaction = reconcile_vouchers(self.transaction_a, self.vouchers(self.payment_a))
		self.assertEqual(transaction.status, "Reconciled")

	def test_reconcile_vouchers_allows_an_unfenced_accounts_user(self):
		user = make_fenced_user("bank-rec-open@example.com", ["Accounts User"])
		with as_user(user):
			transaction = reconcile_vouchers(self.transaction_b, self.vouchers(self.payment_b))
		self.assertEqual(transaction.status, "Reconciled")

	def test_reconcile_vouchers_accepts_doctypes_registered_through_the_hook(self):
		user = make_fenced_user("bank-rec-hook@example.com", ["Accounts User"])
		vouchers = frappe.as_json(
			[{"payment_doctype": "Payment Request", "payment_name": MISSING_NAME, "amount": 1}]
		)
		with patch(
			"erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_doctypes_for_bank_reconciliation",
			return_value=[
				"Payment Entry",
				"Journal Entry",
				"Sales Invoice",
				"Purchase Invoice",
				"Payment Request",
			],
		):
			with as_user(user):
				self.assertRaises(frappe.DoesNotExistError, reconcile_vouchers, self.transaction_a, vouchers)
		with as_user(user):
			self.assertRaises(frappe.ValidationError, reconcile_vouchers, self.transaction_a, vouchers)

	def test_create_payment_entry_bts_checks_the_party(self):
		fenced = make_fenced_user(
			"bank-rec-party@example.com", ["Accounts User"], [("Customer", self.customer)]
		)
		with as_user(fenced):
			for party_type, party in (("Customer", self.other_customer), ("User", "test@example.com")):
				assert_refused(
					self,
					create_payment_entry_bts,
					**self.payment_entry_kwargs(self.transaction_a, party_type, party),
				)
			payment = create_payment_entry_bts(**self.payment_entry_kwargs(self.transaction_a))
		self.assertEqual(payment.party, self.customer)

	def test_create_journal_entry_bts_checks_the_party(self):
		fenced = make_fenced_user(
			"bank-rec-je-party@example.com", ["Accounts User"], [("Customer", self.customer)]
		)
		with as_user(fenced):
			assert_refused(self, create_journal_entry_bts, **self.journal_entry_kwargs(self.other_customer))
			journal = create_journal_entry_bts(**self.journal_entry_kwargs(self.customer))
		parties = []
		for row in journal.accounts:
			parties.append(row.party)
		self.assertIn(self.customer, parties)

	def test_create_bts_refuses_a_transaction_outside_the_company_fence(self):
		fenced = make_company_fenced_user("bank-rec-bts-fenced@example.com", ["Accounts User"], OTHER_COMPANY)
		with as_user(fenced):
			assert_refused_for_names(
				self,
				create_payment_entry_bts,
				self.payment_entry_kwargs,
				[self.transaction_a],
				caller_supplied=True,
			)

	def test_auto_reconcile_vouchers_skips_records_the_user_cannot_write(self):
		fenced = make_fenced_user(
			"bank-rec-auto@example.com", ["Accounts User"], [("Payment Entry", self.payment_a)]
		)
		frappe.local.message_log = []
		with as_user(fenced):
			auto_reconcile_vouchers(**self.auto_reconcile_kwargs(self.bank_account))
		response = frappe.as_json(frappe.local.message_log)
		self.assertNotIn(self.transaction_b, response)
		self.assertNotIn(self.payment_b, response)
		self.assertEqual(frappe.db.get_value("Bank Transaction", self.transaction_a, "status"), "Reconciled")
		self.assertNotEqual(
			frappe.db.get_value("Bank Transaction", self.transaction_b, "status"), "Reconciled"
		)

	def test_auto_reconcile_vouchers_refuses_a_bank_account_outside_the_company_fence(self):
		fenced = make_company_fenced_user(
			"bank-rec-auto-fenced@example.com", ["Accounts User"], OTHER_COMPANY
		)
		with as_user(fenced):
			assert_refused_for_names(
				self,
				auto_reconcile_vouchers,
				self.auto_reconcile_kwargs,
				[self.bank_account],
				type_gated=True,
				caller_supplied=True,
			)

	def test_get_linked_payments_refuses_a_transaction_outside_the_company_fence(self):
		fenced = make_company_fenced_user("bank-rec-linked@example.com", ["Accounts User"], OTHER_COMPANY)
		with as_user(fenced):
			assert_refused_for_names(
				self,
				get_linked_payments,
				self.linked_payments_kwargs,
				[self.transaction_a],
				type_gated=True,
				caller_supplied=True,
			)
		user = make_fenced_user("bank-rec-linked-open@example.com", ["Accounts User"])
		with as_user(user):
			matches = get_linked_payments(**self.linked_payments_kwargs(self.transaction_a))
		names = []
		for match in matches:
			names.append(match.get("name"))
		self.assertIn(self.payment_a, names)
