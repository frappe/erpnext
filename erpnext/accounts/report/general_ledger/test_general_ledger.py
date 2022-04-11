# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.accounts.report.general_ledger.general_ledger import execute


class TestGeneralLedger(FrappeTestCase):
	def test_foreign_account_balance_after_exchange_rate_revaluation(self):
		"""
		Checks the correctness of balance after exchange rate revaluation
		"""
		# create a new account with USD currency
		account_name = "Test USD Account for Revalutation"
		company = "_Test Company"
		account = frappe.get_doc(
			{
				"account_name": account_name,
				"is_group": 0,
				"company": company,
				"root_type": "Asset",
				"report_type": "Balance Sheet",
				"account_currency": "USD",
				"inter_company_account": 0,
				"parent_account": "Bank Accounts - _TC",
				"account_type": "Bank",
				"doctype": "Account",
			}
		)
		account.insert(ignore_if_duplicate=True)
		# create a JV to debit 1000 USD at 75 exchange rate
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = today()
		jv.company = company
		jv.multi_currency = 1
		jv.cost_center = "_Test Cost Center - _TC"
		jv.set(
			"accounts",
			[
				{
					"account": account.name,
					"debit_in_account_currency": 1000,
					"credit_in_account_currency": 0,
					"exchange_rate": 75,
					"cost_center": "_Test Cost Center - _TC",
				},
				{
					"account": "Cash - _TC",
					"debit_in_account_currency": 0,
					"credit_in_account_currency": 75000,
					"cost_center": "_Test Cost Center - _TC",
				},
			],
		)
		jv.save()
		jv.submit()
		# create a JV to credit 900 USD at 100 exchange rate
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = today()
		jv.company = company
		jv.multi_currency = 1
		jv.cost_center = "_Test Cost Center - _TC"
		jv.set(
			"accounts",
			[
				{
					"account": account.name,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": 900,
					"exchange_rate": 100,
					"cost_center": "_Test Cost Center - _TC",
				},
				{
					"account": "Cash - _TC",
					"debit_in_account_currency": 90000,
					"credit_in_account_currency": 0,
					"cost_center": "_Test Cost Center - _TC",
				},
			],
		)
		jv.save()
		jv.submit()

		# create an exchange rate revaluation entry at 77 exchange rate
		revaluation = frappe.new_doc("Exchange Rate Revaluation")
		revaluation.posting_date = today()
		revaluation.company = company
		revaluation.set(
			"accounts",
			[
				{
					"account": account.name,
					"account_currency": "USD",
					"new_exchange_rate": 77,
					"new_balance_in_base_currency": 7700,
					"balance_in_base_currency": -15000,
					"balance_in_account_currency": 100,
					"current_exchange_rate": -150,
				}
			],
		)
		revaluation.save()
		revaluation.submit()

		# post journal entry to revaluate
		frappe.db.set_value(
			"Company", company, "unrealized_exchange_gain_loss_account", "_Test Exchange Gain/Loss - _TC"
		)
		revaluation_jv = revaluation.make_jv_entry()
		revaluation_jv = frappe.get_doc(revaluation_jv)
		revaluation_jv.cost_center = "_Test Cost Center - _TC"
		for acc in revaluation_jv.get("accounts"):
			acc.cost_center = "_Test Cost Center - _TC"
		revaluation_jv.save()
		revaluation_jv.submit()

		# check the balance of the account
		balance = frappe.db.sql(
			"""
				select sum(debit_in_account_currency) - sum(credit_in_account_currency)
				from `tabGL Entry`
				where account = %s
				group by account
			""",
			account.name,
		)

		self.assertEqual(balance[0][0], 100)

		# check if general ledger shows correct balance
		columns, data = execute(
			frappe._dict(
				{
					"company": company,
					"from_date": today(),
					"to_date": today(),
					"account": [account.name],
					"group_by": "Group by Voucher (Consolidated)",
				}
			)
		)

		self.assertEqual(data[1]["account"], account.name)
		self.assertEqual(data[1]["debit"], 1000)
		self.assertEqual(data[1]["credit"], 0)
		self.assertEqual(data[2]["debit"], 0)
		self.assertEqual(data[2]["credit"], 900)
		self.assertEqual(data[3]["debit"], 100)
		self.assertEqual(data[3]["credit"], 100)
