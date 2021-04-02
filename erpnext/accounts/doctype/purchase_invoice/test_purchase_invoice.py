# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from __future__ import unicode_literals
import unittest
import frappe, erpnext
import frappe.model
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.utils import cint, flt, today, nowdate, add_days
import frappe.defaults
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import set_perpetual_inventory, \
	test_records as pr_test_records, make_purchase_receipt, get_taxes
from erpnext.controllers.accounts_controller import get_payment_terms
from erpnext.exceptions import InvalidCurrency
from erpnext.stock.doctype.stock_entry.test_stock_entry import get_qty_after_transaction
from erpnext.accounts.doctype.account.test_account import get_inventory_account
from erpnext.projects.doctype.project.test_project import make_project

test_dependencies = ["Item", "Cost Center", "Payment Term", "Payment Terms Template"]
test_ignore = ["Serial No"]

class TestPurchaseInvoice(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		unlink_payment_on_cancel_of_invoice()
		frappe.db.set_value("Buying Settings", None, "allow_multiple_items", 1)

	@classmethod
	def tearDownClass(self):
		unlink_payment_on_cancel_of_invoice(0)

	def test_gl_entries_without_perpetual_inventory(self):
		frappe.db.set_value("Company", "_Test Company", "round_off_account", "Round Off - _TC")
		wrapper = frappe.copy_doc(test_records[0])
		set_perpetual_inventory(0, wrapper.company)
		self.assertTrue(not cint(erpnext.is_perpetual_inventory_enabled(wrapper.company)))
		wrapper.insert()
		wrapper.submit()
		wrapper.load_from_db()
		dl = wrapper

		expected_gl_entries = {
			"_Test Payable - _TC": [0, 1512.0],
			"_Test Account Cost for Goods Sold - _TC": [1250, 0],
			"_Test Account Shipping Charges - _TC": [100, 0],
			"_Test Account Excise Duty - _TC": [140, 0],
			"_Test Account Education Cess - _TC": [2.8, 0],
			"_Test Account S&H Education Cess - _TC": [1.4, 0],
			"_Test Account CST - _TC": [29.88, 0],
			"_Test Account VAT - _TC": [156.25, 0],
			"_Test Account Discount - _TC": [0, 168.03],
			"Round Off - _TC": [0, 0.3]
		}
		gl_entries = frappe.db.sql("""select account, debit, credit from `tabGL Entry`
			where voucher_type = 'Purchase Invoice' and voucher_no = %s""", dl.name, as_dict=1)
		for d in gl_entries:
			self.assertEqual([d.debit, d.credit], expected_gl_entries.get(d.account))

	def test_gl_entries_with_perpetual_inventory(self):
		pi = make_purchase_invoice(company="_Test Company with perpetual inventory", supplier_warehouse="Work In Progress - TCP1", warehouse= "Stores - TCP1", cost_center = "Main - TCP1", expense_account ="_Test Account Cost for Goods Sold - TCP1", get_taxes_and_charges=True, qty=10)
		self.assertTrue(cint(erpnext.is_perpetual_inventory_enabled(pi.company)), 1)

		self.check_gle_for_pi(pi.name)

	def test_terms_added_after_save(self):
		pi = frappe.copy_doc(test_records[1])
		pi.insert()
		self.assertTrue(pi.payment_schedule)
		self.assertEqual(pi.payment_schedule[0].due_date, pi.due_date)

	def test_payment_entry_unlink_against_purchase_invoice(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
		unlink_payment_on_cancel_of_invoice(0)

		pi_doc = make_purchase_invoice()

		pe = get_payment_entry("Purchase Invoice", pi_doc.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = pi_doc.currency
		pe.paid_to_account_currency = pi_doc.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = pi_doc.grand_total
		pe.save(ignore_permissions=True)
		pe.submit()

		pi_doc = frappe.get_doc('Purchase Invoice', pi_doc.name)
		pi_doc.load_from_db()
		self.assertTrue(pi_doc.status, "Paid")

		self.assertRaises(frappe.LinkExistsError, pi_doc.cancel)
		unlink_payment_on_cancel_of_invoice()

	def test_purchase_invoice_for_blocked_supplier(self):
		supplier = frappe.get_doc('Supplier', '_Test Supplier')
		supplier.on_hold = 1
		supplier.save()

		self.assertRaises(frappe.ValidationError, make_purchase_invoice)

		supplier.on_hold = 0
		supplier.save()

	def test_purchase_invoice_for_blocked_supplier_invoice(self):
		supplier = frappe.get_doc('Supplier', '_Test Supplier')
		supplier.on_hold = 1
		supplier.hold_type = 'Invoices'
		supplier.save()

		self.assertRaises(frappe.ValidationError, make_purchase_invoice)

		supplier.on_hold = 0
		supplier.save()

	def test_purchase_invoice_for_blocked_supplier_payment(self):
		supplier = frappe.get_doc('Supplier', '_Test Supplier')
		supplier.on_hold = 1
		supplier.hold_type = 'Payments'
		supplier.save()

		pi = make_purchase_invoice()

		self.assertRaises(
			frappe.ValidationError, get_payment_entry, dt='Purchase Invoice', dn=pi.name, bank_account="_Test Bank - _TC")

		supplier.on_hold = 0
		supplier.save()

	def test_purchase_invoice_for_blocked_supplier_payment_today_date(self):
		supplier = frappe.get_doc('Supplier', '_Test Supplier')
		supplier.on_hold = 1
		supplier.hold_type = 'Payments'
		supplier.release_date = nowdate()
		supplier.save()

		pi = make_purchase_invoice()

		self.assertRaises(
			frappe.ValidationError, get_payment_entry, dt='Purchase Invoice', dn=pi.name,
			bank_account="_Test Bank - _TC")

		supplier.on_hold = 0
		supplier.save()

	def test_purchase_invoice_for_blocked_supplier_payment_past_date(self):
		# this test is meant to fail only if something fails in the try block
		with self.assertRaises(Exception):
			try:
				supplier = frappe.get_doc('Supplier', '_Test Supplier')
				supplier.on_hold = 1
				supplier.hold_type = 'Payments'
				supplier.release_date = '2018-03-01'
				supplier.save()

				pi = make_purchase_invoice()

				get_payment_entry('Purchase Invoice', dn=pi.name, bank_account="_Test Bank - _TC")

				supplier.on_hold = 0
				supplier.save()
			except:
				pass
			else:
				raise Exception

	def test_purchase_invoice_blocked_invoice_must_be_in_future(self):
		pi = make_purchase_invoice(do_not_save=True)
		pi.release_date = nowdate()

		self.assertRaises(frappe.ValidationError, pi.save)
		pi.release_date = ''
		pi.save()

	def test_purchase_invoice_temporary_blocked(self):
		pi = make_purchase_invoice(do_not_save=True)
		pi.release_date = add_days(nowdate(), 10)
		pi.save()
		pi.submit()

		pe = get_payment_entry('Purchase Invoice', dn=pi.name, bank_account="_Test Bank - _TC")

		self.assertRaises(frappe.ValidationError, pe.save)

	def test_purchase_invoice_explicit_block(self):
		pi = make_purchase_invoice()
		pi.block_invoice()

		self.assertEqual(pi.on_hold, 1)

		pi.unblock_invoice()

		self.assertEqual(pi.on_hold, 0)

	def test_gl_entries_with_perpetual_inventory_against_pr(self):

		pr = make_purchase_receipt(company="_Test Company with perpetual inventory", supplier_warehouse="Work In Progress - TCP1", warehouse= "Stores - TCP1", cost_center = "Main - TCP1", get_taxes_and_charges=True,)

		self.assertTrue(cint(erpnext.is_perpetual_inventory_enabled(pr.company)), 1)

		pi = make_purchase_invoice(company="_Test Company with perpetual inventory", supplier_warehouse="Work In Progress - TCP1", warehouse= "Stores - TCP1", cost_center = "Main - TCP1", expense_account ="_Test Account Cost for Goods Sold - TCP1", get_taxes_and_charges=True, qty=10,do_not_save= "True")

		for d in pi.items:
			d.purchase_receipt = pr.name

		pi.insert()
		pi.submit()
		pi.load_from_db()

		self.assertTrue(pi.status, "Unpaid")
		self.check_gle_for_pi(pi.name)

	def check_gle_for_pi(self, pi):
		gl_entries = frappe.db.sql("""select account, sum(debit) as debit, sum(credit) as credit
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			group by account""", pi, as_dict=1)

		self.assertTrue(gl_entries)

		expected_values = dict((d[0], d) for d in [
			["Creditors - TCP1", 0, 720],
			["Stock Received But Not Billed - TCP1", 500.0, 0],
			["_Test Account Shipping Charges - TCP1", 100.0, 0.0],
			["_Test Account VAT - TCP1", 120.0, 0]
		])

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[gle.account][0], gle.account)
			self.assertEqual(expected_values[gle.account][1], gle.debit)
			self.assertEqual(expected_values[gle.account][2], gle.credit)

	def test_purchase_invoice_change_naming_series(self):
		pi = frappe.copy_doc(test_records[1])
		pi.insert()
		pi.naming_series = 'TEST-'

		self.assertRaises(frappe.CannotChangeConstantError, pi.save)

		pi = frappe.copy_doc(test_records[0])
		pi.insert()
		pi.load_from_db()

		self.assertTrue(pi.status, "Draft")
		pi.naming_series = 'TEST-'

		self.assertRaises(frappe.CannotChangeConstantError, pi.save)

	def test_gl_entries_with_aia_for_non_stock_items(self):
		pi = frappe.copy_doc(test_records[1])
		set_perpetual_inventory(1, pi.company)
		self.assertTrue(cint(erpnext.is_perpetual_inventory_enabled(pi.company)), 1)
		pi.get("items")[0].item_code = "_Test Non Stock Item"
		pi.get("items")[0].expense_account = "_Test Account Cost for Goods Sold - _TC"
		pi.get("taxes").pop(0)
		pi.get("taxes").pop(1)
		pi.insert()
		pi.submit()
		pi.load_from_db()
		self.assertTrue(pi.status, "Unpaid")

		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""", pi.name, as_dict=1)
		self.assertTrue(gl_entries)

		expected_values = sorted([
			["_Test Payable - _TC", 0, 620],
			["_Test Account Cost for Goods Sold - _TC", 500.0, 0],
			["_Test Account VAT - _TC", 120.0, 0],
		])

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[i][0], gle.account)
			self.assertEqual(expected_values[i][1], gle.debit)
			self.assertEqual(expected_values[i][2], gle.credit)
		set_perpetual_inventory(0, pi.company)

	def test_purchase_invoice_calculation(self):
		pi = frappe.copy_doc(test_records[0])
		pi.insert()
		pi.load_from_db()

		expected_values = [
			["_Test Item Home Desktop 100", 90, 59],
			["_Test Item Home Desktop 200", 135, 177]
		]
		for i, item in enumerate(pi.get("items")):
			self.assertEqual(item.item_code, expected_values[i][0])
			self.assertEqual(item.item_tax_amount, expected_values[i][1])
			self.assertEqual(item.valuation_rate, expected_values[i][2])

		self.assertEqual(pi.base_net_total, 1250)

		# tax amounts
		expected_values = [
			["_Test Account Shipping Charges - _TC", 100, 1350],
			["_Test Account Customs Duty - _TC", 125, 1350],
			["_Test Account Excise Duty - _TC", 140, 1490],
			["_Test Account Education Cess - _TC", 2.8, 1492.8],
			["_Test Account S&H Education Cess - _TC", 1.4, 1494.2],
			["_Test Account CST - _TC", 29.88, 1524.08],
			["_Test Account VAT - _TC", 156.25, 1680.33],
			["_Test Account Discount - _TC", 168.03, 1512.30],
		]

		for i, tax in enumerate(pi.get("taxes")):
			self.assertEqual(tax.account_head, expected_values[i][0])
			self.assertEqual(tax.tax_amount, expected_values[i][1])
			self.assertEqual(tax.total, expected_values[i][2])

	def test_purchase_invoice_with_subcontracted_item(self):
		wrapper = frappe.copy_doc(test_records[0])
		wrapper.get("items")[0].item_code = "_Test FG Item"
		wrapper.insert()
		wrapper.load_from_db()

		expected_values = [
			["_Test FG Item", 90, 59],
			["_Test Item Home Desktop 200", 135, 177]
		]
		for i, item in enumerate(wrapper.get("items")):
			self.assertEqual(item.item_code, expected_values[i][0])
			self.assertEqual(item.item_tax_amount, expected_values[i][1])
			self.assertEqual(item.valuation_rate, expected_values[i][2])

		self.assertEqual(wrapper.base_net_total, 1250)

		# tax amounts
		expected_values = [
			["_Test Account Shipping Charges - _TC", 100, 1350],
			["_Test Account Customs Duty - _TC", 125, 1350],
			["_Test Account Excise Duty - _TC", 140, 1490],
			["_Test Account Education Cess - _TC", 2.8, 1492.8],
			["_Test Account S&H Education Cess - _TC", 1.4, 1494.2],
			["_Test Account CST - _TC", 29.88, 1524.08],
			["_Test Account VAT - _TC", 156.25, 1680.33],
			["_Test Account Discount - _TC", 168.03, 1512.30],
		]

		for i, tax in enumerate(wrapper.get("taxes")):
			self.assertEqual(tax.account_head, expected_values[i][0])
			self.assertEqual(tax.tax_amount, expected_values[i][1])
			self.assertEqual(tax.total, expected_values[i][2])

	def test_purchase_invoice_with_advance(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry \
			import test_records as jv_test_records

		jv = frappe.copy_doc(jv_test_records[1])
		jv.insert()
		jv.submit()

		pi = frappe.copy_doc(test_records[0])
		pi.disable_rounded_total = 1
		pi.allocate_advances_automatically = 0
		pi.append("advances", {
			"reference_type": "Journal Entry",
			"reference_name": jv.name,
			"reference_row": jv.get("accounts")[0].name,
			"advance_amount": 400,
			"allocated_amount": 300,
			"remarks": jv.remark
		})
		pi.insert()

		self.assertEqual(pi.outstanding_amount, 1212.30)

		pi.disable_rounded_total = 0
		pi.get("payment_schedule")[0].payment_amount = 1512.0
		pi.save()
		self.assertEqual(pi.outstanding_amount, 1212.0)

		pi.submit()
		pi.load_from_db()

		self.assertTrue(frappe.db.sql("""select name from `tabJournal Entry Account`
			where reference_type='Purchase Invoice'
			and reference_name=%s and debit_in_account_currency=300""", pi.name))

		pi.cancel()

		self.assertFalse(frappe.db.sql("""select name from `tabJournal Entry Account`
			where reference_type='Purchase Invoice' and reference_name=%s""", pi.name))

	def test_invoice_with_advance_and_multi_payment_terms(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry \
			import test_records as jv_test_records

		jv = frappe.copy_doc(jv_test_records[1])
		jv.insert()
		jv.submit()

		pi = frappe.copy_doc(test_records[0])
		pi.disable_rounded_total = 1
		pi.allocate_advances_automatically = 0
		pi.append("advances", {
			"reference_type": "Journal Entry",
			"reference_name": jv.name,
			"reference_row": jv.get("accounts")[0].name,
			"advance_amount": 400,
			"allocated_amount": 300,
			"remarks": jv.remark
		})
		pi.insert()

		pi.update({
			"payment_schedule": get_payment_terms("_Test Payment Term Template",
				pi.posting_date, pi.grand_total)
		})

		pi.save()
		pi.submit()
		self.assertEqual(pi.payment_schedule[0].payment_amount, 606.15)
		self.assertEqual(pi.payment_schedule[0].due_date, pi.posting_date)
		self.assertEqual(pi.payment_schedule[1].payment_amount, 606.15)
		self.assertEqual(pi.payment_schedule[1].due_date, add_days(pi.posting_date, 30))

		pi.load_from_db()

		self.assertTrue(
			frappe.db.sql(
				"select name from `tabJournal Entry Account` where reference_type='Purchase Invoice' and "
				"reference_name=%s and debit_in_account_currency=300", pi.name)
		)

		self.assertEqual(pi.outstanding_amount, 1212.30)

		pi.cancel()

		self.assertFalse(
			frappe.db.sql(
				"select name from `tabJournal Entry Account` where reference_type='Purchase Invoice' and "
				"reference_name=%s", pi.name)
		)

	def test_total_purchase_cost_for_project(self):
		make_project({'project_name':'_Test Project'})

		existing_purchase_cost = frappe.db.sql("""select sum(base_net_amount)
			from `tabPurchase Invoice Item` where project = '_Test Project' and docstatus=1""")
		existing_purchase_cost = existing_purchase_cost and existing_purchase_cost[0][0] or 0

		pi = make_purchase_invoice(currency="USD", conversion_rate=60, project="_Test Project")
		self.assertEqual(frappe.db.get_value("Project", "_Test Project", "total_purchase_cost"),
			existing_purchase_cost + 15000)

		pi1 = make_purchase_invoice(qty=10, project="_Test Project")
		self.assertEqual(frappe.db.get_value("Project", "_Test Project", "total_purchase_cost"),
			existing_purchase_cost + 15500)

		pi1.cancel()
		self.assertEqual(frappe.db.get_value("Project", "_Test Project", "total_purchase_cost"),
			existing_purchase_cost + 15000)

		pi.cancel()
		self.assertEqual(frappe.db.get_value("Project", "_Test Project", "total_purchase_cost"), existing_purchase_cost)

	def test_return_purchase_invoice(self):
		set_perpetual_inventory()

		pi = make_purchase_invoice()

		return_pi = make_purchase_invoice(is_return=1, return_against=pi.name, qty=-2)


		# check gl entries for return
		gl_entries = frappe.db.sql("""select account, debit, credit
			from `tabGL Entry` where voucher_type=%s and voucher_no=%s
			order by account desc""", ("Purchase Invoice", return_pi.name), as_dict=1)

		self.assertTrue(gl_entries)

		expected_values = {
			"Creditors - _TC": [100.0, 0.0],
			"Stock Received But Not Billed - _TC": [0.0, 100.0],
		}

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.debit)
			self.assertEqual(expected_values[gle.account][1], gle.credit)

		set_perpetual_inventory(0)

	def test_multi_currency_gle(self):
		set_perpetual_inventory(0)

		pi = make_purchase_invoice(supplier="_Test Supplier USD", credit_to="_Test Payable USD - _TC",
			currency="USD", conversion_rate=50)

		gl_entries = frappe.db.sql("""select account, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""", pi.name, as_dict=1)

		self.assertTrue(gl_entries)

		expected_values = {
			"_Test Payable USD - _TC": {
				"account_currency": "USD",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 12500,
				"credit_in_account_currency": 250
			},
			"_Test Account Cost for Goods Sold - _TC": {
				"account_currency": "INR",
				"debit": 12500,
				"debit_in_account_currency": 12500,
				"credit": 0,
				"credit_in_account_currency": 0
			}
		}

		for field in ("account_currency", "debit", "debit_in_account_currency", "credit", "credit_in_account_currency"):
			for i, gle in enumerate(gl_entries):
				self.assertEqual(expected_values[gle.account][field], gle[field])


		# Check for valid currency
		pi1 = make_purchase_invoice(supplier="_Test Supplier USD", credit_to="_Test Payable USD - _TC",
			do_not_save=True)

		self.assertRaises(InvalidCurrency, pi1.save)

		# cancel
		pi.cancel()

		gle = frappe.db.sql("""select name from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""", pi.name)

		self.assertFalse(gle)

	def test_purchase_invoice_update_stock_gl_entry_with_perpetual_inventory(self):

		pi = make_purchase_invoice(update_stock=1, posting_date=frappe.utils.nowdate(),
			posting_time=frappe.utils.nowtime(), cash_bank_account="Cash - TCP1", company="_Test Company with perpetual inventory", supplier_warehouse="Work In Progress - TCP1", warehouse= "Stores - TCP1", cost_center = "Main - TCP1", expense_account ="_Test Account Cost for Goods Sold - TCP1")

		gl_entries = frappe.db.sql("""select account, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""", pi.name, as_dict=1)

		self.assertTrue(gl_entries)
		stock_in_hand_account = get_inventory_account(pi.company, pi.get("items")[0].warehouse)

		expected_gl_entries = dict((d[0], d) for d in [
			[pi.credit_to, 0.0, 250.0],
			[stock_in_hand_account, 250.0, 0.0]
		])

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gl_entries[gle.account][0], gle.account)
			self.assertEqual(expected_gl_entries[gle.account][1], gle.debit)
			self.assertEqual(expected_gl_entries[gle.account][2], gle.credit)

	def test_purchase_invoice_for_is_paid_and_update_stock_gl_entry_with_perpetual_inventory(self):

		pi = make_purchase_invoice(update_stock=1, posting_date=frappe.utils.nowdate(),
			posting_time=frappe.utils.nowtime(), cash_bank_account="Cash - TCP1", is_paid=1, company="_Test Company with perpetual inventory", supplier_warehouse="Work In Progress - TCP1", warehouse= "Stores - TCP1", cost_center = "Main - TCP1", expense_account ="_Test Account Cost for Goods Sold - TCP1")

		gl_entries = frappe.db.sql("""select account, account_currency, sum(debit) as debit,
				sum(credit) as credit, debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			group by account, voucher_no order by account asc;""", pi.name, as_dict=1)

		stock_in_hand_account = get_inventory_account(pi.company, pi.get("items")[0].warehouse)
		self.assertTrue(gl_entries)

		expected_gl_entries = dict((d[0], d) for d in [
			[pi.credit_to, 250.0, 250.0],
			[stock_in_hand_account, 250.0, 0.0],
			["Cash - TCP1", 0.0, 250.0]
		])

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gl_entries[gle.account][0], gle.account)
			self.assertEqual(expected_gl_entries[gle.account][1], gle.debit)
			self.assertEqual(expected_gl_entries[gle.account][2], gle.credit)

	def test_auto_batch(self):
		item_code = frappe.db.get_value('Item',
			{'has_batch_no': 1, 'create_new_batch':1}, 'name')

		if not item_code:
			doc = frappe.get_doc({
				'doctype': 'Item',
				'is_stock_item': 1,
				'item_code': 'test batch item',
				'item_group': 'Products',
				'has_batch_no': 1,
				'create_new_batch': 1
			}).insert(ignore_permissions=True)
			item_code = doc.name

		pi = make_purchase_invoice(update_stock=1, posting_date=frappe.utils.nowdate(),
			posting_time=frappe.utils.nowtime(), item_code=item_code)

		self.assertTrue(frappe.db.get_value('Batch',
			{'item': item_code, 'reference_name': pi.name}))

	def test_update_stock_and_purchase_return(self):
		actual_qty_0 = get_qty_after_transaction()

		pi = make_purchase_invoice(update_stock=1, posting_date=frappe.utils.nowdate(),
			posting_time=frappe.utils.nowtime())

		actual_qty_1 = get_qty_after_transaction()
		self.assertEqual(actual_qty_0 + 5, actual_qty_1)

		# return entry
		pi1 = make_purchase_invoice(is_return=1, return_against=pi.name, qty=-2, rate=50, update_stock=1)

		pi.load_from_db()
		self.assertTrue(pi.status, "Debit Note Issued")
		pi1.load_from_db()
		self.assertTrue(pi1.status, "Return")

		actual_qty_2 = get_qty_after_transaction()
		self.assertEqual(actual_qty_1 - 2, actual_qty_2)

		pi1.cancel()
		self.assertEqual(actual_qty_1, get_qty_after_transaction())

		pi.reload()
		pi.cancel()
		self.assertEqual(actual_qty_0, get_qty_after_transaction())

	def test_subcontracting_via_purchase_invoice(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		make_stock_entry(item_code="_Test Item", target="_Test Warehouse 1 - _TC", qty=100, basic_rate=100)
		make_stock_entry(item_code="_Test Item Home Desktop 100", target="_Test Warehouse 1 - _TC",
			qty=100, basic_rate=100)

		pi = make_purchase_invoice(item_code="_Test FG Item", qty=10, rate=500,
			update_stock=1, is_subcontracted="Yes")

		self.assertEqual(len(pi.get("supplied_items")), 2)

		rm_supp_cost = sum([d.amount for d in pi.get("supplied_items")])
		self.assertEqual(pi.get("items")[0].rm_supp_cost, flt(rm_supp_cost, 2))

	def test_rejected_serial_no(self):
		set_perpetual_inventory(0)
		pi = make_purchase_invoice(item_code="_Test Serialized Item With Series", received_qty=2, qty=1,
			rejected_qty=1, rate=500, update_stock=1,
			rejected_warehouse = "_Test Rejected Warehouse - _TC")

		self.assertEqual(frappe.db.get_value("Serial No", pi.get("items")[0].serial_no, "warehouse"),
			pi.get("items")[0].warehouse)

		self.assertEqual(frappe.db.get_value("Serial No", pi.get("items")[0].rejected_serial_no,
			"warehouse"), pi.get("items")[0].rejected_warehouse)

	def test_outstanding_amount_after_advance_jv_cancelation(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry \
			import test_records as jv_test_records

		jv = frappe.copy_doc(jv_test_records[1])
		jv.accounts[0].is_advance = 'Yes'
		jv.insert()
		jv.submit()

		pi = frappe.copy_doc(test_records[0])
		pi.append("advances", {
			"reference_type": "Journal Entry",
			"reference_name": jv.name,
			"reference_row": jv.get("accounts")[0].name,
			"advance_amount": 400,
			"allocated_amount": 300,
			"remarks": jv.remark
		})
		pi.insert()
		pi.submit()
		pi.load_from_db()

		#check outstanding after advance allocation
		self.assertEqual(flt(pi.outstanding_amount), flt(pi.rounded_total - pi.total_advance))

		#added to avoid Document has been modified exception
		jv = frappe.get_doc("Journal Entry", jv.name)
		jv.cancel()

		pi.load_from_db()
		#check outstanding after advance cancellation
		self.assertEqual(flt(pi.outstanding_amount), flt(pi.rounded_total + pi.total_advance))

	def test_outstanding_amount_after_advance_payment_entry_cancelation(self):
		pe = frappe.get_doc({
			"doctype": "Payment Entry",
			"payment_type": "Pay",
			"party_type": "Supplier",
			"party": "_Test Supplier",
			"company": "_Test Company",
			"paid_from_account_currency": "INR",
			"paid_to_account_currency": "INR",
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"reference_no": "1",
			"reference_date": nowdate(),
			"received_amount": 300,
			"paid_amount": 300,
			"paid_from": "_Test Cash - _TC",
			"paid_to": "_Test Payable - _TC"
		})
		pe.insert()
		pe.submit()

		pi = frappe.copy_doc(test_records[0])
		pi.is_pos = 0
		pi.append("advances", {
			"doctype": "Purchase Invoice Advance",
			"reference_type": "Payment Entry",
			"reference_name": pe.name,
			"advance_amount": 300,
			"allocated_amount": 300,
			"remarks": pe.remarks
		})
		pi.insert()
		pi.submit()

		pi.load_from_db()

		#check outstanding after advance allocation
		self.assertEqual(flt(pi.outstanding_amount), flt(pi.rounded_total - pi.total_advance))

		#added to avoid Document has been modified exception
		pe = frappe.get_doc("Payment Entry", pe.name)
		pe.cancel()

		pi.load_from_db()
		#check outstanding after advance cancellation
		self.assertEqual(flt(pi.outstanding_amount), flt(pi.rounded_total + pi.total_advance))

	def test_purchase_invoice_with_shipping_rule(self):
		from erpnext.accounts.doctype.shipping_rule.test_shipping_rule \
			import create_shipping_rule

		shipping_rule = create_shipping_rule(shipping_rule_type = "Buying", shipping_rule_name = "Shipping Rule - Purchase Invoice Test")

		pi = frappe.copy_doc(test_records[0])

		pi.shipping_rule = shipping_rule.name
		pi.insert()

		shipping_amount = 0.0
		for condition in shipping_rule.get("conditions"):
			if not condition.to_value or (flt(condition.from_value) <= pi.net_total <= flt(condition.to_value)):
				shipping_amount = condition.shipping_amount

		shipping_charge = {
			"doctype": "Purchase Taxes and Charges",
			"category": "Valuation and Total",
			"charge_type": "Actual",
			"account_head": shipping_rule.account,
			"cost_center": shipping_rule.cost_center,
			"tax_amount": shipping_amount,
			"description": shipping_rule.name,
			"add_deduct_tax": "Add"
		}
		pi.append("taxes", shipping_charge)
		pi.save()

		self.assertEqual(pi.net_total, 1250)

		self.assertEqual(pi.total_taxes_and_charges, 462.3)
		self.assertEqual(pi.grand_total, 1712.3)

	def test_make_pi_without_terms(self):
		pi = make_purchase_invoice(do_not_save=1)

		self.assertFalse(pi.get('payment_schedule'))

		pi.insert()

		self.assertTrue(pi.get('payment_schedule'))

	def test_duplicate_due_date_in_terms(self):
		pi = make_purchase_invoice(do_not_save=1)
		pi.append('payment_schedule', dict(due_date='2017-01-01', invoice_portion=50.00, payment_amount=50))
		pi.append('payment_schedule', dict(due_date='2017-01-01', invoice_portion=50.00, payment_amount=50))

		self.assertRaises(frappe.ValidationError, pi.insert)

	def test_debit_note(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import get_outstanding_amount

		pi = make_purchase_invoice(item_code = "_Test Item", qty = (5 * -1), rate=500, is_return = 1)
		pi.load_from_db()
		self.assertTrue(pi.status, "Return")

		outstanding_amount = get_outstanding_amount(pi.doctype,
			pi.name, "Creditors - _TC", pi.supplier, "Supplier")

		self.assertEqual(pi.outstanding_amount, outstanding_amount)

		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = pi.currency
		pe.paid_to_account_currency = pi.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = pi.grand_total * -1
		pe.insert()
		pe.submit()

		pi_doc = frappe.get_doc('Purchase Invoice', pi.name)
		self.assertEqual(pi_doc.outstanding_amount, 0)

	def test_purchase_invoice_with_cost_center(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center
		cost_center = "_Test Cost Center for BS Account - _TC"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")

		pi =  make_purchase_invoice_against_cost_center(cost_center=cost_center, credit_to="Creditors - _TC")
		self.assertEqual(pi.cost_center, cost_center)

		expected_values = {
			"Creditors - _TC": {
				"cost_center": cost_center
			},
			"_Test Account Cost for Goods Sold - _TC": {
				"cost_center": cost_center
			}
		}

		gl_entries = frappe.db.sql("""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""", pi.name, as_dict=1)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_purchase_invoice_without_cost_center(self):
		cost_center = "_Test Cost Center - _TC"
		pi =  make_purchase_invoice(credit_to="Creditors - _TC")

		expected_values = {
			"Creditors - _TC": {
				"cost_center": None
			},
			"_Test Account Cost for Goods Sold - _TC": {
				"cost_center": cost_center
			}
		}

		gl_entries = frappe.db.sql("""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""", pi.name, as_dict=1)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_purchase_invoice_with_project_link(self):
		project = make_project({
			'project_name': 'Purchase Invoice Project',
			'project_template_name': 'Test Project Template',
			'start_date': '2020-01-01'
		})
		item_project = make_project({
			'project_name': 'Purchase Invoice Item Project',
			'project_template_name': 'Test Project Template',
			'start_date': '2019-06-01'
		})

		pi = make_purchase_invoice(credit_to="Creditors - _TC" ,do_not_save=1)
		pi.items[0].project = item_project.project_name
		pi.project = project.project_name

		pi.submit()

		expected_values = {
			"Creditors - _TC": {
				"project": project.project_name
			},
			"_Test Account Cost for Goods Sold - _TC": {
				"project": item_project.project_name
			}
		}

		gl_entries = frappe.db.sql("""select account, cost_center, project, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""", pi.name, as_dict=1)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["project"], gle.project)

def unlink_payment_on_cancel_of_invoice(enable=1):
	accounts_settings = frappe.get_doc("Accounts Settings")
	accounts_settings.unlink_payment_on_cancellation_of_invoice = enable
	accounts_settings.save()

def make_purchase_invoice(**args):
	pi = frappe.new_doc("Purchase Invoice")
	args = frappe._dict(args)
	pi.posting_date = args.posting_date or today()
	if args.posting_time:
		pi.posting_time = args.posting_time
	if args.update_stock:
		pi.update_stock = 1
	if args.is_paid:
		pi.is_paid = 1

	if args.cash_bank_account:
		pi.cash_bank_account=args.cash_bank_account

	pi.company = args.company or "_Test Company"
	pi.supplier = args.supplier or "_Test Supplier"
	pi.currency = args.currency or "INR"
	pi.conversion_rate = args.conversion_rate or 1
	pi.is_return = args.is_return
	pi.return_against = args.return_against
	pi.is_subcontracted = args.is_subcontracted or "No"
	pi.supplier_warehouse = args.supplier_warehouse or "_Test Warehouse 1 - _TC"

	pi.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"qty": args.qty or 5,
		"received_qty": args.received_qty or 0,
		"rejected_qty": args.rejected_qty or 0,
		"rate": args.rate or 50,
		'expense_account': args.expense_account or '_Test Account Cost for Goods Sold - _TC',
		"conversion_factor": 1.0,
		"serial_no": args.serial_no,
		"stock_uom": "_Test UOM",
		"cost_center": args.cost_center or "_Test Cost Center - _TC",
		"project": args.project,
		"rejected_warehouse": args.rejected_warehouse or "",
		"rejected_serial_no": args.rejected_serial_no or "",
		"asset_location": args.location or ""
	})

	if args.get_taxes_and_charges:
		taxes = get_taxes()
		for tax in taxes:
			pi.append("taxes", tax)

	if not args.do_not_save:
		pi.insert()
		if not args.do_not_submit:
			pi.submit()
	return pi

def make_purchase_invoice_against_cost_center(**args):
	pi = frappe.new_doc("Purchase Invoice")
	args = frappe._dict(args)
	pi.posting_date = args.posting_date or today()
	if args.posting_time:
		pi.posting_time = args.posting_time
	if args.update_stock:
		pi.update_stock = 1
	if args.is_paid:
		pi.is_paid = 1

	if args.cash_bank_account:
		pi.cash_bank_account=args.cash_bank_account

	pi.company = args.company or "_Test Company"
	pi.cost_center = args.cost_center or "_Test Cost Center - _TC"
	pi.supplier = args.supplier or "_Test Supplier"
	pi.currency = args.currency or "INR"
	pi.conversion_rate = args.conversion_rate or 1
	pi.is_return = args.is_return
	pi.is_return = args.is_return
	pi.credit_to = args.return_against or "Creditors - _TC"
	pi.is_subcontracted = args.is_subcontracted or "No"
	pi.supplier_warehouse = "_Test Warehouse 1 - _TC"

	pi.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"qty": args.qty or 5,
		"received_qty": args.received_qty or 0,
		"rejected_qty": args.rejected_qty or 0,
		"rate": args.rate or 50,
		"conversion_factor": 1.0,
		"serial_no": args.serial_no,
		"stock_uom": "_Test UOM",
		"cost_center": args.cost_center or "_Test Cost Center - _TC",
		"project": args.project,
		"rejected_warehouse": args.rejected_warehouse or "",
		"rejected_serial_no": args.rejected_serial_no or ""
	})
	if not args.do_not_save:
		pi.insert()
		if not args.do_not_submit:
			pi.submit()
	return pi

test_records = frappe.get_test_records('Purchase Invoice')
