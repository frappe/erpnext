# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe import qb
from frappe.utils import add_days, flt, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.general_ledger.general_ledger import execute
from erpnext.controllers.sales_and_purchase_return import make_return_doc
from erpnext.tests.utils import ERPNextTestSuite


class TestGeneralLedger(ERPNextTestSuite):
	def setUp(self):
		self.company = "_Test Company"

	def test_gl_report_runs_with_remarks_length(self):
		# general_ledger_remarks_length adds `substr(remarks, 1, n) as remarks` to the raw SQL; the
		# alias must be unquoted to be valid on Postgres (a single-quoted alias is a string literal there).
		from frappe.utils import today

		frappe.db.set_single_value("Accounts Settings", "general_ledger_remarks_length", 50)
		self.addCleanup(frappe.db.set_single_value, "Accounts Settings", "general_ledger_remarks_length", 0)

		si = create_sales_invoice(company=self.company)
		self.addCleanup(self._cancel_and_delete, "Sales Invoice", si.name)

		columns, data = execute(
			frappe._dict(
				{
					"company": self.company,
					"from_date": today(),
					"to_date": today(),
					"group_by": "Group by Voucher (Consolidated)",
					# required to reach the `substr(remarks, 1, n) as remarks` branch under test
					"show_remarks": True,
				}
			)
		)
		self.assertTrue(columns)
		self.assertTrue(data)
		self.assertTrue(any("remarks" in row for row in data))

	@staticmethod
	def _cancel_and_delete(doctype, name):
		if not frappe.db.exists(doctype, name):
			return
		doc = frappe.get_doc(doctype, name)
		if doc.docstatus == 1:
			doc.cancel()
		frappe.delete_doc(doctype, name, force=1)

	def clear_old_entries(self):
		doctype_list = [
			"GL Entry",
			"Payment Ledger Entry",
			"Sales Invoice",
			"Purchase Invoice",
			"Payment Entry",
			"Journal Entry",
		]
		for doctype in doctype_list:
			qb.from_(qb.DocType(doctype)).delete().where(qb.DocType(doctype).company == self.company).run()

	def test_opening_total_and_closing_balances(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		self.clear_old_entries()
		# reuse bootstrap non-party accounts; clear_old_entries() leaves them clean of GL
		account = "_Test Account Cost for Goods Sold - _TC"
		offset = "_Test Bank - _TC"
		make_journal_entry(account, offset, 1000, posting_date=add_days(today(), -60), submit=True)  # opening
		make_journal_entry(account, offset, 200, posting_date=today(), submit=True)  # in period

		filters = frappe._dict(
			company=self.company, from_date=add_days(today(), -30), to_date=today(), account=[account]
		)
		labelled = {row.get("account"): row for row in execute(filters)[1]}

		self.assertEqual(labelled["'Opening'"]["debit"], 1000)
		self.assertEqual(labelled["'Total'"]["debit"], 200)
		self.assertEqual(labelled["'Closing (Opening + Total)'"]["debit"], 1200)

	def test_categorize_by_account_subtotals(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		self.clear_old_entries()
		# reuse bootstrap non-party accounts; clear_old_entries() leaves them clean of GL
		account_a = "_Test Account Cost for Goods Sold - _TC"
		account_b = "_Test Bank - _TC"
		offset = "_Test Cash - _TC"
		make_journal_entry(account_a, offset, 300, posting_date=today(), submit=True)
		make_journal_entry(account_b, offset, 400, posting_date=today(), submit=True)

		filters = frappe._dict(
			company=self.company,
			from_date=add_days(today(), -1),
			to_date=today(),
			categorize_by="Categorize by Account",
		)
		total_debits = [row["debit"] for row in execute(filters)[1] if row.get("account") == "'Total'"]

		# each account gets its own subtotal row, then a grand total (300 + 400) at the end
		self.assertIn(300, total_debits)
		self.assertIn(400, total_debits)
		self.assertEqual(total_debits[-1], 700)

	def test_party_filter_returns_only_that_party(self):
		self.clear_old_entries()
		create_sales_invoice(customer="_Test Customer", company=self.company, debit_to="Debtors - _TC")
		create_sales_invoice(customer="_Test Customer 1", company=self.company, debit_to="Debtors - _TC")

		filters = frappe._dict(
			company=self.company,
			from_date=add_days(today(), -1),
			to_date=today(),
			party_type="Customer",
			party=["_Test Customer"],
		)
		parties = {row.get("party") for row in execute(filters)[1] if row.get("party")}
		self.assertEqual(parties, {"_Test Customer"})

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
		revaluation_jv = revaluation.make_jv_for_revaluation()
		revaluation_jv.cost_center = "_Test Cost Center - _TC"
		for acc in revaluation_jv.get("accounts"):
			acc.cost_center = "_Test Cost Center - _TC"
		revaluation_jv.save()
		revaluation_jv.submit()

		# check the balance of the account
		balance = frappe.get_all(
			"GL Entry",
			filters={"account": account.name},
			fields=[
				{"SUM": "debit_in_account_currency", "as": "debit"},
				{"SUM": "credit_in_account_currency", "as": "credit"},
			],
			group_by="account",
		)

		self.assertEqual(flt(balance[0].debit) - flt(balance[0].credit), 100)

		# check if general ledger shows correct balance
		columns, data = execute(
			frappe._dict(
				{
					"company": company,
					"from_date": today(),
					"to_date": today(),
					"account": [account.name],
					"categorize_by": "Categorize by Voucher (Consolidated)",
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

	def test_ignore_exchange_rate_journals_filter(self):
		# create a new account with USD currency
		account_name = "Test Debtors USD"
		company = "_Test Company"
		account = frappe.get_doc(
			{
				"account_name": account_name,
				"is_group": 0,
				"company": company,
				"root_type": "Asset",
				"report_type": "Balance Sheet",
				"account_currency": "USD",
				"parent_account": "Accounts Receivable - _TC",
				"account_type": "Receivable",
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
					"party_type": "Customer",
					"party": "_Test Customer USD",
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

		revaluation = frappe.new_doc("Exchange Rate Revaluation")
		revaluation.posting_date = today()
		revaluation.company = company
		accounts = revaluation.get_accounts_data()
		revaluation.extend("accounts", accounts)
		row = revaluation.accounts[0]
		row.new_exchange_rate = 83
		row.new_balance_in_base_currency = flt(row.new_exchange_rate * flt(row.balance_in_account_currency))
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		revaluation.set_total_gain_loss()
		revaluation = revaluation.save().submit()

		# post journal entry for Revaluation doc
		frappe.db.set_value(
			"Company", company, "unrealized_exchange_gain_loss_account", "_Test Exchange Gain/Loss - _TC"
		)
		revaluation_jv = revaluation.make_jv_for_revaluation()
		revaluation_jv.cost_center = "_Test Cost Center - _TC"
		for acc in revaluation_jv.get("accounts"):
			acc.cost_center = "_Test Cost Center - _TC"
		revaluation_jv.save()
		revaluation_jv.submit()

		# With ignore_err enabled
		columns, data = execute(
			frappe._dict(
				{
					"company": company,
					"from_date": today(),
					"to_date": today(),
					"account": [account.name],
					"categorize_by": "Categorize by Voucher (Consolidated)",
					"ignore_err": True,
				}
			)
		)
		self.assertNotIn(revaluation_jv.name, set([x.voucher_no for x in data]))

		# Without ignore_err enabled
		columns, data = execute(
			frappe._dict(
				{
					"company": company,
					"from_date": today(),
					"to_date": today(),
					"account": [account.name],
					"categorize_by": "Categorize by Voucher (Consolidated)",
					"ignore_err": False,
				}
			)
		)
		self.assertIn(revaluation_jv.name, set([x.voucher_no for x in data]))

	def test_ignore_cr_dr_notes_filter(self):
		si = create_sales_invoice()

		cr_note = make_return_doc(si.doctype, si.name)
		cr_note.submit()

		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = si.company
		pr.party_type = "Customer"
		pr.party = si.customer
		pr.receivable_payable_account = si.debit_to

		pr.get_unreconciled_entries()

		invoices = [invoice.as_dict() for invoice in pr.invoices if invoice.invoice_number == si.name]
		payments = [payment.as_dict() for payment in pr.payments if payment.reference_name == cr_note.name]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		system_generated_journal = frappe.db.get_all(
			"Journal Entry",
			filters={
				"docstatus": 1,
				"reference_type": si.doctype,
				"reference_name": si.name,
				"voucher_type": "Credit Note",
				"is_system_generated": True,
			},
			fields=["name"],
		)
		self.assertEqual(len(system_generated_journal), 1)
		expected = set([si.name, cr_note.name, system_generated_journal[0].name])
		# Without ignore_cr_dr_notes
		columns, data = execute(
			frappe._dict(
				{
					"company": si.company,
					"from_date": si.posting_date,
					"to_date": si.posting_date,
					"account": [si.debit_to],
					"categorize_by": "Categorize by Voucher (Consolidated)",
					"ignore_cr_dr_notes": False,
				}
			)
		)
		actual = set([x.voucher_no for x in data if x.voucher_no])
		self.assertEqual(expected, actual)

		# Without ignore_cr_dr_notes
		expected = set([si.name, cr_note.name])
		columns, data = execute(
			frappe._dict(
				{
					"company": si.company,
					"from_date": si.posting_date,
					"to_date": si.posting_date,
					"account": [si.debit_to],
					"categorize_by": "Categorize by Voucher (Consolidated)",
					"ignore_cr_dr_notes": True,
				}
			)
		)
		actual = set([x.voucher_no for x in data if x.voucher_no])
		self.assertEqual(expected, actual)
