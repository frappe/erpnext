# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.query_builder import functions
from frappe.query_builder.utils import DocType
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestExchangeRateRevaluation(AccountsTestMixin, IntegrationTestCase):
	def setUp(self):
		self.create_company()
		self.create_usd_receivable_account()
		self.create_item()
		self.create_customer()
		self.clear_old_entries()
		self.set_system_and_company_settings()

	def tearDown(self):
		frappe.db.rollback()

	def set_system_and_company_settings(self):
		# set number and currency precision
		system_settings = frappe.get_doc("System Settings")
		system_settings.float_precision = 2
		system_settings.currency_precision = 2
		system_settings.save()

		# Using Exchange Gain/Loss account for unrealized as well.
		company_doc = frappe.get_doc("Company", self.company)
		company_doc.unrealized_exchange_gain_loss_account = company_doc.exchange_gain_loss_account
		company_doc.save()

	@IntegrationTestCase.change_settings(
		"Accounts Settings",
		{"allow_multi_currency_invoices_against_single_party_account": 1, "allow_stale": 0},
	)
	def test_01_revaluation_of_forex_balance(self):
		"""
		Test Forex account balance and Journal creation post Revaluation
		"""
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debtors_usd,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			price_list_rate=100,
			do_not_submit=1,
		)
		si.currency = "USD"
		si.conversion_rate = 80
		si.save().submit()

		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = self.company
		err.posting_date = today()
		accounts = err.get_accounts_data()
		err.extend("accounts", accounts)
		row = err.accounts[0]
		row.new_exchange_rate = 85
		row.new_balance_in_base_currency = flt(row.new_exchange_rate * flt(row.balance_in_account_currency))
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		err.set_total_gain_loss()
		err = err.save().submit()

		# Create JV for ERR
		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("revaluation_jv"))
		je = je.submit()

		je.reload()
		self.assertEqual(je.voucher_type, "Exchange Rate Revaluation")
		self.assertEqual(je.total_debit, 8500.0)
		self.assertEqual(je.total_credit, 8500.0)

		gl = DocType("GL Entry")
		acc_balance = frappe.db.get_all(
			"GL Entry",
			filters={"account": self.debtors_usd, "is_cancelled": 0},
			fields=[(functions.Sum(gl.debit) - functions.Sum(gl.credit)).as_("balance")],
		)[0]
		self.assertEqual(acc_balance.balance, 8500.0)

	@IntegrationTestCase.change_settings(
		"Accounts Settings",
		{"allow_multi_currency_invoices_against_single_party_account": 1, "allow_stale": 0},
	)
	def test_02_accounts_only_with_base_currency_balance(self):
		"""
		Test Revaluation on Forex account with balance only in base currency
		"""
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debtors_usd,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			price_list_rate=100,
			do_not_submit=1,
		)
		si.currency = "USD"
		si.conversion_rate = 80
		si.save().submit()

		pe = get_payment_entry(si.doctype, si.name)
		pe.source_exchange_rate = 85
		pe.received_amount = 8500
		pe.save().submit()

		# Cancel the auto created gain/loss JE to simulate balance only in base currency
		je = frappe.db.get_all("Journal Entry Account", filters={"reference_name": si.name}, pluck="parent")[
			0
		]
		frappe.get_doc("Journal Entry", je).cancel()

		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = self.company
		err.posting_date = today()
		err.fetch_and_calculate_accounts_data()
		err = err.save().submit()

		# Create JV for ERR
		self.assertTrue(err.check_journal_entry_condition())
		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("zero_balance_jv"))
		je = je.submit()

		je.reload()
		self.assertEqual(je.voucher_type, "Exchange Gain Or Loss")
		self.assertEqual(len(je.accounts), 2)
		# Only base currency fields will be posted to
		for acc in je.accounts:
			self.assertEqual(acc.debit_in_account_currency, 0)
			self.assertEqual(acc.credit_in_account_currency, 0)

		self.assertEqual(je.total_debit, 500.0)
		self.assertEqual(je.total_credit, 500.0)

		gl = DocType("GL Entry")
		acc_balance = frappe.db.get_all(
			"GL Entry",
			filters={"account": self.debtors_usd, "is_cancelled": 0},
			fields=[
				(functions.Sum(gl.debit) - functions.Sum(gl.credit)).as_("balance"),
				(
					functions.Sum(gl.debit_in_account_currency) - functions.Sum(gl.credit_in_account_currency)
				).as_("balance_in_account_currency"),
			],
		)[0]
		# account shouldn't have balance in base and account currency
		self.assertEqual(acc_balance.balance, 0.0)
		self.assertEqual(acc_balance.balance_in_account_currency, 0.0)

	@IntegrationTestCase.change_settings(
		"Accounts Settings",
		{"allow_multi_currency_invoices_against_single_party_account": 1, "allow_stale": 0},
	)
	def test_03_accounts_only_with_account_currency_balance(self):
		"""
		Test Revaluation on Forex account with balance only in account currency
		"""
		precision = frappe.db.get_single_value("System Settings", "currency_precision")

		# posting on previous date to make sure that ERR picks up the Payment entry's exchange
		# rate while calculating gain/loss for account currency balance
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debtors_usd,
			posting_date=add_days(today(), -1),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			price_list_rate=100,
			do_not_submit=1,
		)
		si.currency = "USD"
		si.conversion_rate = 80
		si.save().submit()

		pe = get_payment_entry(si.doctype, si.name)
		pe.paid_amount = 95
		pe.source_exchange_rate = 84.2105
		pe.received_amount = 8000
		pe.references = []
		pe.save().submit()

		gl = DocType("GL Entry")
		acc_balance = frappe.db.get_all(
			"GL Entry",
			filters={"account": self.debtors_usd, "is_cancelled": 0},
			fields=[
				(functions.Sum(gl.debit) - functions.Sum(gl.credit)).as_("balance"),
				(
					functions.Sum(gl.debit_in_account_currency) - functions.Sum(gl.credit_in_account_currency)
				).as_("balance_in_account_currency"),
			],
		)[0]
		# account should have balance only in account currency
		self.assertEqual(flt(acc_balance.balance, precision), 0.0)
		self.assertEqual(flt(acc_balance.balance_in_account_currency, precision), 5.0)  # in USD

		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = self.company
		err.posting_date = today()
		err.fetch_and_calculate_accounts_data()
		err.set_total_gain_loss()
		err = err.save().submit()

		# Create JV for ERR
		self.assertTrue(err.check_journal_entry_condition())
		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("zero_balance_jv"))
		je = je.submit()

		je.reload()
		self.assertEqual(je.voucher_type, "Exchange Gain Or Loss")
		self.assertEqual(len(je.accounts), 2)
		# Only account currency fields will be posted to
		for acc in je.accounts:
			self.assertEqual(flt(acc.debit, precision), 0.0)
			self.assertEqual(flt(acc.credit, precision), 0.0)

		row = next(x for x in je.accounts if x.account == self.debtors_usd)
		self.assertEqual(flt(row.credit_in_account_currency, precision), 5.0)  # in USD
		row = next(x for x in je.accounts if x.account != self.debtors_usd)
		self.assertEqual(flt(row.debit_in_account_currency, precision), 421.05)  # in INR

		# total_debit and total_credit will be 0.0, as JV is posting only to account currency fields
		self.assertEqual(flt(je.total_debit, precision), 0.0)
		self.assertEqual(flt(je.total_credit, precision), 0.0)

		gl = DocType("GL Entry")
		acc_balance = frappe.db.get_all(
			"GL Entry",
			filters={"account": self.debtors_usd, "is_cancelled": 0},
			fields=[
				(functions.Sum(gl.debit) - functions.Sum(gl.credit)).as_("balance"),
				(
					functions.Sum(gl.debit_in_account_currency) - functions.Sum(gl.credit_in_account_currency)
				).as_("balance_in_account_currency"),
			],
		)[0]
		# account shouldn't have balance in base and account currency post revaluation
		self.assertEqual(flt(acc_balance.balance, precision), 0.0)
		self.assertEqual(flt(acc_balance.balance_in_account_currency, precision), 0.0)

	@IntegrationTestCase.change_settings(
		"Accounts Settings",
		{"allow_multi_currency_invoices_against_single_party_account": 1, "allow_stale": 0},
	)
	def test_04_get_account_details_function(self):
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debtors_usd,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			price_list_rate=100,
			do_not_submit=1,
		)
		si.currency = "USD"
		si.conversion_rate = 80
		si.save().submit()

		from erpnext.accounts.doctype.exchange_rate_revaluation.exchange_rate_revaluation import (
			get_account_details,
		)

		account_details = get_account_details(
			self.company, si.posting_date, self.debtors_usd, "Customer", self.customer, 0.05
		)
		# not checking for new exchange rate and balances as it is dependent on live exchange rates
		expected_data = {
			"account_currency": "USD",
			"balance_in_base_currency": 8000.0,
			"balance_in_account_currency": 100.0,
			"current_exchange_rate": 80.0,
			"zero_balance": False,
			"new_balance_in_account_currency": 100.0,
		}

		for key, _val in expected_data.items():
			self.assertEqual(expected_data.get(key), account_details.get(key))
