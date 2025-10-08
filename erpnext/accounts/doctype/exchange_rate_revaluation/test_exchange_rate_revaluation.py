# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, flt, nowdate, today ,get_date_str, getdate

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from frappe.exceptions import ValidationError


class TestExchangeRateRevaluation(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		create_warehouse(warehouse_name="_Test Warehouse")
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

	@change_settings(
		"Accounts Settings",
		{"allow_multi_currency_invoices_against_single_party_account": 1, "allow_stale": 0},
	)
	def test_01_revaluation_of_forex_balance(self):
		"""
		Test Forex account balance and Journal creation post Revaluation
		"""
		frappe.db.set_value("Customer", self.customer, "default_currency", "USD")
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

		acc_balance = frappe.db.get_all(
			"GL Entry",
			filters={"account": self.debtors_usd, "is_cancelled": 0},
			fields=["sum(debit)-sum(credit) as balance"],
		)[0]
		self.assertEqual(acc_balance.balance, 8500.0)

	@change_settings(
		"Accounts Settings",
		{"allow_multi_currency_invoices_against_single_party_account": 1, "allow_stale": 0},
	)
	def test_02_accounts_only_with_base_currency_balance(self):
		"""
		Test Revaluation on Forex account with balance only in base currency
		"""
		frappe.db.set_value("Customer", self.customer, "default_currency", "USD")
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

		acc_balance = frappe.db.sql(
			"""
			SELECT
				SUM(debit) - SUM(credit) AS balance,
				SUM(debit_in_account_currency) - SUM(credit_in_account_currency) AS balance_in_account_currency
			FROM `tabGL Entry`
			WHERE account = %s AND is_cancelled = 0
			""",
			(self.debtors_usd,),
			as_dict=True,
		)[0]
		# account shouldn't have balance in base and account currency
		self.assertEqual(acc_balance.balance, 0.0)
		self.assertEqual(acc_balance.balance_in_account_currency, 0.0)

	@change_settings(
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
		frappe.db.set_value("Customer", self.customer, "default_currency", "USD")
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

		acc_balance = frappe.db.sql(
			"""
			SELECT
				SUM(debit) - SUM(credit) AS balance,
				SUM(debit_in_account_currency) - SUM(credit_in_account_currency) AS balance_in_account_currency
			FROM `tabGL Entry`
			WHERE account = %s AND is_cancelled = 0
			""",
			(self.debtors_usd,),
			as_dict=True,
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

		acc_balance = frappe.db.sql(
			"""
			SELECT
				SUM(debit) - SUM(credit) AS balance,
				SUM(debit_in_account_currency) - SUM(credit_in_account_currency) AS balance_in_account_currency
			FROM `tabGL Entry`
			WHERE account = %s AND is_cancelled = 0
			""",
			(self.debtors_usd,),
			as_dict=True,
		)[0]
		# account shouldn't have balance in base and account currency post revaluation
		self.assertEqual(flt(acc_balance.balance, precision), 0.0)
		self.assertEqual(flt(acc_balance.balance_in_account_currency, precision), 0.0)

	@change_settings(
		"Accounts Settings",
		{"allow_multi_currency_invoices_against_single_party_account": 1, "allow_stale": 0},
	)
	def test_04_get_account_details_function(self):
		frappe.db.set_value("Customer", self.customer, "default_currency", "USD")
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

	def test_exchange_rate_for_unpaid_pi_TC_ACC_031(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_purchase_invoice

		create_records_for_err()
		supplier = frappe.get_doc("Supplier", "_Test Supplier USD")

		self.assertEqual(supplier.accounts[0].account, "_Test Payable USD - _TC")

		gain_loss_account("_Test Company")
		company = frappe.get_doc("Company", "_Test Company")
		self.assertEqual(company.exchange_gain_loss_account, "Exchange Gain/Loss - _TC")
		self.assertEqual(
			company.unrealized_exchange_gain_loss_account,
			"_Test Unrealized Profit - _TC",
		)

		pi = create_purchase_invoice(
			supplier=supplier.name,
			company="_Test Company",
			currency="USD",
			item_code=self.item,
			rate=100,
			credit_to="_Test Payable USD - _TC",
		)
		pi.conversion_rate = 63
		pi.save().submit()

		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = "_Test Company"
		err.posting_date = today()
		accounts = err.get_accounts_data()
		err.extend("accounts", accounts)

		row = err.accounts[0]
		row.new_exchange_rate = 60
		row.new_balance_in_base_currency = flt(row.new_exchange_rate * flt(row.balance_in_account_currency))
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		err.set_total_gain_loss()
		err = err.save().submit()

		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("revaluation_jv"))
		je = je.submit()
		je.reload()

		self.assertEqual(je.voucher_type, "Exchange Rate Revaluation")
		self.assertEqual(je.total_debit, 6300.0)
		self.assertEqual(je.total_credit, 6300.0)

		for account in je.accounts:
			if account.account == "Exchange Gain/Loss - _TC":
				if account.credit:
					self.assertEqual(account.credit, 6000.0)
				if account.debit:
					self.assertEqual(account.debit, 6300.0)
			if account.account == "_Test Unrealized Profit - _TC":
				self.assertEqual(account.credit, 300.0)

	def test_exhange_rate_for_overdue_pi_TC_ACC_032(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_purchase_invoice,
		)

		create_records_for_err()
		supplier = frappe.get_doc("Supplier", "_Test Supplier USD")

		self.assertEqual(supplier.accounts[0].account, "_Test Payable USD - _TC")

		gain_loss_account("_Test Company")
		company = frappe.get_doc("Company", "_Test Company")
		self.assertEqual(company.exchange_gain_loss_account, "Exchange Gain/Loss - _TC")
		self.assertEqual(
			company.unrealized_exchange_gain_loss_account,
			"_Test Unrealized Profit - _TC",
		)
		pi = create_purchase_invoice(
			supplier=supplier.name,
			posting_date=add_days(today(), -1),
			company="_Test Company",
			currency="USD",
			item_code=self.item,
			rate=100,
			credit_to="_Test Payable USD - _TC",
		)
		pi.conversion_rate = 63
		pi.save()
		pi.submit()

		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = "_Test Company"
		err.posting_date = add_days(today(), -1)
		accounts = err.get_accounts_data()
		err.extend("accounts", accounts)

		row = err.accounts[0]
		row.new_exchange_rate = 60
		row.new_balance_in_base_currency = flt(row.new_exchange_rate * flt(row.balance_in_account_currency))
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		err.set_total_gain_loss()
		err = err.save().submit()

		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("revaluation_jv"))
		je = je.submit()
		je.reload()

		self.assertEqual(je.voucher_type, "Exchange Rate Revaluation")
		self.assertEqual(je.total_debit, 6300.0)
		self.assertEqual(je.total_credit, 6300.0)

		for account in je.accounts:
			if account.account == "Exchange Gain/Loss - _TC":
				if account.credit:
					self.assertEqual(account.credit, 6000.0)
				if account.debit:
					self.assertEqual(account.debit, 6300.0)
			if account.account == "_Test Unrealized Profit - _TC":
				self.assertEqual(account.credit, 300.0)

	def test_exchange_rate_for_unpaid_si_TC_ACC_033(self):
		create_records_for_err()
		customer = frappe.get_doc("Customer", "_Test Customer USD")

		self.assertEqual(customer.accounts[0].account, "_Test Receivable USD - _TC")

		gain_loss_account("_Test Company")
		company = frappe.get_doc("Company", "_Test Company")
		self.assertEqual(company.exchange_gain_loss_account, "Exchange Gain/Loss - _TC")
		self.assertEqual(
			company.unrealized_exchange_gain_loss_account,
			"_Test Unrealized Profit - _TC",
		)

		si = create_sales_invoice(
			company="_Test Company",
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			item=self.item,
			item_name=self.item,
			rate=100,
			conversion_rate=63,
		)
		si.save()
		si.submit()

		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = "_Test Company"
		err.posting_date = today()
		accounts = err.get_accounts_data()
		err.extend("accounts", accounts)

		row = err.accounts[0]
		row.new_exchange_rate = 66
		row.new_balance_in_base_currency = flt(row.new_exchange_rate * flt(row.balance_in_account_currency))
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		err.set_total_gain_loss()
		err = err.save().submit()

		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("revaluation_jv"))
		je = je.submit()
		je.reload()

		self.assertEqual(je.voucher_type, "Exchange Rate Revaluation")
		self.assertEqual(je.total_debit, 6600.0)
		self.assertEqual(je.total_credit, 6600.0)

		for account in je.accounts:
			if account.account == "Exchange Gain/Loss - _TC":
				if account.credit:
					self.assertEqual(account.credit, 6300.0)
				if account.debit:
					self.assertEqual(account.debit, 6600.0)
			if account.account == "_Test Unrealized Profit - _TC":
				self.assertEqual(account.credit, 300.0)

	def test_exchange_rate_for_overdue_si_TC_ACC_034(self):
		create_records_for_err()
		customer = frappe.get_doc("Customer", "_Test Customer USD")

		self.assertEqual(customer.accounts[0].account, "_Test Receivable USD - _TC")

		gain_loss_account("_Test Company")
		company = frappe.get_doc("Company", "_Test Company")
		self.assertEqual(company.exchange_gain_loss_account, "Exchange Gain/Loss - _TC")
		self.assertEqual(
			company.unrealized_exchange_gain_loss_account,
			"_Test Unrealized Profit - _TC",
		)

		si = create_sales_invoice(
			company="_Test Company",
			customer="_Test Customer USD",
			posting_date=add_days(today(), -1),
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			item=self.item,
			item_name=self.item,
			rate=100,
			conversion_rate=63,
		)
		si.save()
		si.submit()

		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = "_Test Company"
		err.posting_date = add_days(today(), -1)
		accounts = err.get_accounts_data()
		err.extend("accounts", accounts)

		row = err.accounts[0]
		row.new_exchange_rate = 66
		row.new_balance_in_base_currency = flt(row.new_exchange_rate * flt(row.balance_in_account_currency))
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		err.set_total_gain_loss()
		err = err.save().submit()

		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("revaluation_jv"))
		je = je.submit()
		je.reload()

		self.assertEqual(je.voucher_type, "Exchange Rate Revaluation")
		self.assertEqual(je.total_debit, 6600.0)
		self.assertEqual(je.total_credit, 6600.0)

		for account in je.accounts:
			if account.account == "Exchange Gain/Loss - _TC":
				if account.credit:
					self.assertEqual(account.credit, 6300.0)
				if account.debit:
					self.assertEqual(account.debit, 6600.0)
			if account.account == "_Test Unrealized Profit - _TC":
				self.assertEqual(account.credit, 300.0)

	def test_debtor_payment_with_revaluation_TC_ACC_111(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_purchase_invoice,
		)
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
			check_gl_entries,
			get_jv_entry_account,
		)

		create_records_for_err()
		supplier = frappe.get_doc("Supplier", "_Test Supplier USD")

		self.assertEqual(supplier.accounts[0].account, "_Test Payable USD - _TC")

		gain_loss_account("_Test Company")
		company = frappe.get_doc("Company", "_Test Company")
		self.assertEqual(company.exchange_gain_loss_account, "Exchange Gain/Loss - _TC")
		self.assertEqual(
			company.unrealized_exchange_gain_loss_account,
			"_Test Unrealized Profit - _TC",
		)
		pi = create_purchase_invoice(
			supplier=supplier.name,
			company="_Test Company",
			currency="USD",
			item_code=self.item,
			rate=100,
			credit_to="_Test Payable USD - _TC",
		)
		pi.conversion_rate = 63
		pi.save()
		pi.submit()

		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = "_Test Company"
		accounts = err.get_accounts_data()
		err.extend("accounts", accounts)

		row = err.accounts[0]
		row.new_exchange_rate = 60
		row.new_balance_in_base_currency = flt(row.new_exchange_rate * flt(row.balance_in_account_currency))
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		err.set_total_gain_loss()
		err = err.save().submit()

		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("revaluation_jv"))
		je = je.submit()
		je.reload()

		self.assertEqual(je.voucher_type, "Exchange Rate Revaluation")
		self.assertEqual(je.total_debit, 6300.0)
		self.assertEqual(je.total_credit, 6300.0)

		for account in je.accounts:
			if account.account == "Exchange Gain/Loss - _TC":
				if account.credit:
					self.assertEqual(account.credit, 6000.0)
				if account.debit:
					self.assertEqual(account.debit, 6300.0)
			if account.account == "_Test Unrealized Profit - _TC":
				self.assertEqual(account.credit, 300.0)

		pe = get_payment_entry(pi.doctype, pi.name)
		pe.target_exchange_rate = 65
		pe.save()
		pe.submit()

		jea_parent = get_jv_entry_account(
			credit_to=pi.credit_to,
			reference_name=pi.name,
			party_type="Supplier",
			party=supplier.name,
			credit=200,
		)

		expected_jv_entries = [
			["Exchange Gain/Loss - _TC", 200.0, 0.0, pe.posting_date],
			["_Test Payable USD - _TC", 0.0, 200.0, pe.posting_date],
		]

		check_gl_entries(
			doc=self,
			voucher_no=jea_parent.parent,
			expected_gle=expected_jv_entries,
			posting_date=pi.posting_date,
			voucher_type="Journal Entry",
		)

	def test_creditor_payment_with_revaluation_TC_ACC_110(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import get_jv_entry_account
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import check_gl_entries

		create_records_for_err()
		customer = frappe.get_doc("Customer", "_Test Customer USD")

		self.assertEqual(customer.accounts[0].account, "_Test Receivable USD - _TC")

		gain_loss_account("_Test Company")
		company = frappe.get_doc("Company", "_Test Company")
		self.assertEqual(company.exchange_gain_loss_account, "Exchange Gain/Loss - _TC")
		self.assertEqual(
			company.unrealized_exchange_gain_loss_account,
			"_Test Unrealized Profit - _TC",
		)

		si = create_sales_invoice(
			company="_Test Company",
			customer="_Test Customer USD",
			debit_to="_Test Receivable USD - _TC",
			currency="USD",
			item=self.item,
			item_name=self.item,
			rate=100,
			conversion_rate=63,
		)
		si.save()
		si.submit()

		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = "_Test Company"
		err.posting_date = today()
		accounts = err.get_accounts_data()
		err.extend("accounts", accounts)

		row = err.accounts[0]
		row.new_exchange_rate = 60
		row.new_balance_in_base_currency = flt(row.new_exchange_rate * flt(row.balance_in_account_currency))
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		err.set_total_gain_loss()
		err = err.save().submit()

		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("revaluation_jv"))
		je = je.submit()
		je.reload()

		self.assertEqual(je.voucher_type, "Exchange Rate Revaluation")
		self.assertEqual(je.total_debit, 6300.0)
		self.assertEqual(je.total_credit, 6300.0)

		for account in je.accounts:
			if account.account == "Exchange Gain/Loss - _TC":
				if account.credit:
					self.assertEqual(account.credit, 6300.0)
				if account.debit:
					self.assertEqual(account.debit, 6600.0)
			if account.account == "_Test Unrealized Profit - _TC":
				self.assertEqual(account.debit, 300.0)
		pe = get_payment_entry("Sales Invoice", si.name)
		pe.source_exchange_rate = 65
		pe.save()
		pe.submit()

		jv_name = get_jv_entry_account(
			credit_to=si.debit_to, reference_name=si.name, party_type="Customer", party=pe.party, debit=200
		)

		self.assertEqual(
			frappe.db.get_value("Journal Entry", jv_name.parent, "voucher_type"), "Exchange Gain Or Loss"
		)

		expected_jv_entries = [
			["Exchange Gain/Loss - _TC", 0.0, 200.0, pe.posting_date],
			["_Test Receivable USD - _TC", 200.0, 0.0, pe.posting_date],
		]
		check_gl_entries(
			doc=self,
			voucher_no=jv_name.parent,
			expected_gle=expected_jv_entries,
			posting_date=pe.posting_date,
			voucher_type="Journal Entry",
		)

	def test_validate_rounding_loss_allowance_TC_ACC_320(self):
		err = frappe.get_doc(
			{
				"doctype": "Exchange Rate Revaluation",
				"company": self.company,
				"rounding_loss_allowance": 2,  # Invalid (>1)
				"accounts": [{"account": "Debtors - {}".format(self.company_abbr), "new_exchange_rate": 1.5}],
			}
		)

		with self.assertRaises(ValidationError) as cm:
			err.save()

		self.assertIn("Rounding Loss Allowance should be between 0 and 1", str(cm.exception))

	def test_remove_accounts_without_gain_loss_TC_ACC_321(self):
		err_doc = frappe.get_doc(
			{
				"doctype": "Exchange Rate Revaluation",
				"company": self.company,
				"posting_date": getdate(),  # 👈 ensures it's inside current FY
				"accounts": [
					frappe._dict(account=f"Debtors - {self.company_abbr}", gain_loss=0),
					frappe._dict(account=f"Creditors - {self.company_abbr}", gain_loss=None),
				],
			}
		)

		with self.assertRaises(ValidationError) as cm:
			err_doc.remove_accounts_without_gain_loss()

		self.assertIn("At least one account with exchange gain or loss is required", str(cm.exception))

	def test_throw_invalid_response_message_coverage_TC_ACC_322(self):
		doc = frappe.get_doc(
			{
				"doctype": "Exchange Rate Revaluation",
				"company": "_Test Company",
				"rounding_loss_allowance": 0.01,
				"accounts": [
					frappe._dict(
						account="Cash In Hand - _TC",
						balance_in_base_currency=0,
						new_balance_in_base_currency=0,
						gain_loss=0,
						new_exchange_rate=0.5,
					),
				],
			}
		).insert()

		accounts_data = doc.get_accounts_data()

		self.assertEqual(accounts_data, [])

	def test_get_for_unrealized_gain_loss_account_throws_TC_ACC_323(self):
		company_name = "_Test Company No GainLoss Account"
		if not frappe.db.exists("Company", company_name):
			frappe.get_doc(
				{"doctype": "Company", "company_name": company_name, "abbr": "TCA", "default_currency": "INR"}
			).insert()

		doc = frappe.get_doc(
			{
				"doctype": "Exchange Rate Revaluation",
				"company": company_name,
				"accounts": [
					frappe._dict(
						account="Cash In Hand - _TC",
						balance_in_base_currency=0,
						new_balance_in_base_currency=0,
						gain_loss=0,
						new_exchange_rate=0.5,
					),
				],
			}
		).insert()

		with self.assertRaises(ValidationError) as cm:
			doc.get_for_unrealized_gain_loss_account()

		self.assertIn("Please set Unrealized Exchange Gain/Loss Account", str(cm.exception))

	def test_get_accounts_data_triggers_throw_invalid_response_message_TC_ACC_336(self):
		doc = frappe.get_doc(
			{
				"doctype": "Exchange Rate Revaluation",
				"company": "_Test Company",
				"posting_date": getdate(),
				"rounding_loss_allowance": 0.01,
				"accounts": [
					frappe._dict(
						account="Cash In Hand - _TC",
						balance_in_base_currency=0,
						new_balance_in_base_currency=0,
						gain_loss=0,
						new_exchange_rate=0.5,
					),
				],
			}
		).insert()

		accounts_data = doc.get_accounts_data()

		self.assertEqual(accounts_data, [])

	def test_calculate_exchange_rate_using_last_gle_TC_ACC_382(self):
		from erpnext.accounts.utils import calculate_exchange_rate_using_last_gle

		existing = frappe.db.exists("GL Entry", {"voucher_no": "TEST-JE-001"})
		if existing:
			frappe.delete_doc("GL Entry", existing, force=True)

		gl_entry = frappe.get_doc({
			"doctype": "GL Entry",
			"posting_date": nowdate(),
			"company": "_Test Company",
			"account": "_Test Receivable - _TC",
			"voucher_type": "Journal Entry",
			"voucher_no": "TEST-JE-001",
			"debit": 200,
			"credit": 0,
			"debit_in_account_currency": 100,
			"credit_in_account_currency": 0,
			"is_cancelled": 0
		}).insert(ignore_permissions=True)

		rate = calculate_exchange_rate_using_last_gle(
			company="_Test Company",
			account="_Test Receivable - _TC",
			party_type=None,
			party=None,
		)

		self.assertEqual(rate, 2.0)
  
	def test_check_journal_entry_condition_mismatch_TC_ACC_530(self):
		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = "_Test Company"
		err.posting_date = today()
		accounts = err.get_accounts_data()
		err.extend("accounts", accounts)

		row = err.accounts[0]
		row.new_exchange_rate = 60
		row.new_balance_in_base_currency = flt(
			row.new_exchange_rate * flt(row.balance_in_account_currency)
		)
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		err.set_total_gain_loss()
		err = err.save().submit()

		exchange_gain_loss_account = err.get_for_unrealized_gain_loss_account()
		je = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"posting_date": nowdate(),
			"accounts": [
				{
					"account": exchange_gain_loss_account,
					"debit": 0,
					"credit": 200,
					"reference_type": "Exchange Rate Revaluation",
					"reference_name": err.name,
				},
				{
					"account": "_Test Receivable - _TC",
					"debit": 200,
					"credit": 0,
				},
			],
		})
		je.insert(ignore_permissions=True)
		je.submit()

		result = err.check_journal_entry_condition()
		self.assertTrue(result)
		je.cancel()

def gain_loss_account(company: str):
	doc = frappe.get_doc("Company", company)
	if not doc.exchange_gain_loss_account or doc.exchange_gain_loss_account != "Exchange Gain/Loss - _TC":
		doc.db_set("exchange_gain_loss_account", "Exchange Gain/Loss - _TC")
	if (
		not doc.unrealized_exchange_gain_loss_account
		or doc.unrealized_exchange_gain_loss_account != "_Test Unrealized Profit - _TC"
	):
		doc.db_set("unrealized_exchange_gain_loss_account", "_Test Unrealized Profit - _TC")


def create_account(**args):
	account_name = args.get("account_name")
	if not account_name:
		return

	company = args.get("company", " ")

	existing_account = frappe.db.exists("Account", {"name": f"{account_name} - _TC"})

	if not existing_account:
		try:
			doc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_type": args.get("account_type", " "),
					"account_name": account_name,
					"report_type": args.get("report_type", "Balance Sheet"),
					"root_type": args.get("root_type", "Liability"),
					"account_currency": args.get("account_currency", "INR"),
					"is_group": args.get("is_group", 0),
				}
			)
			if args.get("parent_account"):
				doc.parent_account = args.get("parent_account")
			if args.get("company"):
				doc.company = args.get("company")
			doc.insert(ignore_mandatory=True)
		except Exception as e:
			frappe.log_error(f"Account Creation Failed: {account_name}", str(e))


def create_records_for_err():
	from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_supplier
	from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_customer

	create_warehouse(warehouse_name="_Test Warehouse", company="_Test Company")

	create_account(
		account_name="_Test Payable USD",
		parent_account="Current Assets - _TC",
		company="_Test Company",
		account_currency="USD",
		account_type="Receivable",
		root_type="Asset",
		report_type="Balance Sheet",
	)

	create_account(
		account_name="_Test Exchange Gain/Loss",
		parent_account="Indirect Expenses - _TC",
		company="_Test Company",
		account_currency="INR",
		report_type="Profit and Loss",
		root_type="Expense",
	)

	create_account(
		account_name="_Test Unrealized Profit",
		parent_account="Current Liabilities - _TC",
		company="_Test Company",
		account_currency="INR",
		root_type="Liability",
		report_type="Balance Sheet",
	)
	create_cost_center(
		cost_center_name="_Test Cost Center",
		company="_Test Company",
		parent_cost_center="_Test Company - _TC",
	)

	create_account(
		account_name="_Test Receivable USD",
		parent_account="Current Assets - _TC",
		company="_Test Company",
		account_currency="USD",
		account_type="Receivable",
	)
	create_account(
		account_name="_Test Cash",
		parent_account="Cash In Hand - _TC",
		company="_Test Company",
		account_currency="INR",
		account_type="Cash",
	)

	create_customer(
		customer_name="_Test Customer USD",
		currency="USD",
		company="_Test Company",
		account="_Test Receivable USD - _TC",
	)
	supplier = create_supplier(
		supplier_name="_Test Supplier USD",
		company="_Test Company",
		default_currency="USD",
	)

	if not supplier.accounts:
		supplier.append(
			"accounts",
			{
				"account": "_Test Payable USD - _TC",
				"company": "_Test Company",
			},
		)
		supplier.save()


def create_warehouse(**args):
	warehouse_name = args.get("warehouse_name")
	company = args.get("company", "_Test Company")
	full_warehouse_name = f"{warehouse_name} - _TC"
	if not frappe.db.exists("Warehouse", full_warehouse_name):
		frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": warehouse_name,
				"company": company,
			}
		).insert(ignore_mandatory=True)


def create_cost_center(**args):
	args = frappe._dict(args)
	if args.cost_center_name:
		company = args.company or "_Test Company"
		company_abbr = frappe.db.get_value("Company", company, "abbr")
		cc_name = args.cost_center_name + " - " + company_abbr
		if not frappe.db.exists("Cost Center", cc_name):
			cc = frappe.new_doc("Cost Center")
			cc.company = args.company or "_Test Company"
			cc.cost_center_name = args.cost_center_name
			cc.is_group = args.is_group or 0
			cc.parent_cost_center = args.parent_cost_center or "_Test Company - _TC"
			cc.insert()


def get_fy_list(year_start_date, year_end_date):
	return frappe.db.sql(
		"""select name from `tabFiscal Year`
			where (
				(%(year_start_date)s between year_start_date and year_end_date)
				or (%(year_end_date)s between year_start_date and year_end_date)
				or (year_start_date between %(year_start_date)s and %(year_end_date)s)
				or (year_end_date between %(year_start_date)s and %(year_end_date)s)
			) """,
		{
			"year_start_date": year_start_date,
			"year_end_date": year_end_date,
		},
		as_dict=True,
	)
