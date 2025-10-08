# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.tests.utils import change_settings
from frappe.utils import flt, getdate, nowdate

from erpnext.accounts.doctype.account.test_account import get_inventory_account
from erpnext.accounts.doctype.journal_entry.journal_entry import StockAccountInvalidTransaction
from erpnext.exceptions import InvalidAccountCurrency


class TestJournalEntry(unittest.TestCase):
	@change_settings("Accounts Settings", {"unlink_payment_on_cancellation_of_invoice": 1})
	def test_journal_entry_with_against_jv(self):
		jv_invoice = frappe.copy_doc(test_records[2])
		base_jv = frappe.copy_doc(test_records[0])
		self.jv_against_voucher_testcase(base_jv, jv_invoice)

	def test_jv_against_sales_order(self):
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		sales_order = make_sales_order(do_not_save=True)
		base_jv = frappe.copy_doc(test_records[0])
		self.jv_against_voucher_testcase(base_jv, sales_order)

	def test_jv_against_purchase_order(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		purchase_order = create_purchase_order(do_not_save=True)
		base_jv = frappe.copy_doc(test_records[1])
		self.jv_against_voucher_testcase(base_jv, purchase_order)

	def jv_against_voucher_testcase(self, base_jv, test_voucher):
		dr_or_cr = "credit" if test_voucher.doctype in ["Sales Order", "Journal Entry"] else "debit"

		test_voucher.insert()
		test_voucher.submit()

		if test_voucher.doctype == "Journal Entry":
			self.assertTrue(
				frappe.db.sql(
					"""select name from `tabJournal Entry Account`
				where account = %s and docstatus = 1 and parent = %s""",
					("Debtors - _TC", test_voucher.name),
				)
			)

		self.assertFalse(
			frappe.db.sql(
				"""select name from `tabJournal Entry Account`
			where reference_type = %s and reference_name = %s""",
				(test_voucher.doctype, test_voucher.name),
			)
		)

		base_jv.get("accounts")[0].is_advance = (
			"Yes" if (test_voucher.doctype in ["Sales Order", "Purchase Order"]) else "No"
		)
		base_jv.get("accounts")[0].set("reference_type", test_voucher.doctype)
		base_jv.get("accounts")[0].set("reference_name", test_voucher.name)
		base_jv.insert()
		base_jv.submit()

		submitted_voucher = frappe.get_doc(test_voucher.doctype, test_voucher.name)

		self.assertTrue(
			frappe.db.sql(
				f"""select name from `tabJournal Entry Account`
			where reference_type = %s and reference_name = %s and {dr_or_cr}=400""",
				(submitted_voucher.doctype, submitted_voucher.name),
			)
		)

		if base_jv.get("accounts")[0].is_advance == "Yes":
			self.advance_paid_testcase(base_jv, submitted_voucher, dr_or_cr)
		self.cancel_against_voucher_testcase(submitted_voucher)

	def advance_paid_testcase(self, base_jv, test_voucher, dr_or_cr):
		# Test advance paid field
		advance_paid = frappe.db.sql(
			"""select advance_paid from `tab{}`
					where name={}""".format(test_voucher.doctype, "%s"),
			(test_voucher.name),
		)
		payment_against_order = base_jv.get("accounts")[0].get(dr_or_cr)

		self.assertTrue(flt(advance_paid[0][0]) == flt(payment_against_order))

	def cancel_against_voucher_testcase(self, test_voucher):
		if test_voucher.doctype == "Journal Entry":
			# if test_voucher is a Journal Entry, test cancellation of test_voucher
			test_voucher.cancel()
			self.assertFalse(
				frappe.db.sql(
					"""select name from `tabJournal Entry Account`
				where reference_type='Journal Entry' and reference_name=%s""",
					test_voucher.name,
				)
			)

		elif test_voucher.doctype in ["Sales Order", "Purchase Order"]:
			# if test_voucher is a Sales Order/Purchase Order, test error on cancellation of test_voucher
			frappe.db.set_single_value(
				"Accounts Settings", "unlink_advance_payment_on_cancelation_of_order", 0
			)
			submitted_voucher = frappe.get_doc(test_voucher.doctype, test_voucher.name)
			try:
				submitted_voucher.cancel()
			except Exception:
				pass

	def test_jv_against_stock_account(self):
		company = "_Test Company with perpetual inventory"
		stock_account = get_inventory_account(company)

		from erpnext.accounts.utils import get_stock_and_account_balance

		account_bal, stock_bal, warehouse_list = get_stock_and_account_balance(
			stock_account, nowdate(), company
		)
		diff = flt(account_bal) - flt(stock_bal)

		if not diff:
			diff = 100

		jv = frappe.new_doc("Journal Entry")
		jv.company = company
		jv.posting_date = nowdate()
		jv.append(
			"accounts",
			{
				"account": stock_account,
				"cost_center": "Main - TCP1",
				"debit_in_account_currency": 0 if diff > 0 else abs(diff),
				"credit_in_account_currency": diff if diff > 0 else 0,
			},
		)

		jv.append(
			"accounts",
			{
				"account": "Stock Adjustment - TCP1",
				"cost_center": "Main - TCP1",
				"debit_in_account_currency": diff if diff > 0 else 0,
				"credit_in_account_currency": 0 if diff > 0 else abs(diff),
			},
		)

		if account_bal == stock_bal and (account_bal > 0 and stock_bal > 0):
			self.assertRaises(StockAccountInvalidTransaction, jv.save)
			frappe.db.rollback()
		else:
			jv.submit()
			jv.cancel()

	def test_multi_currency(self):
		jv = make_journal_entry("_Test Bank USD - _TC", "_Test Bank - _TC", 100, exchange_rate=50, save=False)

		jv.get("accounts")[1].credit_in_account_currency = 5000
		jv.submit()

		self.voucher_no = jv.name

		self.fields = [
			"account",
			"account_currency",
			"debit",
			"debit_in_account_currency",
			"credit",
			"credit_in_account_currency",
		]

		self.expected_gle = [
			{
				"account": "_Test Bank - _TC",
				"account_currency": "INR",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 5000,
				"credit_in_account_currency": 5000,
			},
			{
				"account": "_Test Bank USD - _TC",
				"account_currency": "USD",
				"debit": 5000,
				"debit_in_account_currency": 100,
				"credit": 0,
				"credit_in_account_currency": 0,
			},
		]

		self.check_gl_entries()

		# cancel
		jv.cancel()

		gle = frappe.db.sql(
			"""select name from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""",
			jv.name,
		)

		self.assertFalse(gle)

	def test_reverse_journal_entry(self):
		from erpnext.accounts.doctype.journal_entry.journal_entry import make_reverse_journal_entry

		jv = make_journal_entry("_Test Bank USD - _TC", "Sales - _TC", 100, exchange_rate=50, save=False)

		jv.get("accounts")[1].credit_in_account_currency = 5000
		jv.get("accounts")[1].exchange_rate = 1
		jv.submit()

		rjv = make_reverse_journal_entry(jv.name)
		rjv.posting_date = nowdate()
		rjv.submit()

		self.voucher_no = rjv.name

		self.fields = [
			"account",
			"account_currency",
			"debit",
			"credit",
			"debit_in_account_currency",
			"credit_in_account_currency",
		]

		self.expected_gle = [
			{
				"account": "Sales - _TC",
				"account_currency": "INR",
				"debit": 5000,
				"debit_in_account_currency": 5000,
				"credit": 0,
				"credit_in_account_currency": 0,
			},
			{
				"account": "_Test Bank USD - _TC",
				"account_currency": "USD",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 5000,
				"credit_in_account_currency": 100,
			},
		]

		self.check_gl_entries()

	def test_disallow_change_in_account_currency_for_a_party(self):
		# create jv in USD
		jv = make_journal_entry("_Test Bank USD - _TC", "_Test Receivable USD - _TC", 100, save=False)

		jv.accounts[1].update({"party_type": "Customer", "party": "_Test Customer USD"})

		jv.submit()

		# create jv in USD, but account currency in INR
		jv = make_journal_entry("_Test Bank - _TC", "Debtors - _TC", 100, save=False)

		jv.accounts[1].update({"party_type": "Customer", "party": "_Test Customer USD"})

		self.assertRaises(InvalidAccountCurrency, jv.submit)

		# back in USD
		jv = make_journal_entry("_Test Bank USD - _TC", "_Test Receivable USD - _TC", 100, save=False)

		jv.accounts[1].update({"party_type": "Customer", "party": "_Test Customer USD"})

		jv.submit()

	def test_inter_company_jv(self):
		jv = make_journal_entry(
			"Sales Expenses - _TC",
			"Buildings - _TC",
			100,
			posting_date=nowdate(),
			cost_center="Main - _TC",
			save=False,
		)
		jv.voucher_type = "Inter Company Journal Entry"
		jv.multi_currency = 0
		jv.insert()
		jv.submit()

		jv1 = make_journal_entry(
			"Sales Expenses - _TC1",
			"Buildings - _TC1",
			100,
			posting_date=nowdate(),
			cost_center="Main - _TC1",
			save=False,
		)
		jv1.inter_company_journal_entry_reference = jv.name
		jv1.company = "_Test Company 1"
		jv1.voucher_type = "Inter Company Journal Entry"
		jv1.multi_currency = 0
		jv1.insert()
		jv1.submit()

		jv.reload()

		self.assertEqual(jv.inter_company_journal_entry_reference, jv1.name)
		self.assertEqual(jv1.inter_company_journal_entry_reference, jv.name)

		jv.cancel()
		jv1.reload()
		jv.reload()

		self.assertEqual(jv.inter_company_journal_entry_reference, "")
		self.assertEqual(jv1.inter_company_journal_entry_reference, "")

	def test_jv_with_cost_centre(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center

		cost_center = "_Test Cost Center for BS Account - _TC"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")
		jv = make_journal_entry(
			"_Test Cash - _TC", "_Test Bank - _TC", 100, cost_center=cost_center, save=False
		)
		jv.voucher_type = "Bank Entry"
		jv.multi_currency = 0
		jv.cheque_no = "112233"
		jv.cheque_date = nowdate()
		jv.insert()
		jv.submit()

		self.voucher_no = jv.name

		self.fields = [
			"account",
			"cost_center",
		]

		self.expected_gle = [
			{
				"account": "_Test Bank - _TC",
				"cost_center": cost_center,
			},
			{
				"account": "_Test Cash - _TC",
				"cost_center": cost_center,
			},
		]

		self.check_gl_entries()

	def test_jv_account_and_party_balance_with_cost_centre(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		from erpnext.accounts.utils import get_balance_on

		cost_center = "_Test Cost Center for BS Account - _TC"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")
		jv = make_journal_entry(
			"_Test Cash - _TC", "_Test Bank - _TC", 100, cost_center=cost_center, save=False
		)
		account_balance = get_balance_on(account="_Test Bank - _TC", cost_center=cost_center)
		jv.voucher_type = "Bank Entry"
		jv.multi_currency = 0
		jv.cheque_no = "112233"
		jv.cheque_date = nowdate()
		jv.insert()
		jv.submit()

		expected_account_balance = account_balance - 100
		account_balance = get_balance_on(account="_Test Bank - _TC", cost_center=cost_center)
		self.assertEqual(expected_account_balance, account_balance)

	def test_journal_entry_basic_TC_ACC_049(self):
		# Arrange: Create a simple journal entry
		jv = make_journal_entry("_Test Bank - _TC", "_Test Cash - _TC", 100, save=False)
		jv.voucher_type = "Depreciation Entry"
		jv.insert()

		# Act: Submit the journal entry
		jv.submit()

		# Assert: Verify GL entries
		gl_entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": jv.name},
			fields=["account", "debit", "credit"],
		)
		self.assertEqual(len(gl_entries), 2)
		self.assertIn({"account": "_Test Bank - _TC", "debit": 100, "credit": 0}, gl_entries)
		self.assertIn({"account": "_Test Cash - _TC", "debit": 0, "credit": 100}, gl_entries)

		# Cleanup: Cancel the journal entry
		jv.cancel()

	def test_journal_entry_credit_note_TC_ACC_051(self):
		# Arrange: Create a Journal Entry with type 'Credit Note'
		jv = make_journal_entry("_Test Receivable - _TC", "_Test Bank - _TC", 500, save=False)
		jv.voucher_type = "Credit Note"

		# Set Party Type and Party for the receivable account
		jv.accounts[0].party_type = "Customer"
		jv.accounts[0].party = "_Test Customer"

		jv.insert()

		# Act: Submit the Journal Entry
		jv.submit()

		# Assert: Verify GL entries
		gl_entries = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": jv.name},
			fields=["account", "debit", "credit"],
		)
		self.assertEqual(len(gl_entries), 2)
		# Correct the expected values for debit and credit
		self.assertIn({"account": "_Test Receivable - _TC", "debit": 500, "credit": 0}, gl_entries)
		self.assertIn({"account": "_Test Bank - _TC", "debit": 0, "credit": 500}, gl_entries)

		# Cleanup: Cancel the Journal Entry
		jv.cancel()

	def test_repost_accounting_entries(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center

		# Configure Repost Accounting Ledger for JVs
		settings = frappe.get_doc("Repost Accounting Ledger Settings")
		if not [x for x in settings.allowed_types if x.document_type == "Journal Entry"]:
			settings.append("allowed_types", {"document_type": "Journal Entry", "allowed": True})
		settings.save()

		# Create JV with defaut cost center - _Test Cost Center
		jv = make_journal_entry("_Test Cash - _TC", "_Test Bank - _TC", 100, save=False)
		jv.multi_currency = 0
		jv.submit()

		# Check GL entries before reposting
		self.voucher_no = jv.name

		self.fields = [
			"account",
			"debit_in_account_currency",
			"credit_in_account_currency",
			"cost_center",
		]

		self.expected_gle = [
			{
				"account": "_Test Bank - _TC",
				"debit_in_account_currency": 0,
				"credit_in_account_currency": 100,
				"cost_center": "_Test Cost Center - _TC",
			},
			{
				"account": "_Test Cash - _TC",
				"debit_in_account_currency": 100,
				"credit_in_account_currency": 0,
				"cost_center": "_Test Cost Center - _TC",
			},
		]

		self.check_gl_entries()

		# Change cost center for bank account - _Test Cost Center for BS Account
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")
		jv.accounts[1].cost_center = "_Test Cost Center for BS Account - _TC"
		# Ledger reposted implicitly upon 'Update After Submit'
		jv.save()

		# Check GL entries after reposting
		jv.load_from_db()
		self.expected_gle[0]["cost_center"] = "_Test Cost Center for BS Account - _TC"
		self.check_gl_entries()

	def check_gl_entries(self):
		gl = frappe.qb.DocType("GL Entry")
		query = frappe.qb.from_(gl)
		for field in self.fields:
			query = query.select(gl[field])

		query = query.where(
			(gl.voucher_type == "Journal Entry") & (gl.voucher_no == self.voucher_no) & (gl.is_cancelled == 0)
		).orderby(gl.account)

		gl_entries = query.run(as_dict=True)
		for i in range(len(self.expected_gle)):
			for field in self.fields:
				self.assertEqual(self.expected_gle[i][field], gl_entries[i][field])

	def test_negative_debit_and_credit_with_same_account_head(self):
		from erpnext.accounts.general_ledger import process_gl_map

		# Create JV with defaut cost center - _Test Cost Center
		frappe.db.set_single_value("Accounts Settings", "merge_similar_account_heads", 0)

		jv = make_journal_entry("_Test Bank - _TC", "_Test Bank - _TC", 100 * -1, save=True)
		jv.append(
			"accounts",
			{
				"account": "_Test Cash - _TC",
				"debit": 100 * -1,
				"credit": 100 * -1,
				"debit_in_account_currency": 100 * -1,
				"credit_in_account_currency": 100 * -1,
				"exchange_rate": 1,
			},
		)
		jv.flags.ignore_validate = True
		jv.save()

		self.assertEqual(len(jv.accounts), 3)

		gl_map = jv.build_gl_map()

		for row in gl_map:
			if row.account == "_Test Cash - _TC":
				self.assertEqual(row.debit_in_account_currency, 100 * -1)
				self.assertEqual(row.credit_in_account_currency, 100 * -1)

		gl_map = process_gl_map(gl_map, False)

		for row in gl_map:
			if row.account == "_Test Cash - _TC":
				self.assertEqual(row.debit_in_account_currency, 100)
				self.assertEqual(row.credit_in_account_currency, 100)

	def test_toggle_debit_credit_if_negative(self):
		from erpnext.accounts.general_ledger import process_gl_map

		# Create JV with defaut cost center - _Test Cost Center
		frappe.db.set_single_value("Accounts Settings", "merge_similar_account_heads", 0)
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = nowdate()
		jv.company = "_Test Company"
		jv.user_remark = "test"
		jv.extend(
			"accounts",
			[
				{
					"account": "_Test Cash - _TC",
					"debit": 100 * -1,
					"debit_in_account_currency": 100 * -1,
					"exchange_rate": 1,
				},
				{
					"account": "_Test Bank - _TC",
					"credit": 100 * -1,
					"credit_in_account_currency": 100 * -1,
					"exchange_rate": 1,
				},
			],
		)
		jv.flags.ignore_validate = True
		jv.save()
		self.assertEqual(len(jv.accounts), 2)
		gl_map = jv.build_gl_map()
		for row in gl_map:
			if row.account == "_Test Cash - _TC":
				self.assertEqual(row.debit, 100 * -1)
				self.assertEqual(row.debit_in_account_currency, 100 * -1)
				self.assertEqual(row.debit_in_transaction_currency, 100 * -1)
		gl_map = process_gl_map(gl_map, False)
		for row in gl_map:
			if row.account == "_Test Cash - _TC":
				self.assertEqual(row.credit, 100)
				self.assertEqual(row.credit_in_account_currency, 100)
				self.assertEqual(row.credit_in_transaction_currency, 100)

	def test_transaction_exchange_rate_on_journals(self):
		jv = make_journal_entry("_Test Bank - _TC", "_Test Receivable USD - _TC", 100, save=False)
		jv.accounts[0].update({"debit_in_account_currency": 8500, "exchange_rate": 1})
		jv.accounts[1].update({"party_type": "Customer", "party": "_Test Customer USD", "exchange_rate": 85})
		jv.submit()
		actual = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": jv.name, "is_cancelled": 0},
			fields=["account", "transaction_exchange_rate"],
			order_by="account",
		)
		expected = [
			{"account": "_Test Bank - _TC", "transaction_exchange_rate": 85.0},
			{"account": "_Test Receivable USD - _TC", "transaction_exchange_rate": 85.0},
		]
		self.assertEqual(expected, actual)

	def test_select_tds_payable_and_creditors_account_TC_ACC_024(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_records

		create_records("_Test Supplier TDS")

		supplier = frappe.get_doc("Supplier", "_Test Supplier TDS")
		account = frappe.get_doc("Account", "_Test TDS Payable - _TC")

		if supplier and account:
			jv = frappe.new_doc("Journal Entry")
			jv.posting_date = nowdate()
			jv.company = "_Test Company"
			jv.set(
				"accounts",
				[
					{
						"account": account.name,
						"debit_in_account_currency": 0,
						"credit_in_account_currency": 1000,
					},
					{
						"account": "Creditors - _TC",
						"party_type": "Supplier",
						"party": supplier.name,
						"debit_in_account_currency": 1000,
						"credit_in_account_currency": 0,
					},
				],
			)
			jv.save()
			jv.submit()
			self.voucher_no = jv.name

			self.fields = [
				"account",
				"debit_in_account_currency",
				"credit_in_account_currency",
				"cost_center",
			]

			self.expected_gle = [
				{
					"account": "Creditors - _TC",
					"debit_in_account_currency": 1000,
					"credit_in_account_currency": 0,
					"cost_center": "Main - _TC",
				},
				{
					"account": account.name,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": 1000,
					"cost_center": "Main - _TC",
				},
			]

			self.check_gl_entries()

	def test_round_off_entry_TC_ACC_050(self):
		# Set up round-off account and cost center
		frappe.db.set_value("Company", "_Test Company", "round_off_account", "_Test Write Off - _TC")
		frappe.db.set_value("Company", "_Test Company", "round_off_cost_center", "_Test Cost Center - _TC")

		# Create a journal entry
		jv = make_journal_entry(
			"_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC",
			100,
			"_Test Cost Center - _TC",
			submit=False,
		)
		jv.get("accounts")[0].debit = 100.01
		jv.flags.ignore_validate = True
		jv.submit()

		# Fetch round-off GL Entry
		round_off_entry = frappe.db.sql(
			"""select debit, credit, account, cost_center
			from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_no = %s
			and account='_Test Write Off - _TC' and cost_center='_Test Cost Center - _TC'""",
			jv.name,
			as_dict=True,
		)
		self.assertTrue(round_off_entry, "Round-off entry not found.")

		# Validate the round-off amount
		entry = round_off_entry[0]
		self.assertEqual(entry["debit"], 0, "Round-off debit is incorrect.")
		self.assertEqual(entry["credit"], 0.01, "Round-off credit is incorrect.")

		# Validate the debit and credit accounts for the main journal entry
		debit_account = frappe.db.get_value(
			"GL Entry", {"voucher_no": jv.name, "voucher_type": "Journal Entry", "debit": 100.01}, "account"
		)
		credit_account = frappe.db.get_value(
			"GL Entry", {"voucher_no": jv.name, "voucher_type": "Journal Entry", "credit": 100}, "account"
		)

		self.assertEqual(
			debit_account, "_Test Account Cost for Goods Sold - _TC", "Debit account is incorrect."
		)
		self.assertEqual(credit_account, "_Test Bank - _TC", "Credit account is incorrect.")

	def test_debit_note_entry_TC_ACC_052(self):
		# Set up parameters
		party_type = "Customer"
		party = "_Test Customer"
		account1 = "Debtors - _TC"  # Debit Account
		account2 = "Cash - _TC"  # Credit Account
		amount = 1000.0

		# Create the Journal Entry for Debit Note
		jv = make_journal_entry(
			account1=account1,
			account2=account2,
			amount=amount,
			# cost_center=cost_center,
			save=False,
			submit=False,
		)

		# Update party details for GL entries
		for account in jv.accounts:
			if account.account == "Debtors - _TC":
				account.party_type = party_type
				account.party = party
		jv.save()
		jv.submit()

		# Fetch the GL Entries for the created JV
		gl_entries = frappe.db.sql(
			"""SELECT account, debit, credit, party_type, party
				FROM `tabGL Entry`
				WHERE voucher_no = %s AND voucher_type = 'Journal Entry'""",
			jv.name,
			as_dict=True,
		)

		# Assertions
		self.assertEqual(len(gl_entries), 2, "Incorrect number of GL Entries created.")

	def test_contra_entry_TC_ACC_053(self):
		# Set up input parameters
		entry_type = "Contra Entry"
		debit_account = "_Test Bank - _TC"
		credit_account = "_Test Cash - _TC"
		amount = 50000.0

		# Create the Journal Entry using the existing function
		jv = make_journal_entry(
			account1=debit_account,
			account2=credit_account,
			amount=amount,
			save=False,
			submit=False,
		)

		# Set the entry type and save the journal entry
		jv.entry_type = entry_type
		jv.save()
		jv.submit()

		# Fetch GL Entries to validate the transaction
		gl_entries = frappe.db.sql(
			"""SELECT account, debit, credit FROM `tabGL Entry`
				WHERE voucher_type='Journal Entry' AND voucher_no=%s
				ORDER BY account""",
			jv.name,
			as_dict=True,
		)

		# Expected GL entries
		expected_gl_entries = [
			{"account": debit_account, "debit": amount, "credit": 0},
			{"account": credit_account, "debit": 0, "credit": amount},
		]

		# Assertions
		self.assertEqual(len(gl_entries), 2, "Incorrect number of GL entries created.")
		for entry, expected in zip(gl_entries, expected_gl_entries, strict=True):
			self.assertEqual(entry["account"], expected["account"], "Account mismatch in GL Entry.")
			self.assertEqual(entry["debit"], expected["debit"], f"Debit mismatch for {entry['account']}.")
			self.assertEqual(entry["credit"], expected["credit"], f"Credit mismatch for {entry['account']}.")

	def test_payment_of_gst_tds_TC_ACC_054(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import validate_fiscal_year

		# Set up input parameters
		validate_fiscal_year("_Test Company")
		create_custom_test_accounts()
		entry_type = "Journal Entry"
		credit_account = "_Test Bank - _TC"
		amount = 20000.0
		tax_accounts = frappe.get_all(
			"Account",
			filters={
				"company": "_Test Company",
				"account_type": "Tax",
				"parent_account": ["like", "%Assets%"],
			},
			fields=["name"],
		)

		# Identify SGST and CGST accounts based on their name
		debit_account = None
		for account in tax_accounts:
			if "IGST" in account["name"]:
				debit_account = account["name"]

		# Ensure both SGST and CGST accounts are found
		if not debit_account:
			self.fail(f"Could not find IGST account: {tax_accounts}")
		# Create the Journal Entry using the existing function
		jv = make_journal_entry(
			account1=debit_account,
			account2=credit_account,
			amount=amount,
			save=False,
			submit=False,
		)

		# Set the entry type and save the journal entry
		jv.entry_type = entry_type
		jv.save()
		jv.submit()

		# Fetch GL Entries to validate the transaction
		gl_entries = frappe.db.sql(
			"""SELECT account, debit, credit FROM `tabGL Entry`
				WHERE voucher_type='Journal Entry' AND voucher_no=%s
				ORDER BY account""",
			jv.name,
			as_dict=True,
		)

		# Expected GL entries
		expected_gl_entries = [
			{"account": debit_account, "debit": amount, "credit": 0},
			{"account": credit_account, "debit": 0, "credit": amount},
		]

		# Assertions
		self.assertEqual(len(gl_entries), 2, "Incorrect number of GL entries created.")
		for entry, expected in zip(gl_entries, expected_gl_entries, strict=True):
			self.assertEqual(entry["account"], expected["account"], "Account mismatch in GL Entry.")
			self.assertEqual(entry["debit"], expected["debit"], f"Debit mismatch for {entry['account']}.")
			self.assertEqual(entry["credit"], expected["credit"], f"Credit mismatch for {entry['account']}.")

	def test_deferred_expense_entry_TC_ACC_055(self):
		# Set up input parameters
		entry_type = "Deferred Expense"
		debit_account = "_Test Accumulated Depreciations - _TC"
		credit_account = "Creditors - _TC"
		amount = 30000.0

		# Create the Journal Entry using the existing function
		jv = make_journal_entry(
			account1=debit_account,
			account2=credit_account,
			amount=amount,
			save=False,
			submit=False,
		)
		for account in jv.accounts:
			if account.account == "Creditors - _TC":
				account.party_type = "Supplier"
				account.party = "_Test Supplier"
		# Set the entry type and save the journal entry
		jv.entry_type = entry_type
		jv.save().submit()

		# Fetch GL Entries to validate the transaction
		gl_entries = frappe.db.sql(
			"""SELECT account, debit, credit FROM `tabGL Entry`
				WHERE voucher_type='Journal Entry' AND voucher_no=%s
				ORDER BY account""",
			jv.name,
			as_dict=True,
		)
		# Expected GL entries
		expected_gl_entries = [
			{"account": credit_account, "debit": 0, "credit": amount},
			{"account": debit_account, "debit": amount, "credit": 0},
		]

		# Assertions
		self.assertEqual(len(gl_entries), 2, "Incorrect number of GL entries created.")
		for entry, expected in zip(gl_entries, expected_gl_entries, strict=True):
			self.assertEqual(entry["account"], expected["account"], "Account mismatch in GL Entry.")
			self.assertEqual(entry["debit"], expected["debit"], f"Debit mismatch for {entry['account']}.")
			self.assertEqual(entry["credit"], expected["credit"], f"Credit mismatch for {entry['account']}.")

	def test_deferred_expense_entry_TC_ACC_056(self):
		# Set up input parameters
		entry_type = "Deferred Expense"
		debit_account = "Write Off - _TC"
		credit_account = "_Test Accumulated Depreciations - _TC"
		amount = 30000.0

		# Create the Journal Entry using the existing function
		jv = make_journal_entry(
			account1=debit_account,
			account2=credit_account,
			amount=amount,
			save=False,
			submit=False,
		)
		# Set the entry type and save the journal entry
		jv.entry_type = entry_type
		jv.save().submit()

		# Fetch GL Entries to validate the transaction
		gl_entries = frappe.db.sql(
			"""SELECT account, debit, credit FROM `tabGL Entry`
				WHERE voucher_type='Journal Entry' AND voucher_no=%s
				ORDER BY account""",
			jv.name,
			as_dict=True,
		)
		# Expected GL entries
		expected_gl_entries = [
			{"account": debit_account, "debit": amount, "credit": 0},
			{"account": credit_account, "debit": 0, "credit": amount},
		]

		# Assertions
		self.assertEqual(len(gl_entries), 2, "Incorrect number of GL entries created.")
		for entry, expected in zip(gl_entries, expected_gl_entries, strict=True):
			self.assertEqual(entry["account"], expected["account"], "Account mismatch in GL Entry.")
			self.assertEqual(entry["debit"], expected["debit"], f"Debit mismatch for {entry['account']}.")
			self.assertEqual(entry["credit"], expected["credit"], f"Credit mismatch for {entry['account']}.")

	def test_deferred_revenue_entry_TC_ACC_057(self):
		# Set up input parameters
		entry_type = "Deferred Revenue"
		debit_account = "Debtors - _TC"
		credit_account = "Creditors - _TC"
		amount = 30000.0

		# Create the Journal Entry using the existing function
		jv = make_journal_entry(
			account1=debit_account,
			account2=credit_account,
			amount=amount,
			save=False,
			submit=False,
		)
		for account in jv.accounts:
			if account.account == "Creditors - _TC":
				account.party_type = "Supplier"
				account.party = "_Test Supplier"

			elif account.account == "Debtors - _TC":
				account.party_type = "Customer"
				account.party = "_Test Customer"
		# Set the entry type and save the journal entry
		jv.entry_type = entry_type
		jv.save().submit()

		# Fetch GL Entries to validate the transaction
		gl_entries = frappe.db.sql(
			"""SELECT account, debit, credit FROM `tabGL Entry`
				WHERE voucher_type='Journal Entry' AND voucher_no=%s
				ORDER BY account""",
			jv.name,
			as_dict=True,
		)
		# Expected GL entries
		expected_gl_entries = [
			{"account": credit_account, "debit": 0, "credit": amount},
			{"account": debit_account, "debit": amount, "credit": 0},
		]

		# Assertions
		self.assertEqual(len(gl_entries), 2, "Incorrect number of GL entries created.")
		for entry, expected in zip(gl_entries, expected_gl_entries, strict=True):
			self.assertEqual(entry["account"], expected["account"], "Account mismatch in GL Entry.")
			self.assertEqual(entry["debit"], expected["debit"], f"Debit mismatch for {entry['account']}.")
			self.assertEqual(entry["credit"], expected["credit"], f"Credit mismatch for {entry['account']}.")

	def test_deferred_revenue_entry_TC_ACC_058(self):
		# Set up input parameters
		entry_type = "Deferred Revenue"
		debit_account = "Creditors - _TC"
		credit_account = "Sales - _TC"
		amount = 30000.0

		# Create the Journal Entry using the existing function
		jv = make_journal_entry(
			account1=debit_account,
			account2=credit_account,
			amount=amount,
			save=False,
			submit=False,
		)
		for account in jv.accounts:
			if account.account == "Creditors - _TC":
				account.party_type = "Supplier"
				account.party = "_Test Supplier"
		# Set the entry type and save the journal entry
		jv.entry_type = entry_type
		jv.save().submit()

		# Fetch GL Entries to validate the transaction
		gl_entries = frappe.db.sql(
			"""SELECT account, debit, credit FROM `tabGL Entry`
				WHERE voucher_type='Journal Entry' AND voucher_no=%s
				ORDER BY account""",
			jv.name,
			as_dict=True,
		)
		# Expected GL entries
		expected_gl_entries = [
			{"account": debit_account, "debit": amount, "credit": 0},
			{"account": credit_account, "debit": 0, "credit": amount},
		]

		# Assertions
		self.assertEqual(len(gl_entries), 2, "Incorrect number of GL entries created.")
		for entry, expected in zip(gl_entries, expected_gl_entries, strict=True):
			self.assertEqual(entry["account"], expected["account"], "Account mismatch in GL Entry.")
			self.assertEqual(entry["debit"], expected["debit"], f"Debit mismatch for {entry['account']}.")
			self.assertEqual(entry["credit"], expected["credit"], f"Credit mismatch for {entry['account']}.")

	def test_reversal_of_itc_TC_ACC_059(self):
		# Set up input parameters
		entry_type = "Reversal of ITC"
		credit_account = "Creditors - _TC"
		amount_sgst = 5000.0
		amount_cgst = 5000.0
		create_custom_test_accounts()
		# Fetch Tax Accounts dynamically
		tax_accounts = frappe.get_all(
			"Account",
			filters={
				"company": "_Test Company",
				"account_type": "Tax",
				"parent_account": ["like", "%Assets%"],
			},
			fields=["name"],
		)
		# Identify SGST and CGST accounts based on their name
		debit_account_sgst = None
		debit_account_cgst = None

		for account in tax_accounts:
			if "SGST" in account["name"]:
				debit_account_sgst = account["name"]
			elif "CGST" in account["name"]:
				debit_account_cgst = account["name"]

		# Ensure both SGST and CGST accounts are found
		if not debit_account_sgst or not debit_account_cgst:
			self.fail(f"Could not find SGST or CGST accounts. Found: {tax_accounts}")

		# Create the Journal Entry
		jv = frappe.new_doc("Journal Entry")
		jv.posting_date = nowdate()
		jv.company = "_Test Company"
		jv.entry_type = entry_type
		jv.user_remark = "Reversal of ITC Test Case"

		# Add accounts to the Journal Entry
		jv.append(
			"accounts",
			{
				"account": debit_account_sgst,
				"debit_in_account_currency": amount_sgst,
				"credit_in_account_currency": 0,
				"cost_center": "_Test Cost Center - _TC",
			},
		)

		jv.append(
			"accounts",
			{
				"account": debit_account_cgst,
				"debit_in_account_currency": amount_cgst,
				"credit_in_account_currency": 0,
				"cost_center": "_Test Cost Center - _TC",
			},
		)

		jv.append(
			"accounts",
			{
				"account": credit_account,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": amount_sgst + amount_cgst,
				"cost_center": "_Test Cost Center - _TC",
				"party_type": "Supplier",
				"party": "_Test Supplier",
			},
		)

		# Save and submit the Journal Entry
		jv.insert()
		jv.submit()

		# Fetch GL Entries to validate the transaction
		gl_entries = frappe.db.sql(
			"""SELECT account, debit, credit FROM `tabGL Entry`
				WHERE voucher_type='Journal Entry' AND voucher_no=%s
				ORDER BY account""",
			jv.name,
			as_dict=True,
		)

		# Expected GL entries
		expected_gl_entries = [
			{"account": credit_account, "debit": 0, "credit": amount_sgst + amount_cgst},
			{"account": debit_account_cgst, "debit": amount_cgst, "credit": 0},
			{"account": debit_account_sgst, "debit": amount_sgst, "credit": 0},
		]

		# Assertions
		self.assertEqual(len(gl_entries), 3, "Incorrect number of GL entries created.")
		for entry, expected in zip(gl_entries, expected_gl_entries, strict=True):
			self.assertEqual(
				entry["account"], expected["account"], f"Account mismatch in GL Entry: {entry['account']}."
			)
			self.assertEqual(entry["debit"], expected["debit"], f"Debit mismatch for {entry['account']}.")
			self.assertEqual(entry["credit"], expected["credit"], f"Credit mismatch for {entry['account']}.")

	def test_exchange_gain_or_loss_TC_ACC_060(self):
		# Set up input parameters
		entry_type = "Exchange Gain or Loss"
		debit_account = "Exchange Gain/Loss - _TC"
		credit_account = "Debtors - _TC"
		party_type = "Customer"
		party = "_Test Customer"
		new_exchange_rate = 75.0
		amount = 1000.0

		# Create the Journal Entry using the make_journal_entry method
		jv = make_journal_entry(
			account1=debit_account, account2=credit_account, amount=amount, save=False, submit=False
		)

		for account in jv.accounts:
			if account.account == credit_account:
				account.party_type = party_type
				account.party = party
				account.exchange_rate = new_exchange_rate

		# Set the entry type and save the journal entry
		jv.entry_type = entry_type
		jv.save().submit()

		# Fetch GL Entries to validate the transaction
		gl_entries = frappe.db.sql(
			"""SELECT account, debit, credit FROM `tabGL Entry`
				WHERE voucher_type='Journal Entry' AND voucher_no=%s
				ORDER BY account""",
			jv.name,
			as_dict=True,
		)

		# Expected GL entries
		expected_gl_entries = [
			{"account": credit_account, "debit": 0, "credit": amount},
			{"account": debit_account, "debit": amount, "credit": 0},
		]

		# Assertions
		self.assertEqual(len(gl_entries), 2, "Incorrect number of GL entries created.")
		for entry, expected in zip(gl_entries, expected_gl_entries, strict=True):
			self.assertEqual(
				entry["account"], expected["account"], f"Account mismatch in GL Entry: {entry['account']}."
			)
			self.assertEqual(entry["debit"], expected["debit"], f"Debit mismatch for {entry['account']}.")
			self.assertEqual(entry["credit"], expected["credit"], f"Credit mismatch for {entry['account']}.")

	def test_exchange_rate_revaluation_TC_ACC_061(self):
		# Set up input parameters
		entry_type = "Exchange Rate Revaluation"
		debit_account = "Creditors - _TC"
		credit_account = "Exchange Gain/Loss - _TC"
		party_type = "Supplier"
		party = "_Test Supplier"
		new_exchange_rate = 80.0
		amount = 2000.0

		# Create the Journal Entry
		jv = make_journal_entry(
			account1=debit_account, account2=credit_account, amount=amount, save=False, submit=False
		)

		for account in jv.accounts:
			if account.account == debit_account:
				account.party_type = party_type
				account.party = party
				account.exchange_rate = new_exchange_rate

		# Set the entry type and save the journal entry
		jv.entry_type = entry_type
		jv.save().submit()

		# Fetch GL Entries to validate the transaction
		gl_entries = frappe.db.sql(
			"""SELECT account, debit, credit FROM `tabGL Entry`
				WHERE voucher_type='Journal Entry' AND voucher_no=%s
				ORDER BY account""",
			jv.name,
			as_dict=True,
		)

		# Expected GL entries
		expected_gl_entries = [
			{"account": debit_account, "debit": amount, "credit": 0},
			{"account": credit_account, "debit": 0, "credit": amount},
		]

		# Assertions
		self.assertEqual(len(gl_entries), 2, "Incorrect number of GL entries created.")
		for entry, expected in zip(gl_entries, expected_gl_entries, strict=True):
			self.assertEqual(
				entry["account"], expected["account"], f"Account mismatch in GL Entry: {entry['account']}."
			)
			self.assertEqual(entry["debit"], expected["debit"], f"Debit mismatch for {entry['account']}.")
			self.assertEqual(entry["credit"], expected["credit"], f"Credit mismatch for {entry['account']}.")

	def test_create_jv_for_cash_enrty_TC_ACC_082(self):
		jv = make_journal_entry(
			account1="Cash - _TC",
			account2="_Test Payable - _TC",
			amount=1000.0,
			exchange_rate=0,
			save=False,
			submit=False,
		)
		for account in jv.accounts:
			if account.account == "_Test Payable - _TC":
				account.party_type = "Supplier"
				account.party = "_Test Supplier"
		jv.save().submit()
		self.voucher_no = jv.name
		self.fields = [
			"account",
			"account_currency",
			"debit",
			"debit_in_account_currency",
			"credit",
			"credit_in_account_currency",
		]

		self.expected_gle = [
			{
				"account": "Cash - _TC",
				"account_currency": "INR",
				"debit": 1000,
				"debit_in_account_currency": 1000,
				"credit": 0,
				"credit_in_account_currency": 0,
			},
			{
				"account": "_Test Payable - _TC",
				"account_currency": "INR",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 1000,
				"credit_in_account_currency": 1000,
			},
		]
		self.check_gl_entries()

	def test_create_jv_for_bank_enrty_TC_ACC_083(self):
		jv = make_journal_entry(
			account1="_Test Bank - _TC",
			account2="_Test Receivable - _TC",
			amount=1000.0,
			exchange_rate=0,
			save=False,
			submit=False,
		)
		jv.voucher_type = "Bank Entry"
		jv.cheque_no = "112233"
		jv.cheque_date = nowdate()
		for account in jv.accounts:
			if account.account == "_Test Receivable - _TC":
				account.party_type = "Customer"
				account.party = "_Test Customer"
		jv.save().submit()
		self.voucher_no = jv.name
		self.fields = [
			"account",
			"account_currency",
			"debit",
			"debit_in_account_currency",
			"credit",
			"credit_in_account_currency",
		]

		self.expected_gle = [
			{
				"account": "_Test Bank - _TC",
				"account_currency": "INR",
				"debit": 1000,
				"debit_in_account_currency": 1000,
				"credit": 0,
				"credit_in_account_currency": 0,
			},
			{
				"account": "_Test Receivable - _TC",
				"account_currency": "INR",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 1000,
				"credit_in_account_currency": 1000,
			},
		]
		self.check_gl_entries()

	def test_create_jv_with_jv_template_TC_ACC_084(self):
		if not frappe.db.exists("Journal Entry Template", "_Test Template"):
			template = frappe.new_doc("Journal Entry Template")
			template.template_title = "_Test Template"
			template.company = "_Test Company"
			template.naming_series = "ACC-JV-.YYYY.-"
			template.append(
				"accounts",
				{
					"account": "Cash - _TC",
				},
			)
			template.insert()
		template = frappe.get_doc("Journal Entry Template", "_Test Template")
		jv = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": "_Test Company",
				"posting_date": frappe.utils.nowdate(),
				"from_template": template.name,
				"accounts": [
					{
						"account": template.accounts[0].account,
						"account_currency": "INR",
						"debit": 10000,
						"debit_in_account_currency": 10000,
						"credit": 0,
						"credit_in_account_currency": 0,
					}
				],
			}
		).insert()
		jv.append(
			"accounts",
			{
				"account": "_Test Payable - _TC",
				"account_currency": "INR",
				"party_type": "Supplier",
				"party": "_Test Supplier",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 10000,
				"credit_in_account_currency": 10000,
			},
		)
		jv.save().submit()

		self.voucher_no = jv.name
		self.fields = [
			"account",
			"account_currency",
			"debit",
			"debit_in_account_currency",
			"credit",
			"credit_in_account_currency",
		]

		self.expected_gle = [
			{
				"account": "Cash - _TC",
				"account_currency": "INR",
				"debit": 10000,
				"debit_in_account_currency": 10000,
				"credit": 0,
				"credit_in_account_currency": 0,
			},
			{
				"account": "_Test Payable - _TC",
				"account_currency": "INR",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 10000,
				"credit_in_account_currency": 10000,
			},
		]

		self.check_gl_entries()

	def test_opening_entry_TC_ACC_116(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_records

		create_records("_Test Supplier")
		jv = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Opening Entry",
				"company": "_Test Company",
				"posting_date": frappe.utils.nowdate(),
				"accounts": [
					{
						"account": "_Test Payable - _TC",
						"party_type": "Supplier",
						"party": "_Test Supplier",
						"debit_in_account_currency": 1000,
					},
					{
						"account": "_Test Creditors - _TC",
						"credit_in_account_currency": 1000,
						"party_type": "Supplier",
						"party": "_Test Supplier",
					},
					{
						"account": "Debtors - _TC",
						"party_type": "Customer",
						"party": "_Test Customer",
						"debit_in_account_currency": 1000,
					},
					{
						"account": "_Test Receivable - _TC",
						"party_type": "Customer",
						"party": "_Test Customer",
						"credit_in_account_currency": 1000,
					},
					{"account": "Cash - _TC", "debit_in_account_currency": 2000},
					{"account": "Temporary Opening - _TC", "credit_in_account_currency": 2000},
				],
			}
		).insert()
		jv.submit()
		self.voucher_no = jv.name
		self.fields = [
			"account",
			"account_currency",
			"debit",
			"debit_in_account_currency",
			"credit",
			"credit_in_account_currency",
		]

		self.expected_gle = [
			{
				"account": "Cash - _TC",
				"account_currency": "INR",
				"debit": 2000.0,
				"debit_in_account_currency": 2000.0,
				"credit": 0.0,
				"credit_in_account_currency": 0.0,
			},
			{
				"account": "Debtors - _TC",
				"account_currency": "INR",
				"debit": 1000.0,
				"debit_in_account_currency": 1000.0,
				"credit": 0.0,
				"credit_in_account_currency": 0.0,
			},
			{
				"account": "Temporary Opening - _TC",
				"account_currency": "INR",
				"debit": 0.0,
				"debit_in_account_currency": 0.0,
				"credit": 2000.0,
				"credit_in_account_currency": 2000.0,
			},
			{
				"account": "_Test Creditors - _TC",
				"account_currency": "INR",
				"debit": 0.0,
				"debit_in_account_currency": 0.0,
				"credit": 1000.0,
				"credit_in_account_currency": 1000.0,
			},
			{
				"account": "_Test Payable - _TC",
				"account_currency": "INR",
				"debit": 1000.0,
				"debit_in_account_currency": 1000.0,
				"credit": 0.0,
				"credit_in_account_currency": 0.0,
			},
			{
				"account": "_Test Receivable - _TC",
				"account_currency": "INR",
				"debit": 0.0,
				"debit_in_account_currency": 0.0,
				"credit": 1000.0,
				"credit_in_account_currency": 1000.0,
			},
		]

		self.check_gl_entries()

	def test_reverse_journal_entry_TC_ACC_107(self):
		from erpnext.accounts.doctype.journal_entry.journal_entry import make_reverse_journal_entry

		jv = make_journal_entry(
			account1="Cost of Goods Sold - _TC",
			account2="Cash - _TC",
			amount=10000.0,
			save=False,
			submit=False,
		)
		jv.voucher_type = "Journal Entry"
		jv.save().submit()
		self.voucher_no = jv.name
		self.fields = [
			"account",
			"account_currency",
			"debit",
			"debit_in_account_currency",
			"credit",
			"credit_in_account_currency",
		]
		self.expected_gle = [
			{
				"account": "Cash - _TC",
				"account_currency": "INR",
				"debit": 0.0,
				"debit_in_account_currency": 0.0,
				"credit": 10000.0,
				"credit_in_account_currency": 10000.0,
			},
			{
				"account": "Cost of Goods Sold - _TC",
				"account_currency": "INR",
				"debit": 10000.0,
				"debit_in_account_currency": 10000.0,
				"credit": 0.0,
				"credit_in_account_currency": 0.0,
			},
		]

		self.check_gl_entries()

		_jv = make_reverse_journal_entry(jv.name)
		_jv.posting_date = nowdate()
		_jv.save().submit()
		self.voucher_no = _jv.name
		self.fields = [
			"account",
			"account_currency",
			"debit",
			"debit_in_account_currency",
			"credit",
			"credit_in_account_currency",
		]
		self.expected_gle = [
			{
				"account": "Cash - _TC",
				"account_currency": "INR",
				"debit": 10000.0,
				"debit_in_account_currency": 10000.0,
				"credit": 0.0,
				"credit_in_account_currency": 0.0,
			},
			{
				"account": "Cost of Goods Sold - _TC",
				"account_currency": "INR",
				"debit": 0.0,
				"debit_in_account_currency": 0.0,
				"credit": 10000.0,
				"credit_in_account_currency": 10000.0,
			},
		]

		self.check_gl_entries()

	def test_make_differnce_function_TC_ACC_108(self):
		jv = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"company": "_Test Company",
				"posting_date": nowdate(),
				"accounts": [
					{
						"account": "Cash - _TC",
						"cost_center": "Main - _TC",
						"debit_in_account_currency": 1000,
						"credit_in_account_currency": 0,
					},
				],
			}
		).insert()
		jv.get_balance()
		jv.accounts[1].account = "Cost of Goods Sold - _TC"
		jv.accounts[1].cost_center = "Main - _TC"
		jv.save()
		self.assertEqual(jv.accounts[0].debit_in_account_currency, jv.accounts[1].credit_in_account_currency)

	def test_apply_tax_withholding_TC_ACC_543(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		create_company(company_name="_Test Company")
		company = "_Test Company"
		abbr = frappe.get_cached_value("Company", company, "abbr")

		withholding_account = get_or_create_account(
			"TDS Payable", company, f"Current Liabilities - {abbr}", "Tax", "Liability"
		)
		creditor_account = get_or_create_account(
			"Creditors", company, f"Current Liabilities - {abbr}", "Payable", "Liability"
		)
		bank_account = get_or_create_account("Bank", company, f"Current Assets - {abbr}", "Bank", "Asset")
		get_or_create_supplier("_Test Supplier")
		get_or_create_tds_category("_Test TDS Category", company, withholding_account)

		je = make_journal_entry(account1=creditor_account, account2=bank_account, amount=-1000.0, save=False)
		je.voucher_type = "Credit Note"
		je.company = company
		je.apply_tds = 1
		je.tax_withholding_category = "_Test TDS Category"
		je.accounts[0].party_type = "Supplier"
		je.accounts[0].party = "_Test Supplier"
		je.insert(ignore_permissions=True)
		je.apply_tax_withholding()

		creditor_row = next(d for d in je.accounts if d.account == creditor_account)
		self.assertEqual(creditor_row.credit_in_account_currency, 1000.0)

	def test_get_outstanding_invoices_TC_ACC_544(self):
		from frappe import _dict

		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company,
			create_sales_invoice,
		)

		create_company(company_name="_Test Company")
		company = "_Test Company"
		abbr = frappe.get_cached_value("Company", company, "abbr")
		customer = get_or_create_customer("_Test Customer JE")

		si = create_sales_invoice(
			company=company,
			customer=customer,
			debit_to=f"Debtors - {abbr}",
			item="_Test Item",
			qty=1,
			rate=100.0,
		)

		je = make_journal_entry(
			account1=f"Debtors - {abbr}", account2=f"Creditors - {abbr}", amount=0, save=False
		)
		je.voucher_type = "Credit Note"
		je.write_off_based_on = "Accounts Receivable"
		je.get_values = lambda: [
			_dict(
				{
					"name": si.name,
					"account": si.debit_to,
					"party": si.customer,
					"outstanding_amount": si.outstanding_amount,
				}
			)
		]

		je.get_outstanding_invoices()
		self.assertEqual(len(je.accounts), 2)
		first, bal = je.accounts[0], je.accounts[1]
		self.assertEqual(first.party_type, "Customer")
		self.assertEqual(first.account, si.debit_to)
		self.assertEqual(first.reference_type, "Sales Invoice")
		self.assertEqual(first.reference_name, si.name)
		self.assertEqual(first.credit_in_account_currency, 100.0)
		self.assertEqual(bal.debit_in_account_currency, 100.0)

	def test_get_average_exchange_rate_TC_ACC_545(self):
		from erpnext.accounts.doctype.journal_entry.journal_entry import get_average_exchange_rate
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		create_company(company_name="_Test Company")
		company = "_Test Company"
		abbr = frappe.get_cached_value("Company", company, "abbr")

		bank_account = get_or_create_account("Bank", company, f"Current Assets - {abbr}", "Bank", "Asset")
		expense_account = get_or_create_account(
			"Round Off", company, f"Expenses - {abbr}", "Expense Account", "Expense"
		)

		je = make_journal_entry(
			account1=bank_account,
			account2=expense_account,
			amount=200.0,
			exchange_rate=2.0,
			save=False,
			submit=False,
		)
		je.accounts[0].exchange_rate = 2.0
		je.accounts[0].debit_in_account_currency = 200.0
		je.accounts[0].debit = 400.0
		je.accounts[1].credit_in_account_currency = 200.0
		je.accounts[1].credit = 400.0
		je.insert(ignore_permissions=True)
		je.submit()

		rate = get_average_exchange_rate(bank_account)
		self.assertEqual(rate, 1.0)

	def test_make_inter_company_journal_entry_TC_ACC_546(self):
		from erpnext.accounts.doctype.journal_entry.journal_entry import make_inter_company_journal_entry
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		create_company(company_name="_Test Company")
		company1 = "_Test Company"
		create_company(company_name="_Test Company")
		company2 = "_Test Company with perpetual inventory"
		abbr1 = frappe.get_cached_value("Company", company1, "abbr")
		abbr2 = frappe.get_cached_value("Company", company2, "abbr")

		bank1 = get_or_create_account("Bank", company1, f"Current Assets - {abbr1}", "Bank", "Asset")
		bank2 = get_or_create_account("Bank", company2, f"Current Assets - {abbr2}", "Bank", "Asset")

		je1 = make_journal_entry(account1=bank1, account2=bank1, amount=100, save=False, submit=False)
		je1.company = company1
		je1.voucher_type = "Inter Company Journal Entry"
		je1.insert()
		je1.submit()

		je2_dict = make_inter_company_journal_entry(je1.name, "Inter Company Journal Entry", company2)
		je2 = frappe.get_doc(je2_dict)

		je2.accounts = []
		je2.append("accounts", {"account": bank2, "credit_in_account_currency": 200})
		je2.append("accounts", {"account": bank2, "debit_in_account_currency": 100})

		with self.assertRaises(frappe.ValidationError):
			je2.validate_inter_company_accounts()

	def test_validate_orders_TC_ACC_547(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		create_company(company_name="_Test Company")
		company = "_Test Company"
		abbr = frappe.get_cached_value("Company", company, "abbr")

		def setup_je(ref_so, total):
			je = frappe.get_doc(
				{
					"doctype": "Journal Entry",
					"company": company,
					"voucher_type": "Journal Entry",
					"posting_date": nowdate(),
				}
			)
			je.reference_totals = {ref_so.name: total}
			je.reference_types = {ref_so.name: "Sales Order"}
			je.reference_accounts = {ref_so.name: f"Debtors - {abbr}"}
			return je

		so1 = make_sales_order(company=company, customer="_Test Customer", rate=100, do_not_submit=True)
		with self.assertRaises(frappe.ValidationError):
			setup_je(so1, total=0).validate_orders()

		so2 = make_sales_order(company=company, customer="_Test Customer", rate=200)
		so2.db_set("per_billed", 100)
		with self.assertRaises(frappe.ValidationError):
			setup_je(so2, total=0).validate_orders()

		so3 = make_sales_order(company=company, customer="_Test Customer", rate=300)
		so3.db_set("status", "Closed")
		with self.assertRaises(frappe.ValidationError):
			setup_je(so3, total=0).validate_orders()

	def test_validate_inter_company_accounts_TC_ACC_548(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		create_company(company_name="_Test Company")
		company = "_Test Company"
		abbr = frappe.get_cached_value("Company", company, "abbr")
		account1 = get_or_create_account("Bank", company, f"Current Assets - {abbr}", "Bank", "Asset")
		account2 = get_or_create_account(
			"Round Off", company, f"Expenses - {abbr}", "Expense Account", "Expense"
		)

		je1 = make_journal_entry(account1=account1, account2=account2, amount=500, save=True, submit=True)
		je2 = make_journal_entry(account1=account1, account2=account2, amount=300, save=False, submit=False)
		je2.voucher_type = "Inter Company Journal Entry"
		je2.inter_company_journal_entry_reference = je1.name

		with self.assertRaises(frappe.ValidationError):
			je2.validate_inter_company_accounts()

	def test_update_invoice_discounting_else_branch_TC_ACC_551(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		create_company(company_name="_Test Company")
		company = "_Test Company"
		abbr = frappe.get_cached_value("Company", company, "abbr")

		short_term_loan_acc = get_or_create_account(
			"Short Term Loan", company, f"Current Liabilities - {abbr}", "Bank", "Liability"
		)
		bank_acc = get_or_create_account("Bank", company, f"Current Assets - {abbr}", "Bank", "Asset")
		bank_charges_acc = get_or_create_account(
			"Bank Charges", company, f"Indirect Expenses - {abbr}", "Expense Account", "Expense"
		)

		inv_disc = frappe.get_doc(
			{
				"doctype": "Invoice Discounting",
				"customer": "_Test Customer",
				"company": company,
				"posting_date": frappe.utils.nowdate(),
				"status": "Disbursed",
				"invoice_discounting_amount": 1000,
				"short_term_loan": short_term_loan_acc,
				"bank_account": bank_acc,
				"bank_charges_account": bank_charges_acc,
				"accounts_receivable_credit": f"Debtors - {abbr}",
				"accounts_receivable_discounted": f"Debtors - {abbr}",
				"accounts_receivable_unpaid": f"Debtors - {abbr}",
				"invoices": [
					{
						"sales_invoice": frappe.get_all(
							"Sales Invoice", filters={"company": company}, pluck="name", limit=1
						)[0]
						if frappe.db.exists("Sales Invoice", {"company": company})
						else None,
						"amount": 1000,
					}
				],
			}
		).insert(ignore_permissions=True)

		je1 = make_journal_entry(
			account1=inv_disc.short_term_loan, account2=bank_acc, amount=1000, save=True, submit=False
		)
		je1.accounts[0].reference_type = "Invoice Discounting"
		je1.accounts[0].reference_name = inv_disc.name
		je1.save()
		with self.assertRaises(frappe.ValidationError):
			je1.update_invoice_discounting()

		je2 = make_journal_entry(
			account1=bank_acc, account2=inv_disc.short_term_loan, amount=1000, save=True, submit=False
		)
		je2.accounts[1].reference_type = "Invoice Discounting"
		je2.accounts[1].reference_name = inv_disc.name
		je2.save()
		with self.assertRaises(frappe.ValidationError):
			je2.update_invoice_discounting()

	def test_get_outstanding_invoices_accounts_payable_TC_ACC_552(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		create_company(company_name="_Test Company")
		company = "_Test Company"
		abbr = frappe.get_cached_value("Company", company, "abbr")

		supplier_name = get_or_create_supplier("_Test Supplier Payable")
		warehouse_name = get_or_create_warehouse("_Test Warehouse 1 - _TC", company)
		bank_account_name = get_or_create_account("Bank", company, f"Cash and Bank - {abbr}", "Bank", "Asset")
		expense_account_name = get_or_create_account(
			"Cost of Goods Sold", company, f"Direct Expenses - {abbr}", "Expense Account", "Expense"
		)

		pi = make_purchase_invoice(
			company=company,
			supplier=supplier_name,
			rate=100,
			qty=1,
			warehouse=warehouse_name,
			uom="Nos",
			expense_account=expense_account_name,
			do_not_submit=False,
		)

		je = make_journal_entry(
			account1=pi.credit_to, account2=bank_account_name, amount=pi.grand_total, save=False
		)
		je.company = company
		je.voucher_type = "Write Off Entry"
		je.write_off_based_on = "Accounts Payable"

		je.get_values = lambda: [
			frappe._dict(
				{
					"outstanding_amount": pi.outstanding_amount,
					"account": pi.credit_to,
					"party": pi.supplier,
					"name": pi.name,
				}
			)
		]

		je.get_outstanding_invoices()
		jd1, jd2 = je.accounts[0], je.accounts[1]

		self.assertEqual(jd1.party_type, "Supplier")
		self.assertEqual(jd1.reference_type, "Purchase Invoice")
		self.assertEqual(jd1.reference_name, pi.name)
		self.assertEqual(jd1.debit_in_account_currency, pi.outstanding_amount)
		self.assertEqual(jd2.credit_in_account_currency, pi.outstanding_amount)

	def test_validate_cheque_info_errors_TC_ACC_553(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		create_company(company_name="_Test Company")
		company = "_Test Company"
		abbr = frappe.get_cached_value("Company", company, "abbr")

		bank_account = get_or_create_account("Bank", company, f"Current Assets - {abbr}", "Bank", "Asset")
		expense_account = get_or_create_account(
			"Round Off", company, f"Expenses - {abbr}", "Expense Account", "Expense"
		)

		je1 = make_journal_entry(
			account1=bank_account,
			account2=expense_account,
			amount=200.0,
			exchange_rate=2.0,
			save=False,
			submit=False,
		)
		je1.company = company
		je1.voucher_type = "Bank Entry"
		je1.insert()

		with self.assertRaises(frappe.ValidationError):
			je1.validate_cheque_info()

		je2 = make_journal_entry(
			account1=bank_account,
			account2=expense_account,
			amount=200.0,
			exchange_rate=2.0,
			save=False,
			submit=False,
		)
		je2.company = company
		je2.cheque_date = nowdate()
		je2.insert()

		with self.assertRaises(frappe.ValidationError):
			je2.validate_cheque_info()

	def test_get_values_TC_ACC_554(self):
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		create_company(company_name="_Test Company")
		company = "_Test Company"
		abbr = frappe.get_cached_value("Company", company, "abbr")

		supplier_name = get_or_create_supplier("_Test Supplier Values")
		customer_name = get_or_create_customer("_Test Customer Values")
		warehouse_name = get_or_create_warehouse("_Test Warehouse Values - _TC", company)
		expense_account_name = get_or_create_account(
			"Cost of Goods Sold", company, f"Direct Expenses - {abbr}", "Expense Account", "Expense"
		)

		pi = make_purchase_invoice(
			company=company,
			supplier=supplier_name,
			rate=100,
			qty=1,
			warehouse=warehouse_name,
			uom="Nos",
			expense_account=expense_account_name,
			do_not_submit=False,
		)

		si = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": customer_name,
				"company": company,
				"due_date": nowdate(),
				"debit_to": f"Debtors - {abbr}",
				"currency": "INR",
				"items": [{"item_code": "_Test Item", "qty": 1, "rate": 100}],
			}
		)
		si.insert(ignore_permissions=True)
		si.submit()

		je1 = make_journal_entry(
			account1=pi.credit_to, account2=f"Cash - {abbr}", amount=pi.grand_total, save=False
		)
		je1.company = company
		je1.voucher_type = "Write Off Entry"
		je1.write_off_based_on = "Accounts Payable"
		je1.write_off_amount = 0

		values1 = je1.get_values()
		self.assertTrue(any(v["party"] == pi.supplier for v in values1))

		je2 = make_journal_entry(
			account1=si.debit_to, account2=f"Cash - {abbr}", amount=si.grand_total, save=False
		)
		je2.company = company
		je2.voucher_type = "Write Off Entry"
		je2.write_off_based_on = "Accounts Receivable"
		je2.write_off_amount = 0

		values2 = je2.get_values()
		self.assertTrue(any(v["party"] == si.customer for v in values2))

	def test_validate_credit_debit_note_TC_ACC_555(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company
		from erpnext.stock.doctype.item.test_item import create_item
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		create_company(company_name="_Test Company")
		company = "_Test Company"
		item = create_item(item_code="_Test Item SE")
		item.is_stock_item = 1
		item.save()
		get_or_create_supplier("_Test Supplier")
		get_or_create_customer("_Test Customer")

		se1 = make_stock_entry(
			item_code=item.name,
			target="_Test Warehouse - _TC",
			qty=1,
			basic_rate=100,
			company=company,
			do_not_submit=True,
		)
		se1.save()

		je1 = make_journal_entry(
			account1="Debtors - _TC", account2="Creditors - _TC", amount=100, save=False, submit=False
		)
		je1.company = company
		je1.voucher_type = "Credit Note"
		je1.stock_entry = se1.name

		with self.assertRaises(frappe.ValidationError):
			je1.validate_credit_debit_note()

		se2 = make_stock_entry(
			item_code=item.name,
			target="_Test Warehouse - _TC",
			qty=1,
			basic_rate=100,
			company=company,
			do_not_submit=False,
		)
		se2.submit()

		je2a = make_journal_entry(
			account1="Debtors - _TC", account2="Creditors - _TC", amount=100, save=False
		)
		je2a.company = company
		je2a.voucher_type = "Credit Note"
		je2a.stock_entry = se2.name
		je2a.accounts[0].party_type = "Customer"
		je2a.accounts[0].party = "_Test Customer"
		je2a.accounts[1].party_type = "Supplier"
		je2a.accounts[1].party = "_Test Supplier"
		je2a.save()
		je2a.submit()

		je2b = make_journal_entry(
			account1="Debtors - _TC", account2="Creditors - _TC", amount=50, save=False, submit=False
		)
		je2b.company = company
		je2b.voucher_type = "Debit Note"
		je2b.stock_entry = se2.name

		je2b.validate_credit_debit_note()

	def test_get_outstanding_sales_and_purchase_TC_ACC_556(self):
		from erpnext.accounts.doctype.journal_entry.journal_entry import get_outstanding
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company,
			create_sales_invoice,
		)

		create_company(company_name="_Test Company")
		company = "_Test Company"
		abbr = frappe.get_cached_value("Company", company, "abbr")

		customer = get_or_create_customer("_Test Customer OUT")
		si = create_sales_invoice(
			company=company,
			customer=customer,
			debit_to=f"Debtors - {abbr}",
			item="_Test Item",
			qty=1,
			rate=150.0,
		)
		args = {
			"doctype": "Sales Invoice",
			"docname": si.name,
			"account": si.debit_to,
			"company": company,
			"account_currency": "INR",
		}
		result = get_outstanding(args)

		self.assertIn("credit_in_account_currency", result)
		self.assertEqual(result["credit_in_account_currency"], 150.0)
		self.assertEqual(result["party_type"], "Customer")
		self.assertEqual(result["party"], si.customer)

		supplier = get_or_create_supplier("_Test Supplier OUT")
		pi = make_purchase_invoice(
			company=company,
			supplier=supplier,
			rate=200,
			qty=1,
			warehouse=get_or_create_warehouse("_Test Warehouse OUT - _TC", company),
			uom="Nos",
			expense_account=get_or_create_account(
				"COGS OUT", company, f"Direct Expenses - {abbr}", "Expense Account", "Expense"
			),
			do_not_submit=False,
		)
		args = {
			"doctype": "Purchase Invoice",
			"docname": pi.name,
			"account": pi.credit_to,
			"company": company,
			"account_currency": "INR",
		}
		result = get_outstanding(args)

		self.assertIn("debit_in_account_currency", result)
		self.assertEqual(result["debit_in_account_currency"], 200.0)
		self.assertEqual(result["party_type"], "Supplier")
		self.assertEqual(result["party"], pi.supplier)

	def test_get_party_account_and_currency_TC_ACC_557(self):
		from erpnext.accounts.doctype.journal_entry.journal_entry import get_party_account_and_currency
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		company = "_Test Company"
		create_company(company_name=company)

		customer = get_or_create_customer("_Test Customer JE")
		supplier = get_or_create_supplier("_Test Supplier JE")

		receivable_account = get_or_create_account(
			"Debtors - TC1", company, "Accounts Receivable - _TC", "Receivable", "Asset"
		)
		payable_account = get_or_create_account(
			"Creditors - TC1", company, "Accounts Payable - _TC", "Payable", "Liability"
		)

		customer_doc = frappe.get_doc("Customer", customer)
		if not any(d.company == company for d in customer_doc.get("accounts")):
			customer_doc.append("accounts", {"company": company, "account": receivable_account})
			customer_doc.save()

		supplier_doc = frappe.get_doc("Supplier", supplier)
		if not any(d.company == company for d in supplier_doc.get("accounts")):
			supplier_doc.append("accounts", {"company": company, "account": payable_account})
			supplier_doc.save()

		result = get_party_account_and_currency(company, "Customer", customer)
		self.assertEqual(result["account"], receivable_account)
		self.assertIsNotNone(result["account_currency"])

		result = get_party_account_and_currency(company, "Supplier", supplier)
		self.assertEqual(result["account"], payable_account)
		self.assertIsNotNone(result["account_currency"])

	def test_get_payment_entry_against_order_TC_ACC_558(self):
		from erpnext.accounts.doctype.journal_entry.journal_entry import get_payment_entry_against_order
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company
		from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order

		company = "_Test Company"
		create_company(company_name=company)
		abbr = frappe.get_cached_value("Company", company, "abbr")

		customer = get_or_create_customer("_Test Customer PE")
		receivable_account = get_or_create_account(
			"Debtors - PE1", company, f"Accounts Receivable - {abbr}", "Receivable", "Asset"
		)

		cust_doc = frappe.get_doc("Customer", customer)
		if not any(d.company == company for d in cust_doc.get("accounts")):
			cust_doc.append("accounts", {"company": company, "account": receivable_account})
			cust_doc.save()

		so = make_sales_order(customer=customer, company=company, item="_Test Item", qty=1, rate=100)
		so.submit()
		so.per_billed = 0
		so.save()

		pe_doc = get_payment_entry_against_order("Sales Order", so.name)

		accounts = pe_doc.accounts
		self.assertTrue(any(d.party == customer and d.party_type == "Customer" for d in accounts))
		self.assertTrue(any("Debtors" in d.account for d in accounts))
		self.assertTrue(
			any(d.debit_in_account_currency > 0 or d.credit_in_account_currency > 0 for d in accounts)
		)

		self.assertEqual(pe_doc.accounts[0].is_advance, "Yes")

	def test_validate_party_exceptions_TC_ACC_559(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		company = "_Test Company"
		create_company(company_name=company)
		abbr = frappe.get_cached_value("Company", company, "abbr")

		if not frappe.db.exists("Account", f"Accounts Receivable - {abbr}"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Accounts Receivable",
					"parent_account": f"Debtors - {abbr}",
					"company": company,
					"is_group": 1,
					"root_type": "Asset",
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Account", f"Cash and Bank - {abbr}"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Cash and Bank",
					"parent_account": f"Application of Funds (Assets) - {abbr}",
					"company": company,
					"is_group": 1,
					"root_type": "Asset",
				}
			).insert(ignore_permissions=True)

		receivable_account = get_or_create_account(
			"Debtors - VP1", company, f"Accounts Receivable - {abbr}", "Receivable", "Asset"
		)
		bank_account = get_or_create_account(
			"Bank - VP1", company, f"Cash and Bank - {abbr}", "Bank", "Asset"
		)

		je1 = make_journal_entry(account1=receivable_account, account2=bank_account, amount=100, save=False)
		for d in je1.accounts:
			d.party_type = None
			d.party = None

		with self.assertRaises(frappe.ValidationError) as cm1:
			je1.validate_party()
		self.assertIn("Party Type and Party is required", str(cm1.exception))

		supplier = get_or_create_supplier("_Test Supplier VP")

		je2 = make_journal_entry(account1=receivable_account, account2=bank_account, amount=200, save=False)
		je2.accounts[0].party_type = "Supplier"
		je2.accounts[0].party = supplier

		with self.assertRaises(frappe.ValidationError) as cm2:
			je2.validate_party()
		self.assertIn("have different account types", str(cm2.exception))

	def test_validate_entries_for_advance_exceptions_TC_ACC_560(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		company = "_Test Company"
		create_company(company_name=company)
		abbr = frappe.get_cached_value("Company", company, "abbr")

		ar_account = f"Accounts Receivable - {abbr}"
		cr_account = f"Creditors - {abbr}"

		# Backup current state so we can restore later
		ar_was_group = (
			frappe.db.get_value("Account", ar_account, "is_group")
			if frappe.db.exists("Account", ar_account)
			else None
		)
		cr_was_group = (
			frappe.db.get_value("Account", cr_account, "is_group")
			if frappe.db.exists("Account", cr_account)
			else None
		)

		try:
			if not frappe.db.exists("Account", ar_account):
				frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": "Accounts Receivable",
						"parent_account": f"Debtors - {abbr}",
						"company": company,
						"is_group": 1,
						"root_type": "Asset",
					}
				).insert(ignore_permissions=True)
			else:
				frappe.db.set_value("Account", ar_account, "is_group", 1)

			if not frappe.db.exists("Account", cr_account):
				frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": "Creditors",
						"parent_account": f"Current Liabilities - {abbr}",
						"company": company,
						"is_group": 1,
						"root_type": "Liability",
					}
				).insert(ignore_permissions=True)
			else:
				frappe.db.set_value("Account", cr_account, "is_group", 1)

			receivable_account = get_or_create_account(
				"Debtors - ADV", company, ar_account, "Receivable", "Asset"
			)

			payable_account = get_or_create_account(
				"Creditors - ADV", company, cr_account, "Payable", "Liability"
			)

			je1 = make_journal_entry(
				account1=receivable_account, account2=payable_account, amount=300, save=False
			)
			je1.accounts[0].party_type = "Customer"
			je1.accounts[0].credit = 300
			je1.accounts[0].is_advance = ""
			je1.accounts[0].reference_type = "Sales Order"

			with self.assertRaises(frappe.ValidationError) as cm1:
				je1.validate_entries_for_advance()
			self.assertIn(
				"Payment against Sales/Purchase Order should always be marked as advance", str(cm1.exception)
			)

			je2 = make_journal_entry(
				account1=receivable_account, account2=payable_account, amount=400, save=False
			)
			je2.accounts[0].party_type = "Customer"
			je2.accounts[0].is_advance = "Yes"
			je2.accounts[0].debit = 400
			je2.accounts[0].credit = 0

			with self.assertRaises(frappe.ValidationError) as cm2:
				je2.validate_entries_for_advance()

			self.assertIn("Advance against Customer must be credit", str(cm2.exception))
			je3 = make_journal_entry(
				account1=receivable_account, account2=payable_account, amount=500, save=False
			)
			je3.accounts[0].party_type = "Supplier"
			je3.accounts[0].is_advance = "Yes"
			je3.accounts[0].credit = 500
			je3.accounts[0].debit = 0

			with self.assertRaises(frappe.ValidationError) as cm3:
				je3.validate_entries_for_advance()
			self.assertIn("Advance against Supplier must be debit", str(cm3.exception))

		finally:
			# Always restore accounts to their original is_group state
			if ar_was_group is not None:
				frappe.db.set_value("Account", ar_account, "is_group", ar_was_group)
			if cr_was_group is not None:
				frappe.db.set_value("Account", cr_account, "is_group", cr_was_group)

	def test_validate_stock_accounts_exceptions_TC_ACC_561(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		company = "_Test Company"
		create_company(company_name=company)
		abbr = frappe.get_cached_value("Company", company, "abbr")

		if not frappe.db.exists("Account", f"Stock In Hand - {abbr}"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Stock In Hand",
					"parent_account": f"Current Assets - {abbr}",
					"company": company,
					"is_group": 0,
					"root_type": "Asset",
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Account", f"Cash - {abbr}"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Cash",
					"parent_account": f"Current Assets - {abbr}",
					"company": company,
					"is_group": 0,
					"root_type": "Asset",
				}
			).insert(ignore_permissions=True)

		je = make_journal_entry(
			account1=f"Stock In Hand - {abbr}", account2=f"Cash - {abbr}", amount=100, save=True
		)
		with self.assertRaises(frappe.ValidationError) as cm:
			je.validate_stock_accounts()

		self.assertIn("can only be updated via Stock Transactions", str(cm.exception))

	def test_validate_against_jv_exceptions_TC_ACC_562(self):
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		company = "_Test Company"
		create_company(company_name=company)
		abbr = frappe.get_cached_value("Company", company, "abbr")
		get_or_create_supplier("_Test Supplier")
		get_or_create_customer("_Test Customer")

		debtors_account = f"Debtors - {abbr}"
		liabilities_account = f"Current Liabilities - {abbr}"

		try:
			if not frappe.db.exists("Account", debtors_account):
				frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": "Debtors",
						"parent_account": f"Accounts Receivable - {abbr}",
						"company": company,
						"is_group": 1,
						"root_type": "Asset",
					}
				).insert(ignore_permissions=True)
			else:
				frappe.db.set_value("Account", debtors_account, "is_group", 1)

			if not frappe.db.exists("Account", liabilities_account):
				frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": "Current Liabilities",
						"parent_account": f"Liabilities - {abbr}",
						"company": company,
						"is_group": 1,
						"root_type": "Liability",
					}
				).insert(ignore_permissions=True)
			else:
				frappe.db.set_value("Account", liabilities_account, "is_group", 1)

			asset_account = get_or_create_account(
				"Debtors - JV", company, debtors_account, "Receivable", "Asset"
			)
			liability_account = get_or_create_account(
				"Creditors - JV", company, liabilities_account, "Payable", "Liability"
			)

			je1 = make_journal_entry(
				account1=asset_account, account2=liability_account, amount=200, save=False
			)
			je1.accounts[0].reference_type = "Journal Entry"
			je1.accounts[0].debit = 200
			je1.accounts[0].credit = 0
			with self.assertRaises(frappe.ValidationError) as cm1:
				je1.validate_against_jv()
			self.assertIn(
				"you can select reference document only if account gets credited", str(cm1.exception)
			)

			je2 = make_journal_entry(
				account1=liability_account, account2=asset_account, amount=300, save=False
			)
			je2.accounts[0].reference_type = "Journal Entry"
			je2.accounts[0].credit = 300
			je2.accounts[0].debit = 0
			with self.assertRaises(frappe.ValidationError) as cm2:
				je2.validate_against_jv()
			self.assertIn(
				"you can select reference document only if account gets debited", str(cm2.exception)
			)

			je3 = make_journal_entry(
				account1=asset_account, account2=liability_account, amount=400, save=False
			)
			je3.accounts[0].party_type = "Customer"
			je3.accounts[0].party = "_Test Customer"
			je3.accounts[0].reference_type = "Journal Entry"
			je3.accounts[0].reference_name = je3.name
			with self.assertRaises(frappe.ValidationError) as cm3:
				je3.validate_against_jv()
			self.assertIn(
				"You can not enter current voucher in 'Against Journal Entry' column", str(cm3.exception)
			)

			ref_je = make_journal_entry(
				account1=asset_account, account2=liability_account, amount=500, save=False
			)
			ref_je.accounts[0].party_type = "Customer"
			ref_je.accounts[0].party = "_Test Customer"
			ref_je.accounts[1].party_type = "Supplier"
			ref_je.accounts[1].party = "_Test Supplier"
			ref_je.submit()

			je4 = make_journal_entry(
				account1=asset_account, account2=liability_account, amount=500, save=False
			)
			je4.accounts[0].reference_type = "Journal Entry"
			je4.accounts[0].reference_name = ref_je.name
			je4.accounts[0].party_type = "Customer"
			je4.accounts[0].party = "_Test Customer"

			with self.assertRaises(frappe.ValidationError) as cm4:
				je4.validate_against_jv()
			self.assertIn("does not have any unmatched", str(cm4.exception))

		finally:
			if frappe.db.exists("Account", debtors_account):
				frappe.db.set_value("Account", debtors_account, "is_group", 0)
			if frappe.db.exists("Account", liabilities_account):
				frappe.db.set_value("Account", liabilities_account, "is_group", 0)

	def test_get_outstanding_for_journal_entry_TC_ACC_563(self):
		from erpnext.accounts.doctype.journal_entry.journal_entry import get_outstanding
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		company = "_Test Company"
		create_company(company_name=company)
		abbr = frappe.get_cached_value("Company", company, "abbr")
		get_or_create_customer("_Test Customer")

		if not frappe.db.exists("Account", f"Accounts Receivable - {abbr}"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Accounts Receivable",
					"parent_account": f"Current Assets - {abbr}",
					"company": company,
					"is_group": 1,
					"root_type": "Asset",
				}
			).insert(ignore_permissions=True)

		if not frappe.db.exists("Account", f"Cash In Hand - {abbr}"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Cash In Hand",
					"parent_account": f"Current Assets - {abbr}",
					"company": company,
					"is_group": 1,
					"root_type": "Asset",
				}
			).insert(ignore_permissions=True)

		asset_account = get_or_create_account(
			"Debtors - OUT", company, f"Accounts Receivable - {abbr}", "Receivable", "Asset"
		)

		cash_account = get_or_create_account("Cash - OUT", company, f"Cash In Hand - {abbr}", "Cash", "Asset")
		je = make_journal_entry(account1=asset_account, account2=cash_account, amount=250, save=False)
		je.accounts[0].party_type = "Customer"
		je.accounts[0].party = "_Test Customer"
		je.save()

		args = {
			"doctype": "Journal Entry",
			"docname": je.name,
			"account": asset_account,
			"company": company,
		}
		out = get_outstanding(args)

		self.assertTrue(
			"debit_in_account_currency" in out or "credit_in_account_currency" in out,
			"Outstanding dict must include debit_in_account_currency or credit_in_account_currency",
		)
		self.assertEqual(
			abs(out.get("debit_in_account_currency", 0) or out.get("credit_in_account_currency", 0)), 250
		)

	def test_get_payment_entry_against_invoice_TC_ACC_564(self):
		from erpnext.accounts.doctype.journal_entry.journal_entry import get_payment_entry_against_invoice
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
			create_company,
			create_sales_invoice,
		)

		company = "_Test Company"
		create_company(company_name=company)
		abbr = frappe.get_cached_value("Company", company, "abbr")

		receivable_acc = frappe.db.get_value("Account", {"account_type": "Receivable", "company": company})
		if not receivable_acc:
			receivable_acc = (
				frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": "Test Receivable",
						"parent_account": f"Accounts Receivable - {abbr}",
						"company": company,
						"is_group": 0,
						"account_type": "Receivable",
						"root_type": "Asset",
					}
				)
				.insert(ignore_permissions=True)
				.name
			)

		payable_acc = frappe.db.get_value("Account", {"account_type": "Payable", "company": company})
		if not payable_acc:
			payable_acc = (
				frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": "Test Payable",
						"parent_account": f"Creditors - {abbr}",
						"company": company,
						"is_group": 0,
						"account_type": "Payable",
						"root_type": "Liability",
					}
				)
				.insert(ignore_permissions=True)
				.name
			)

		si = create_sales_invoice(
			customer="_Test Customer",
			company=company,
			posting_date=frappe.utils.nowdate(),
			debit_to=receivable_acc,
			outstanding_amount=100,
		)
		get_payment_entry_against_invoice("Sales Invoice", si.name)

		create_sales_invoice(
			customer="_Test Customer",
			company=company,
			posting_date=frappe.utils.nowdate(),
			debit_to=receivable_acc,
			outstanding_amount=0,
		)

		pi = make_purchase_invoice(
			company=company,
			supplier="_Test Supplier",
			rate=100,
			qty=1,
			uom="Nos",
			do_not_submit=True,
		)
		get_payment_entry_against_invoice("Purchase Invoice", pi.name)

		pi2 = make_purchase_invoice(
			supplier="_Test Supplier",
			company=company,
			posting_date=frappe.utils.nowdate(),
			credit_to=payable_acc,
			uom="Nos",
			outstanding_amount=100,
		)
		get_payment_entry_against_invoice("Purchase Invoice", pi2.name)

	def test_get_exchange_rate_TC_ACC_565(self):
		from frappe.utils import nowdate

		from erpnext.accounts.doctype.journal_entry.journal_entry import get_exchange_rate
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import get_or_create_account
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		company = "_Test Company"
		create_company(company_name=company)
		abbr = frappe.get_cached_value("Company", company, "abbr")

		if not frappe.db.exists("Account", f"Current Assets - {abbr}"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Current Assets",
					"parent_account": f"Assets - {abbr}"
					if frappe.db.exists("Account", f"Assets - {abbr}")
					else None,
					"company": company,
					"is_group": 1,
					"root_type": "Asset",
				}
			).insert(ignore_permissions=True)

		cash_acc = get_or_create_account(
			"Test Cash",
			company,
			f"Current Assets - {abbr}",
			"Cash",
			"Asset",
		)

		with self.assertRaises(frappe.ValidationError):
			get_exchange_rate(nowdate(), account="_Nonexistent Account")

		rate_company_none = get_exchange_rate(nowdate(), account=cash_acc, company=None)
		self.assertTrue(rate_company_none is not None)
		self.assertEqual(rate_company_none, 1)

		rate_currency_none = get_exchange_rate(
			nowdate(), account=cash_acc, company=company, account_currency=None
		)
		self.assertTrue(rate_currency_none is not None)
		self.assertEqual(rate_currency_none, 1)

		foreign_acc = get_or_create_account(
			"Test USD Account",
			company,
			f"Current Assets - {abbr}",
			"Bank",
			"Asset",
		)
		rate_foreign = get_exchange_rate(
			nowdate(), account=foreign_acc, company=company, account_currency="USD"
		)
		self.assertTrue(rate_foreign > 0)

	def test_get_account_details_and_party_type_TC_ACC_566(self):
		from frappe.utils import nowdate

		from erpnext.accounts.doctype.journal_entry.journal_entry import get_account_details_and_party_type
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import get_or_create_account
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company

		company = "_Test Company"
		create_company(company_name=company)
		abbr = frappe.get_cached_value("Company", company, "abbr")

		if not frappe.db.exists("Account", f"Current Assets - {abbr}"):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Current Assets",
					"parent_account": f"Assets - {abbr}"
					if frappe.db.exists("Account", f"Assets - {abbr}")
					else None,
					"company": company,
					"is_group": 1,
					"root_type": "Asset",
				}
			).insert(ignore_permissions=True)

		receivable_acc = get_or_create_account(
			"Test Receivable - PARTY", company, f"Current Assets - {abbr}", "Receivable", "Asset"
		)
		res_receivable = get_account_details_and_party_type(receivable_acc, nowdate(), company)
		self.assertEqual(res_receivable["party_type"], "Customer")
		self.assertEqual(res_receivable["account_type"], "Receivable")
		self.assertTrue(res_receivable["exchange_rate"] > 0)

		payable_acc = get_or_create_account(
			"Test Payable - PARTY", company, f"Current Assets - {abbr}", "Payable", "Liability"
		)
		res_payable = get_account_details_and_party_type(payable_acc, nowdate(), company)
		self.assertEqual(res_payable["party_type"], "Supplier")
		self.assertEqual(res_payable["account_type"], "Payable")
		self.assertTrue(res_payable["exchange_rate"] > 0)

		cash_acc = get_or_create_account(
			"Test Cash - PARTY", company, f"Current Assets - {abbr}", "Cash", "Asset"
		)
		res_cash = get_account_details_and_party_type(cash_acc, nowdate(), company)
		self.assertEqual(res_cash["party_type"], "")
		self.assertEqual(res_cash["account_type"], "Cash")
		self.assertIn("party", res_cash)


def make_journal_entry(
	account1,
	account2,
	amount,
	cost_center=None,
	posting_date=None,
	exchange_rate=1,
	save=True,
	submit=False,
	project=None,
):
	if not cost_center:
		cost_center = "_Test Cost Center - _TC"

	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = posting_date or nowdate()
	jv.company = "_Test Company"
	jv.user_remark = "test"
	jv.multi_currency = 1
	jv.set(
		"accounts",
		[
			{
				"account": account1,
				"cost_center": cost_center,
				"project": project,
				"debit_in_account_currency": amount if amount > 0 else 0,
				"credit_in_account_currency": abs(amount) if amount < 0 else 0,
				"exchange_rate": exchange_rate,
			},
			{
				"account": account2,
				"cost_center": cost_center,
				"project": project,
				"credit_in_account_currency": amount if amount > 0 else 0,
				"debit_in_account_currency": abs(amount) if amount < 0 else 0,
				"exchange_rate": exchange_rate,
			},
		],
	)
	if save or submit:
		jv.insert()

		if submit:
			jv.submit()

	return jv


test_records = frappe.get_test_records("Journal Entry")


def create_custom_test_accounts():
	accounts = [
		["_Test Account Tax Assets", "Current Assets", 1, None, None],
		["_Test Account VAT", "_Test Account Tax Assets", 0, "Tax", None],
		["_Test Account Service Tax", "_Test Account Tax Assets", 0, "Tax", None],
		["_Test Account Reserves and Surplus", "Current Liabilities", 0, None, None],
		["_Test Account Cost for Goods Sold", "Expenses", 0, None, None],
		["_Test Bank", "Bank Accounts", 0, "Bank", None],
		["_Test Account IGST", "_Test Account Tax Assets", 0, "Tax", None],
		["Input Tax CGST", "_Test Account Tax Assets", 0, "Tax", None],
		["Input Tax SGST", "_Test Account Tax Assets", 0, "Tax", None],
		["Input Tax IGST", "_Test Account Tax Assets", 0, "Tax", None],
		["Output Tax SGST Refund", "_Test Account Tax Assets", 0, "Tax", None],
		["Output Tax CGST Refund", "_Test Account Tax Assets", 0, "Tax", None],
		["Output Tax IGST Refund", "_Test Account Tax Assets", 0, "Tax", None],
	]

	company = "_Test Company"
	abbr = "_TC"

	for account_name, parent_account, is_group, account_type, currency in accounts:
		if not frappe.db.exists("Account", account_name + " - " + abbr):
			doc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": account_name,
					"parent_account": f"{parent_account} - {abbr}",
					"company": company,
					"is_group": is_group,
					"account_type": account_type,
					"account_currency": currency
					or frappe.get_cached_value("Company", company, "default_currency"),
					"account_number": "",
				}
			)
			doc.insert(ignore_permissions=True)


def get_or_create_account(account_name, company, parent, account_type, root_type):
	abbr = frappe.get_cached_value("Company", company, "abbr")
	full_name = f"{account_name} - {abbr}"
	if not frappe.db.exists("Account", full_name):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": parent,
				"company": company,
				"account_type": account_type,
				"root_type": root_type,
			}
		).insert(ignore_permissions=True)
	return full_name


def get_or_create_supplier(name="_Test Supplier Payable"):
	if not frappe.db.exists("Supplier", name):
		frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": name,
				"supplier_group": "All Supplier Groups",
				"supplier_type": "Company",
			}
		).insert(ignore_permissions=True)
	return name


def get_or_create_customer(name="_Test Customer", group="_Test Customer Group", territory="_Test Territory"):
	if not frappe.db.exists("Customer", name):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_group": group,
				"territory": territory,
			}
		).insert(ignore_permissions=True)
	return name


def get_or_create_warehouse(name="_Test Warehouse 1 - _TC", company="_Test Company"):
	if not frappe.db.exists("Warehouse", name):
		frappe.get_doc({"doctype": "Warehouse", "warehouse_name": name, "company": company}).insert(
			ignore_permissions=True
		)
	return name


def get_or_create_tds_category(name="_Test TDS Category", company="_Test Company", account=None):
	if not frappe.db.exists("Tax Withholding Category", name):
		frappe.get_doc(
			{
				"doctype": "Tax Withholding Category",
				"name": name,
				"company": company,
				"accounts": [
					{"account": account, "company": company, "tax_withholding_rate": 10.0, "threshold": 0.0}
				],
				"rates": [
					{
						"from_date": frappe.utils.nowdate(),
						"to_date": frappe.utils.add_years(frappe.utils.nowdate(), 1),
						"tax_withholding_rate": 10.0,
						"single_threshold": 0.0,
						"cumulative_threshold": 0.0,
					}
				],
			}
		).insert(ignore_permissions=True)
	return name
