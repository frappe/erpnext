# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import unittest, frappe
from frappe.utils import flt

class TestJournalVoucher(unittest.TestCase):
	def test_journal_voucher_with_against_jv(self):

		jv_invoice = frappe.copy_doc(test_records[2])
		base_jv = frappe.copy_doc(test_records[0])
		self.jv_against_voucher_testcase(base_jv, jv_invoice)

	def test_jv_against_sales_order(self):
		from erpnext.selling.doctype.sales_order.test_sales_order \
			import test_records as so_test_records

		sales_order = frappe.copy_doc(so_test_records[0])
		base_jv = frappe.copy_doc(test_records[0])
		self.jv_against_voucher_testcase(base_jv, sales_order)

	def test_jv_against_purchase_order(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order \
			import test_records as po_test_records

		purchase_order = frappe.copy_doc(po_test_records[0])
		base_jv = frappe.copy_doc(test_records[1])
		self.jv_against_voucher_testcase(base_jv, purchase_order)

	def jv_against_voucher_testcase(self, base_jv, test_voucher):
		dr_or_cr = "credit" if test_voucher.doctype in ["Sales Order", "Journal Voucher"] else "debit"
		field_dict = {'Journal Voucher': "against_jv",
			'Sales Order': "against_sales_order",
			'Purchase Order': "against_purchase_order"
			}

		self.clear_account_balance()
		test_voucher.insert()
		test_voucher.submit()

		if test_voucher.doctype == "Journal Voucher":
			self.assertTrue(frappe.db.sql("""select name from `tabJournal Voucher Detail`
				where account = %s and docstatus = 1 and parent = %s""",
				("_Test Customer - _TC", test_voucher.name)))

		self.assertTrue(not frappe.db.sql("""select name from `tabJournal Voucher Detail`
			where %s=%s""" % (field_dict.get(test_voucher.doctype), '%s'), (test_voucher.name)))

		base_jv.get("entries")[0].is_advance = "Yes" if (test_voucher.doctype in ["Sales Order", "Purchase Order"]) else "No"
		base_jv.get("entries")[0].set(field_dict.get(test_voucher.doctype), test_voucher.name)
		base_jv.insert()
		base_jv.submit()

		submitted_voucher = frappe.get_doc(test_voucher.doctype, test_voucher.name)

		self.assertTrue(frappe.db.sql("""select name from `tabJournal Voucher Detail`
			where %s=%s""" % (field_dict.get(test_voucher.doctype), '%s'), (submitted_voucher.name)))

		self.assertTrue(frappe.db.sql("""select name from `tabJournal Voucher Detail`
			where %s=%s and %s=400""" % (field_dict.get(submitted_voucher.doctype), '%s', dr_or_cr), (submitted_voucher.name)))

		if base_jv.get("entries")[0].is_advance == "Yes":
			self.advance_paid_testcase(base_jv, submitted_voucher, dr_or_cr)
		self.cancel_against_voucher_testcase(submitted_voucher)

	def advance_paid_testcase(self, base_jv, test_voucher, dr_or_cr):
		#Test advance paid field
		advance_paid = frappe.db.sql("""select advance_paid from `tab%s`
					where name=%s""" % (test_voucher.doctype, '%s'), (test_voucher.name))
		payment_against_order = base_jv.get("entries")[0].get(dr_or_cr)
		
		self.assertTrue(flt(advance_paid[0][0]) == flt(payment_against_order))

	def cancel_against_voucher_testcase(self, test_voucher):
		if test_voucher.doctype == "Journal Voucher":
			# if test_voucher is a Journal Voucher, test cancellation of test_voucher 
			test_voucher.cancel()
			self.assertTrue(not frappe.db.sql("""select name from `tabJournal Voucher Detail`
				where against_jv=%s""", test_voucher.name))

		elif test_voucher.doctype in ["Sales Order", "Purchase Order"]:
			# if test_voucher is a Sales Order/Purchase Order, test error on cancellation of test_voucher 
			submitted_voucher = frappe.get_doc(test_voucher.doctype, test_voucher.name)
			self.assertRaises(frappe.LinkExistsError, submitted_voucher.cancel)

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
