# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe

class TestJournalVoucher(unittest.TestCase):
	def test_journal_voucher_with_against_jv(self):
		self.clear_account_balance()
		jv_invoice = frappe.copy_doc(test_records[2])
		jv_invoice.insert()
		jv_invoice.submit()

		self.assertTrue(frappe.db.sql("""select name from `tabJournal Voucher Detail`
			where account = %s and docstatus = 1 and parent = %s""",
			("_Test Customer - _TC", jv_invoice.name)))

		self.assertTrue(not frappe.db.sql("""select name from `tabJournal Voucher Detail`
			where against_jv=%s""", jv_invoice.name))

		jv_payment = frappe.copy_doc(test_records[0])
		jv_payment.get("entries")[0].against_jv = jv_invoice.name
		jv_payment.insert()
		jv_payment.submit()

		self.assertTrue(frappe.db.sql("""select name from `tabJournal Voucher Detail`
			where against_jv=%s""", jv_invoice.name))

		self.assertTrue(frappe.db.sql("""select name from `tabJournal Voucher Detail`
			where against_jv=%s and credit=400""", jv_invoice.name))

		# cancel jv_invoice
		jv_invoice.cancel()

		self.assertTrue(not frappe.db.sql("""select name from `tabJournal Voucher Detail`
			where against_jv=%s""", jv_invoice.name))

	def test_jv_against_stock_account(self):
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory
		set_perpetual_inventory()

		jv = frappe.copy_doc(test_records[0])
		jv.get("entries")[0].account = "_Test Warehouse - _TC"
		jv.insert()

		from erpnext.accounts.general_ledger import StockAccountInvalidTransaction
		self.assertRaises(StockAccountInvalidTransaction, jv.submit)

		set_perpetual_inventory(0)

	def test_monthly_budget_crossed_ignore(self):
		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Ignore")
		self.clear_account_balance()

		jv = frappe.copy_doc(test_records[0])
		jv.get("entries")[1].account = "_Test Account Cost for Goods Sold - _TC"
		jv.get("entries")[1].cost_center = "_Test Cost Center - _TC"
		jv.get("entries")[1].debit = 20000.0
		jv.get("entries")[0].credit = 20000.0
		jv.insert()
		jv.submit()
		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Voucher", "voucher_no": jv.name}))

	def test_monthly_budget_crossed_stop(self):
		from erpnext.accounts.utils import BudgetError
		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Stop")
		self.clear_account_balance()

		jv = frappe.copy_doc(test_records[0])
		jv.get("entries")[1].account = "_Test Account Cost for Goods Sold - _TC"
		jv.get("entries")[1].cost_center = "_Test Cost Center - _TC"
		jv.get("entries")[1].debit = 20000.0
		jv.get("entries")[0].credit = 20000.0
		jv.insert()

		self.assertRaises(BudgetError, jv.submit)

		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Ignore")

	def test_yearly_budget_crossed_stop(self):
		from erpnext.accounts.utils import BudgetError
		self.clear_account_balance()
		self.test_monthly_budget_crossed_ignore()

		frappe.db.set_value("Company", "_Test Company", "yearly_bgt_flag", "Stop")

		jv = frappe.copy_doc(test_records[0])
		jv.posting_date = "2013-08-12"
		jv.get("entries")[1].account = "_Test Account Cost for Goods Sold - _TC"
		jv.get("entries")[1].cost_center = "_Test Cost Center - _TC"
		jv.get("entries")[1].debit = 150000.0
		jv.get("entries")[0].credit = 150000.0
		jv.insert()

		self.assertRaises(BudgetError, jv.submit)

		frappe.db.set_value("Company", "_Test Company", "yearly_bgt_flag", "Ignore")

	def test_monthly_budget_on_cancellation(self):
		from erpnext.accounts.utils import BudgetError
		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Stop")
		self.clear_account_balance()

		jv = frappe.copy_doc(test_records[0])
		jv.get("entries")[0].account = "_Test Account Cost for Goods Sold - _TC"
		jv.get("entries")[0].cost_center = "_Test Cost Center - _TC"
		jv.get("entries")[0].credit = 30000.0
		jv.get("entries")[1].debit = 30000.0
		jv.submit()

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Voucher", "voucher_no": jv.name}))

		jv1 = frappe.copy_doc(test_records[0])
		jv1.get("entries")[1].account = "_Test Account Cost for Goods Sold - _TC"
		jv1.get("entries")[1].cost_center = "_Test Cost Center - _TC"
		jv1.get("entries")[1].debit = 40000.0
		jv1.get("entries")[0].credit = 40000.0
		jv1.submit()

		self.assertTrue(frappe.db.get_value("GL Entry",
			{"voucher_type": "Journal Voucher", "voucher_no": jv1.name}))

		self.assertRaises(BudgetError, jv.cancel)

		frappe.db.set_value("Company", "_Test Company", "monthly_bgt_flag", "Ignore")

	def clear_account_balance(self):
		frappe.db.sql("""delete from `tabGL Entry`""")


test_records = frappe.get_test_records('Journal Voucher')
