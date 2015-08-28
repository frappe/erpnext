# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest, frappe
from frappe.utils import flt
from erpnext.accounts.utils import get_actual_expense, BudgetError, get_fiscal_year


class TestJournalEntry(unittest.TestCase):
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
			self.assertTrue(frappe.db.sql("""select name from `tabJournal Entry Account`
				where account = %s and docstatus = 1 and parent = %s""",
				("_Test Receivable - _TC", test_voucher.name)))

		self.assertFalse(frappe.db.sql("""select name from `tabJournal Entry Account`
			where reference_type = %s and reference_name = %s""", (test_voucher.doctype, test_voucher.name)))

		base_jv.get("accounts")[0].is_advance = "Yes" if (test_voucher.doctype in ["Sales Order", "Purchase Order"]) else "No"
		base_jv.get("accounts")[0].set("reference_type", test_voucher.doctype)
		base_jv.get("accounts")[0].set("reference_name", test_voucher.name)
		base_jv.insert()
		base_jv.submit()

		submitted_voucher = frappe.get_doc(test_voucher.doctype, test_voucher.name)

		self.assertTrue(frappe.db.sql("""select name from `tabJournal Entry Account`
			where reference_type = %s and reference_name = %s and {0}=400""".format(dr_or_cr),
				(submitted_voucher.doctype, submitted_voucher.name)))

		if base_jv.get("accounts")[0].is_advance == "Yes":
			self.advance_paid_testcase(base_jv, submitted_voucher, dr_or_cr)
		self.cancel_against_voucher_testcase(submitted_voucher)

	def advance_paid_testcase(self, base_jv, test_voucher, dr_or_cr):
		#Test advance paid field
		advance_paid = frappe.db.sql("""select advance_paid from `tab%s`
					where name=%s""" % (test_voucher.doctype, '%s'), (test_voucher.name))
		payment_against_order = base_jv.get("accounts")[0].get(dr_or_cr)

		self.assertTrue(flt(advance_paid[0][0]) == flt(payment_against_order))

	def cancel_against_voucher_testcase(self, test_voucher):
		if test_voucher.doctype == "Journal Entry":
			# if test_voucher is a Journal Entry, test cancellation of test_voucher
			test_voucher.cancel()
			self.assertFalse(frappe.db.sql("""select name from `tabJournal Entry Account`
				where reference_type='Journal Entry' and reference_name=%s""", test_voucher.name))

		elif test_voucher.doctype in ["Sales Order", "Purchase Order"]:
			# if test_voucher is a Sales Order/Purchase Order, test error on cancellation of test_voucher
			submitted_voucher = frappe.get_doc(test_voucher.doctype, test_voucher.name)
			self.assertRaises(frappe.LinkExistsError, submitted_voucher.cancel)

	def test_jv_against_stock_account(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
		set_perpetual_inventory()

		jv = frappe.copy_doc(test_records[0])
		jv.get("accounts")[0].update({
			"account": "_Test Warehouse - _TC",
			"party_type": None,
			"party": None
		})

		jv.insert()

		from erpnext.accounts.general_ledger import StockAccountInvalidTransaction
		self.assertRaises(StockAccountInvalidTransaction, jv.submit)

		set_perpetual_inventory(0)

	def test_monthly_budget_crossed_ignore(self):
		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Ignore")

		self.set_total_expense_zero("2013-02-28")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center - _TC", submit=True)

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv.name}))

	def test_monthly_budget_crossed_stop(self):
		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Stop")

		self.set_total_expense_zero("2013-02-28")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 40000, "_Test Cost Center - _TC")

		self.assertRaises(BudgetError, jv.submit)

		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Ignore")

	def test_yearly_budget_crossed_stop(self):
		self.test_monthly_budget_crossed_ignore()

		frappe.db.set_value("Company", "_Test Company", "yearly_bgt_flag", "Stop")

		self.set_total_expense_zero("2013-02-28")

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 150000, "_Test Cost Center - _TC")

		self.assertRaises(BudgetError, jv.submit)

		frappe.db.set_value("Company", "_Test Company", "yearly_bgt_flag", "Ignore")

	def test_monthly_budget_on_cancellation(self):
		self.set_total_expense_zero("2013-02-28")

		jv1 = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 20000, "_Test Cost Center - _TC", submit=True)

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv1.name}))

		jv2 = make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", 20000, "_Test Cost Center - _TC", submit=True)

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv2.name}))

		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Stop")

		self.assertRaises(BudgetError, jv1.cancel)

		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Ignore")

	def get_actual_expense(self, monthly_end_date):
		return get_actual_expense({
			"account": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"monthly_end_date": monthly_end_date,
			"company": "_Test Company",
			"fiscal_year": get_fiscal_year(monthly_end_date)[0]
		})

	def set_total_expense_zero(self, posting_date):
		existing_expense = self.get_actual_expense(posting_date)
		make_journal_entry("_Test Account Cost for Goods Sold - _TC",
			"_Test Bank - _TC", -existing_expense, "_Test Cost Center - _TC", submit=True)
			
	def test_multi_currency(self):
		jv = make_journal_entry("_Test Bank USD - _TC",
			"_Test Bank - _TC", 100, exchange_rate=50, save=False)
			
		jv.get("accounts")[1].credit_in_account_currency = 5000
		jv.submit()
			
		gl_entries = frappe.db.sql("""select account, account_currency, debit, credit, 
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Journal Entry' and voucher_no=%s
			order by account asc""", jv.name, as_dict=1)

		self.assertTrue(gl_entries)

		expected_values = {
			"_Test Bank USD - _TC": {
				"account_currency": "USD",
				"debit": 5000,
				"debit_in_account_currency": 100,
				"credit": 0,
				"credit_in_account_currency": 0
			},
			"_Test Bank - _TC": {
				"account_currency": "INR",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 5000,
				"credit_in_account_currency": 5000
			}
		}
		
		for field in ("account_currency", "debit", "debit_in_account_currency", "credit", "credit_in_account_currency"):
			for i, gle in enumerate(gl_entries):
				self.assertEquals(expected_values[gle.account][field], gle[field])
		
		

		# cancel
		jv.cancel()

		gle = frappe.db.sql("""select name from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""", jv.name)

		self.assertFalse(gle)

def make_journal_entry(account1, account2, amount, cost_center=None, exchange_rate=1, save=True, submit=False):
	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = "2013-02-14"
	jv.company = "_Test Company"
	jv.fiscal_year = "_Test Fiscal Year 2013"
	jv.user_remark = "test"
	jv.exchange_rate = exchange_rate

	jv.set("accounts", [
		{
			"account": account1,
			"cost_center": cost_center,
			"debit_in_account_currency": amount if amount > 0 else 0,
			"credit_in_account_currency": abs(amount) if amount < 0 else 0,
		}, {
			"account": account2,
			"cost_center": cost_center,
			"credit_in_account_currency": amount if amount > 0 else 0,
			"debit_in_account_currency": abs(amount) if amount < 0 else 0,
		}
	])
	if save or submit:
		jv.insert()

		if submit:
			jv.submit()

	return jv


test_records = frappe.get_test_records('Journal Entry')
