# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.tests.utils import change_settings
from frappe.utils import flt, nowdate

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
					("_Test Receivable - _TC", test_voucher.name),
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
				"""select name from `tabJournal Entry Account`
			where reference_type = %s and reference_name = %s and {0}=400""".format(
					dr_or_cr
				),
				(submitted_voucher.doctype, submitted_voucher.name),
			)
		)

		if base_jv.get("accounts")[0].is_advance == "Yes":
			self.advance_paid_testcase(base_jv, submitted_voucher, dr_or_cr)
		self.cancel_against_voucher_testcase(submitted_voucher)

	def advance_paid_testcase(self, base_jv, test_voucher, dr_or_cr):
		# Test advance paid field
		advance_paid = frappe.db.sql(
			"""select advance_paid from `tab%s`
					where name=%s"""
			% (test_voucher.doctype, "%s"),
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
			frappe.db.set_value(
				"Accounts Settings", "Accounts Settings", "unlink_advance_payment_on_cancelation_of_order", 0
			)
			submitted_voucher = frappe.get_doc(test_voucher.doctype, test_voucher.name)
			self.assertRaises(frappe.LinkExistsError, submitted_voucher.cancel)

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
		jv.insert()

		if account_bal == stock_bal:
			self.assertRaises(StockAccountInvalidTransaction, jv.submit)
			frappe.db.rollback()
		else:
			jv.submit()
			jv.cancel()

	def test_multi_currency(self):
		jv = make_journal_entry(
			"_Test Bank USD - _TC", "_Test Bank - _TC", 100, exchange_rate=50, save=False
		)

		jv.get("accounts")[1].credit_in_account_currency = 5000
		jv.submit()

		gl_entries = frappe.db.sql(
			"""select account, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Journal Entry' and voucher_no=%s
			order by account asc""",
			jv.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		expected_values = {
			"_Test Bank USD - _TC": {
				"account_currency": "USD",
				"debit": 5000,
				"debit_in_account_currency": 100,
				"credit": 0,
				"credit_in_account_currency": 0,
			},
			"_Test Bank - _TC": {
				"account_currency": "INR",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 5000,
				"credit_in_account_currency": 5000,
			},
		}

		for field in (
			"account_currency",
			"debit",
			"debit_in_account_currency",
			"credit",
			"credit_in_account_currency",
		):
			for i, gle in enumerate(gl_entries):
				self.assertEqual(expected_values[gle.account][field], gle[field])

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

		gl_entries = frappe.db.sql(
			"""select account, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Journal Entry' and voucher_no=%s
			order by account asc""",
			rjv.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		expected_values = {
			"_Test Bank USD - _TC": {
				"account_currency": "USD",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 5000,
				"credit_in_account_currency": 100,
			},
			"Sales - _TC": {
				"account_currency": "INR",
				"debit": 5000,
				"debit_in_account_currency": 5000,
				"credit": 0,
				"credit_in_account_currency": 0,
			},
		}

		for field in (
			"account_currency",
			"debit",
			"debit_in_account_currency",
			"credit",
			"credit_in_account_currency",
		):
			for i, gle in enumerate(gl_entries):
				self.assertEqual(expected_values[gle.account][field], gle[field])

	def test_disallow_change_in_account_currency_for_a_party(self):
		# create jv in USD
		jv = make_journal_entry("_Test Bank USD - _TC", "_Test Receivable USD - _TC", 100, save=False)

		jv.accounts[1].update({"party_type": "Customer", "party": "_Test Customer USD"})

		jv.submit()

		# create jv in USD, but account currency in INR
		jv = make_journal_entry("_Test Bank - _TC", "_Test Receivable - _TC", 100, save=False)

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

		expected_values = {
			"_Test Cash - _TC": {"cost_center": cost_center},
			"_Test Bank - _TC": {"cost_center": cost_center},
		}

		gl_entries = frappe.db.sql(
			"""select account, cost_center, debit, credit
			from `tabGL Entry` where voucher_type='Journal Entry' and voucher_no=%s
			order by account asc""",
			jv.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_jv_with_project(self):
		from erpnext.projects.doctype.project.test_project import make_project

		if not frappe.db.exists("Project", {"project_name": "Journal Entry Project"}):
			project = make_project(
				{
					"project_name": "Journal Entry Project",
					"project_template_name": "Test Project Template",
					"start_date": "2020-01-01",
				}
			)
			project_name = project.name
		else:
			project_name = frappe.get_value("Project", {"project_name": "_Test Project"})

		jv = make_journal_entry("_Test Cash - _TC", "_Test Bank - _TC", 100, save=False)
		for d in jv.accounts:
			d.project = project_name
		jv.voucher_type = "Bank Entry"
		jv.multi_currency = 0
		jv.cheque_no = "112233"
		jv.cheque_date = nowdate()
		jv.insert()
		jv.submit()

		expected_values = {
			"_Test Cash - _TC": {"project": project_name},
			"_Test Bank - _TC": {"project": project_name},
		}

		gl_entries = frappe.db.sql(
			"""select account, project, debit, credit
			from `tabGL Entry` where voucher_type='Journal Entry' and voucher_no=%s
			order by account asc""",
			jv.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["project"], gle.project)

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
