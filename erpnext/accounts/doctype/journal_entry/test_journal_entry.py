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
		field_dict = {'Journal Entry': "against_jv",
			'Sales Order': "against_sales_order",
			'Purchase Order': "against_purchase_order"
			}

		test_voucher.insert()
		test_voucher.submit()

		if test_voucher.doctype == "Journal Entry":
			self.assertTrue(frappe.db.sql("""select name from `tabJournal Entry Account`
				where account = %s and docstatus = 1 and parent = %s""",
				("_Test Receivable - _TC", test_voucher.name)))

		self.assertTrue(not frappe.db.sql("""select name from `tabJournal Entry Account`
			where %s=%s""" % (field_dict.get(test_voucher.doctype), '%s'), (test_voucher.name)))

		base_jv.get("accounts")[0].is_advance = "Yes" if (test_voucher.doctype in ["Sales Order", "Purchase Order"]) else "No"
		base_jv.get("accounts")[0].set(field_dict.get(test_voucher.doctype), test_voucher.name)
		base_jv.insert()
		base_jv.submit()

		submitted_voucher = frappe.get_doc(test_voucher.doctype, test_voucher.name)

		self.assertTrue(frappe.db.sql("""select name from `tabJournal Entry Account`
			where %s=%s""" % (field_dict.get(test_voucher.doctype), '%s'), (submitted_voucher.name)))

		self.assertTrue(frappe.db.sql("""select name from `tabJournal Entry Account`
			where %s=%s and %s=400""" % (field_dict.get(submitted_voucher.doctype), '%s', dr_or_cr), (submitted_voucher.name)))

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
			self.assertTrue(not frappe.db.sql("""select name from `tabJournal Entry Account`
				where against_jv=%s""", test_voucher.name))

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
		
		existing_expense = self.get_actual_expense("2013-02-28")
		current_expense = - existing_expense + 20000 if existing_expense < 0 else 20000
		
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC", 
			"_Test Account Bank Account - _TC", current_expense, "_Test Cost Center - _TC", submit=True)
			
		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv.name}))

	def test_monthly_budget_crossed_stop(self):
		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Stop")
		
		existing_expense = self.get_actual_expense("2013-02-28")
		current_expense = - existing_expense + 20000 if existing_expense < 0 else 20000
		
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC", 
			"_Test Account Bank Account - _TC", current_expense, "_Test Cost Center - _TC")
			
		self.assertRaises(BudgetError, jv.submit)

		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Ignore")

	def test_yearly_budget_crossed_stop(self):
		self.test_monthly_budget_crossed_ignore()

		frappe.db.set_value("Company", "_Test Company", "yearly_bgt_flag", "Stop")
		
		existing_expense = self.get_actual_expense("2013-02-28")
		current_expense = - existing_expense + 150000 if existing_expense < 0 else 150000

		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC", 
			"_Test Account Bank Account - _TC", current_expense, "_Test Cost Center - _TC")
		
		self.assertRaises(BudgetError, jv.submit)

		frappe.db.set_value("Company", "_Test Company", "yearly_bgt_flag", "Ignore")

	def test_monthly_budget_on_cancellation(self):
		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Stop")

		existing_expense = self.get_actual_expense("2013-02-28")
		current_expense = - existing_expense - 30000 if existing_expense < 0 else 30000
		
		jv = make_journal_entry("_Test Account Cost for Goods Sold - _TC", 
			"_Test Account Bank Account - _TC", current_expense, "_Test Cost Center - _TC", submit=True)
		
		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv.name}))

		jv1 = make_journal_entry("_Test Account Cost for Goods Sold - _TC", 
			"_Test Account Bank Account - _TC", 40000, "_Test Cost Center - _TC", submit=True)
					
		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Entry", "voucher_no": jv1.name}))

		self.assertRaises(BudgetError, jv.cancel)

		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Ignore")
		
	def get_actual_expense(self, monthly_end_date):
		return get_actual_expense({
			"account": "_Test Account Cost for Goods Sold - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"monthly_end_date": monthly_end_date,
			"company": "_Test Company",
			"fiscal_year": get_fiscal_year(monthly_end_date)[0]
		})
		
def make_journal_entry(account1, account2, amount, cost_center=None, submit=False):
	jv = frappe.new_doc("Journal Entry")
	jv.posting_date = "2013-02-14"
	jv.company = "_Test Company"
	jv.fiscal_year = "_Test Fiscal Year 2013"
	jv.user_remark = "test"
	
	jv.set("accounts", [
		{
			"account": account1,
			"cost_center": cost_center,
			"debit": amount if amount > 0 else 0,
			"credit": abs(amount) if amount < 0 else 0,
		}, {
			"account": account2,
			"cost_center": cost_center,
			"credit": amount if amount > 0 else 0,
			"debit": abs(amount) if amount < 0 else 0,
		}
	])
	jv.insert()
	
	if submit:
		jv.submit()
	
	return jv
		

test_records = frappe.get_test_records('Journal Entry')
