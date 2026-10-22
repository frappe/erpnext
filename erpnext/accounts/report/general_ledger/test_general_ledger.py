# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, flt, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.general_ledger.general_ledger import execute
from erpnext.controllers.sales_and_purchase_return import make_return_doc


class TestGeneralLedger(FrappeTestCase):
	def test_snapshot_reports_use_live_data_for_restricted_users(self):
		from importlib import import_module
		from unittest.mock import patch

		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		class SnapshotReached(Exception):
			pass

		restricted = make_fenced_user(
			"gl-snapshot-fenced@example.com", ["Accounts User"], [("Company", "_Test Company")]
		)
		unrestricted = make_fenced_user("gl-snapshot-open@example.com", ["Accounts User"])
		for report in ("general_ledger", "balance_sheet", "profit_and_loss_statement", "trial_balance"):
			module = import_module(f"erpnext.accounts.report.{report}.{report}")
			for user, expect_live in ((restricted, True), (unrestricted, False)):
				with (
					as_user(user),
					patch.object(module, "execute", return_value="live") as live,
					patch(
						"frappe.database.duckdb.database.get_latest_sync", side_effect=SnapshotReached
					) as sync,
				):
					try:
						result = module.execute_snapshot_report(frappe._dict(company="_Test Company"))
					except SnapshotReached:
						result = "snapshot"
				self.assertEqual(result, "live" if expect_live else "snapshot", f"{report} as {user}")
				self.assertEqual((live.called, sync.called), (expect_live, not expect_live))

	def setUp(self):
		self.company = "_Test Company"
		self.clear_old_entries()

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

	def test_accounts_user_can_run_report(self):
		from frappe.desk.query_report import generate_report_result

		from erpnext.tests.permission_test_utils import as_user, make_fenced_user

		create_sales_invoice(company=self.company)
		user = make_fenced_user("gl-accounts-user@example.com", ["Accounts User"])
		filters = {
			"company": self.company,
			"from_date": today(),
			"to_date": today(),
			"categorize_by": "Categorize by Voucher (Consolidated)",
		}
		with as_user(user):
			result = generate_report_result(frappe.get_doc("Report", "General Ledger"), filters, user)

		self.assertTrue(result["result"])

	def test_categorize_by_party_separates_party_types(self):
		self.clear_old_entries()
		party = "_Test Customer"
		if not frappe.db.exists("Supplier", party):
			frappe.get_doc(
				doctype="Supplier", supplier_name=party, supplier_group="_Test Supplier Group"
			).insert(set_name=party)
		opening_date, period_date = add_days(today(), -60), today()
		self.make_party_journal_entry("Debtors - _TC", "Customer", party, 1000, opening_date)
		self.make_party_journal_entry("Debtors - _TC", "Customer", party, 200, period_date)
		self.make_party_journal_entry("Creditors - _TC", "Supplier", party, -400, opening_date)
		self.make_party_journal_entry("Creditors - _TC", "Supplier", party, -50, period_date)

		filters = frappe._dict(
			company=self.company,
			from_date=add_days(today(), -30),
			to_date=today(),
			categorize_by="Categorize by Party",
		)
		closing_rows = [r for r in execute(filters)[1] if r.get("account") == "'Closing (Opening + Total)'"]

		# one closing row per party type, then the grand closing
		self.assertEqual(sorted(r["debit"] - r["credit"] for r in closing_rows[:-1]), [-450, 1200])

	def make_party_journal_entry(self, account, party_type, party, amount, posting_date):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry

		jv = make_journal_entry(account, "_Test Bank - _TC", amount, posting_date=posting_date, save=False)
		jv.accounts[0].update({"party_type": party_type, "party": party})
		jv.insert()
		jv.submit()
		return jv

	def test_presentation_currency_without_exchange_rate(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import make_journal_entry
		from erpnext.accounts.report import utils as report_utils

		exchange_settings_disabled = frappe.db.get_single_value("Currency Exchange Settings", "disabled")
		self.addCleanup(
			frappe.db.set_single_value, "Currency Exchange Settings", "disabled", exchange_settings_disabled
		)
		frappe.db.delete("Currency Exchange", {"from_currency": "USD", "to_currency": "INR"})
		frappe.db.set_single_value("Currency Exchange Settings", "disabled", 1)
		getattr(report_utils, "__exchange_rates").clear()
		jv = make_journal_entry("_Test Bank - _TC", "_Test Cash - _TC", 8000, submit=True)
		filters = frappe._dict(
			company=self.company,
			from_date=today(),
			to_date=today(),
			account=["_Test Bank - _TC"],
			voucher_no=jv.name,
			presentation_currency="USD",
		)

		self.assertRaisesRegex(
			frappe.ValidationError, "Exchange rate from .*USD.* to .*INR", execute, filters
		)

		frappe.get_doc(
			doctype="Currency Exchange",
			date=today(),
			from_currency="USD",
			to_currency="INR",
			exchange_rate=80,
		).insert()
		total = next(r for r in execute(filters)[1] if r.get("account") == "'Total'")
		self.assertEqual(total["debit"], 100)
