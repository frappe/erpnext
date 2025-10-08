# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
import frappe.utils
from frappe.tests.utils import FrappeTestCase, change_settings, if_app_installed
from frappe.utils import (
	add_days,
	cint,
	flt,
	formatdate,
	get_quarter_start,
	get_year_ending,
	get_year_start,
	getdate,
	nowdate,
	today,
)

import erpnext
from erpnext.accounts.doctype.account.test_account import create_account, get_inventory_account
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.buying.doctype.purchase_order.purchase_order import get_mapped_purchase_invoice
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice as make_pi_from_po
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.controllers.accounts_controller import InvalidQtyError, get_payment_terms
from erpnext.controllers.buying_controller import QtyMismatchError
from erpnext.exceptions import InvalidCurrency
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
	make_purchase_invoice as create_purchase_invoice_from_receipt,
)
from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import (
	get_taxes,
	make_purchase_receipt,
)
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_batch_from_bundle,
	get_serial_nos_from_bundle,
	make_serial_batch_bundle,
)
from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse
from erpnext.stock.tests.test_utils import StockTestMixin

from .purchase_invoice import make_debit_note

test_dependencies = ["Item", "Cost Center", "Payment Term", "Payment Terms Template"]
test_ignore = ["Serial No"]


class TestPurchaseInvoice(FrappeTestCase, StockTestMixin):
	@classmethod
	def setUpClass(self):
		unlink_payment_on_cancel_of_invoice()
		frappe.db.set_single_value("Buying Settings", "allow_multiple_items", 1)

	@classmethod
	def tearDownClass(self):
		unlink_payment_on_cancel_of_invoice(0)

	def tearDown(self):
		frappe.db.rollback()

	def test_purchase_invoice_qty(self):
		pi = make_purchase_invoice(qty=0, do_not_save=True)
		with self.assertRaises(InvalidQtyError):
			pi.save()

		# No error with qty=1
		pi.items[0].qty = 1
		pi.save()
		self.assertEqual(pi.items[0].qty, 1)

	def test_purchase_invoice_received_qty(self):
		"""
		1. Test if received qty is validated against accepted + rejected
		2. Test if received qty is auto set on save
		"""
		pi = make_purchase_invoice(
			qty=1,
			rejected_qty=1,
			received_qty=3,
			item_code="_Test Item Home Desktop 200",
			rejected_warehouse="_Test Rejected Warehouse - _TC",
			update_stock=True,
			do_not_save=True,
		)
		self.assertRaises(QtyMismatchError, pi.save)

		pi.items[0].received_qty = 0
		pi.save()
		self.assertEqual(pi.items[0].received_qty, 2)

		# teardown
		pi.delete()

	def test_update_received_qty_in_material_request(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
		from erpnext.stock.doctype.material_request.test_material_request import make_material_request

		"""
		Test if the received_qty in Material Request is updated correctly when
		a Purchase Invoice with update_stock=True is submitted.
		"""
		mr = make_material_request(item_code="_Test Item", qty=10)
		mr.save()
		mr.submit()
		po = make_purchase_order(mr.name)
		po.supplier = "_Test Supplier"
		po.save()
		po.submit()

		# Create a Purchase Invoice with update_stock=True
		pi = make_purchase_invoice(po.name)
		pi.update_stock = True
		pi.insert(ignore_permissions=True)
		pi.submit()

		# Check if the received quantity is updated in Material Request
		mr.reload()
		self.assertEqual(mr.items[0].received_qty, 10)

	def test_gl_entries_without_perpetual_inventory(self):
		frappe.db.set_value("Company", "_Test Company", "round_off_account", "Round Off - _TC")
		pi = frappe.copy_doc(test_records[0])
		self.assertTrue(not cint(erpnext.is_perpetual_inventory_enabled(pi.company)))
		pi.insert(ignore_permissions=True)
		pi.submit()

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
			"Round Off - _TC": [0, 0.3],
		}
		gl_entries = frappe.db.sql(
			"""select account, debit, credit from `tabGL Entry`
			where voucher_type = 'Purchase Invoice' and voucher_no = %s""",
			pi.name,
			as_dict=1,
		)
		for d in gl_entries:
			self.assertEqual([d.debit, d.credit], expected_gl_entries.get(d.account))

	def test_gl_entries_with_perpetual_inventory(self):
		pi = make_purchase_invoice(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			expense_account="_Test Account Cost for Goods Sold - TCP1",
			get_taxes_and_charges=True,
			qty=10,
		)

		self.assertTrue(cint(erpnext.is_perpetual_inventory_enabled(pi.company)), 1)

		self.check_gle_for_pi(pi.name)

	def test_terms_added_after_save(self):
		pi = frappe.copy_doc(test_records[1])
		pi.insert(ignore_permissions=True)
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

		pi_doc = frappe.get_doc("Purchase Invoice", pi_doc.name)
		pi_doc.load_from_db()
		self.assertTrue(pi_doc.status, "Paid")
		pi_doc.cancel()
		self.assertRaises(frappe.LinkExistsError, pi_doc.delete)
		unlink_payment_on_cancel_of_invoice()

	def test_purchase_invoice_for_blocked_supplier(self):
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.on_hold = 1
		supplier.save()

		self.assertRaises(frappe.ValidationError, make_purchase_invoice)

		supplier.on_hold = 0
		supplier.save()

	def test_purchase_invoice_for_blocked_supplier_invoice(self):
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.on_hold = 1
		supplier.hold_type = "Invoices"
		supplier.save()

		self.assertRaises(frappe.ValidationError, make_purchase_invoice)

		supplier.on_hold = 0
		supplier.save()

	def test_purchase_invoice_for_blocked_supplier_payment(self):
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.on_hold = 1
		supplier.hold_type = "Payments"
		supplier.save()

		pi = make_purchase_invoice()

		self.assertRaises(
			frappe.ValidationError,
			get_payment_entry,
			dt="Purchase Invoice",
			dn=pi.name,
			bank_account="_Test Bank - _TC",
		)

		supplier.on_hold = 0
		supplier.save()

	def test_purchase_invoice_for_blocked_supplier_payment_today_date(self):
		supplier = frappe.get_doc("Supplier", "_Test Supplier")
		supplier.on_hold = 1
		supplier.hold_type = "Payments"
		supplier.release_date = nowdate()
		supplier.save()

		pi = make_purchase_invoice()

		self.assertRaises(
			frappe.ValidationError,
			get_payment_entry,
			dt="Purchase Invoice",
			dn=pi.name,
			bank_account="_Test Bank - _TC",
		)

		supplier.on_hold = 0
		supplier.save()

	def test_purchase_invoice_for_blocked_supplier_payment_past_date(self):
		# this test is meant to fail only if something fails in the try block
		with self.assertRaises(Exception):
			try:
				supplier = frappe.get_doc("Supplier", "_Test Supplier")
				supplier.on_hold = 1
				supplier.hold_type = "Payments"
				supplier.release_date = "2018-03-01"
				supplier.save()

				pi = make_purchase_invoice()

				get_payment_entry("Purchase Invoice", dn=pi.name, bank_account="_Test Bank - _TC")

				supplier.on_hold = 0
				supplier.save()
			except Exception:
				pass
			else:
				raise Exception

	def test_purchase_invoice_blocked_invoice_must_be_in_future(self):
		pi = make_purchase_invoice(do_not_save=True)
		pi.release_date = nowdate()

		self.assertRaises(frappe.ValidationError, pi.save)
		pi.release_date = ""
		pi.save()

	def test_purchase_invoice_temporary_blocked(self):
		pi = make_purchase_invoice(do_not_save=True)
		pi.release_date = add_days(nowdate(), 10)
		pi.save()
		pi.submit()

		pe = get_payment_entry("Purchase Invoice", dn=pi.name, bank_account="_Test Bank - _TC")

		self.assertRaises(frappe.ValidationError, pe.save)

	def test_purchase_invoice_explicit_block(self):
		pi = make_purchase_invoice()
		pi.block_invoice()

		self.assertEqual(pi.on_hold, 1)

		pi.unblock_invoice()

		self.assertEqual(pi.on_hold, 0)

	def test_gl_entries_with_perpetual_inventory_against_pr(self):
		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			supplier_warehouse="Work In Progress - TCP1",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			get_taxes_and_charges=True,
		)

		pi = make_purchase_invoice(
			company="_Test Company with perpetual inventory",
			supplier_warehouse="Work In Progress - TCP1",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			expense_account="_Test Account Cost for Goods Sold - TCP1",
			get_taxes_and_charges=True,
			qty=10,
			do_not_save="True",
		)

		for d in pi.items:
			d.purchase_receipt = pr.name

		pi.insert(ignore_permissions=True)
		pi.submit()
		pi.load_from_db()

		self.assertTrue(pi.status, "Unpaid")
		self.check_gle_for_pi(pi.name)

	def check_gle_for_pi(self, pi):
		gl_entries = frappe.db.sql(
			"""select account, sum(debit) as debit, sum(credit) as credit
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			group by account""",
			pi,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		expected_values = dict(
			(d[0], d)
			for d in [
				["Creditors - TCP1", 0, 720],
				["Stock Received But Not Billed - TCP1", 500.0, 0],
				["_Test Account Shipping Charges - TCP1", 100.0, 0.0],
				["_Test Account VAT - TCP1", 120.0, 0],
			]
		)

		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[gle.account][0], gle.account)
			self.assertEqual(expected_values[gle.account][1], gle.debit)
			self.assertEqual(expected_values[gle.account][2], gle.credit)

	def test_purchase_invoice_with_exchange_rate_difference(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_invoice as create_purchase_invoice,
		)

		pr = make_purchase_receipt(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			currency="USD",
			conversion_rate=70,
		)

		pi = create_purchase_invoice(pr.name)
		pi.conversion_rate = 80

		pi.insert(ignore_permissions=True)
		pi.submit()

		# Get exchnage gain and loss account
		exchange_gain_loss_account = frappe.db.get_value("Company", pi.company, "exchange_gain_loss_account")

		# fetching the latest GL Entry with exchange gain and loss account account
		amount = frappe.db.get_value(
			"GL Entry", {"account": exchange_gain_loss_account, "voucher_no": pi.name}, "debit"
		)
		discrepancy_caused_by_exchange_rate_diff = abs(
			pi.items[0].base_net_amount - pr.items[0].base_net_amount
		)

		self.assertEqual(discrepancy_caused_by_exchange_rate_diff, amount)

	def test_purchase_invoice_change_naming_series(self):
		pi = frappe.copy_doc(test_records[1])
		pi.insert(ignore_permissions=True)
		pi.naming_series = "TEST-"

		self.assertRaises(frappe.CannotChangeConstantError, pi.save)

		pi = frappe.copy_doc(test_records[0])
		pi.insert(ignore_permissions=True)
		pi.load_from_db()

		self.assertTrue(pi.status, "Draft")
		pi.naming_series = "TEST-"

		self.assertRaises(frappe.CannotChangeConstantError, pi.save)

	def test_gl_entries_for_non_stock_items_with_perpetual_inventory(self):
		pi = make_purchase_invoice(
			item_code="_Test Non Stock Item",
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			expense_account="_Test Account Cost for Goods Sold - TCP1",
		)

		self.assertTrue(pi.status, "Unpaid")

		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""",
			pi.name,
			as_dict=1,
		)
		self.assertTrue(gl_entries)
		if frappe.db.db_type == "postgres":
			expected_values = [
				["Creditors - TCP1", 0, 250],
				["_Test Account Cost for Goods Sold - TCP1", 250.0, 0],
			]
		else:
			expected_values = [
				["_Test Account Cost for Goods Sold - TCP1", 250.0, 0],
				["Creditors - TCP1", 0, 250],
			]

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_values[i][0], gle.account)
			self.assertEqual(expected_values[i][1], gle.debit)
			self.assertEqual(expected_values[i][2], gle.credit)

	def test_purchase_invoice_calculation(self):
		pi = frappe.copy_doc(test_records[0])
		pi.insert(ignore_permissions=True)
		pi.load_from_db()

		expected_values = [
			["_Test Item Home Desktop 100", 90, 59],
			["_Test Item Home Desktop 200", 135, 177],
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

	@change_settings("Accounts Settings", {"unlink_payment_on_cancellation_of_invoice": 1})
	def test_purchase_invoice_with_advance(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import (
			test_records as jv_test_records,
		)

		jv = frappe.copy_doc(jv_test_records[1])
		jv.insert()
		jv.submit()

		pi = frappe.copy_doc(test_records[0])
		pi.disable_rounded_total = 1
		pi.allocate_advances_automatically = 0
		pi.append(
			"advances",
			{
				"reference_type": "Journal Entry",
				"reference_name": jv.name,
				"reference_row": jv.get("accounts")[0].name,
				"advance_amount": 400,
				"allocated_amount": 300,
				"remarks": jv.remark,
			},
		)
		pi.insert(ignore_permissions=True)

		self.assertEqual(pi.outstanding_amount, 1212.30)

		pi.disable_rounded_total = 0
		pi.get("payment_schedule")[0].payment_amount = 1512.0
		pi.save()
		self.assertEqual(pi.outstanding_amount, 1212.0)

		pi.submit()
		pi.load_from_db()

		self.assertTrue(
			frappe.db.sql(
				"""select name from `tabJournal Entry Account`
			where reference_type='Purchase Invoice'
			and reference_name=%s and debit_in_account_currency=300""",
				pi.name,
			)
		)

		pi.cancel()

		self.assertFalse(
			frappe.db.sql(
				"""select name from `tabJournal Entry Account`
			where reference_type='Purchase Invoice' and reference_name=%s""",
				pi.name,
			)
		)

	@change_settings("Accounts Settings", {"unlink_payment_on_cancellation_of_invoice": 1})
	def test_invoice_with_advance_and_multi_payment_terms(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import (
			test_records as jv_test_records,
		)

		jv = frappe.copy_doc(jv_test_records[1])
		jv.insert()
		jv.submit()

		pi = frappe.copy_doc(test_records[0])
		pi.disable_rounded_total = 1
		pi.allocate_advances_automatically = 0
		pi.append(
			"advances",
			{
				"reference_type": "Journal Entry",
				"reference_name": jv.name,
				"reference_row": jv.get("accounts")[0].name,
				"advance_amount": 400,
				"allocated_amount": 300,
				"remarks": jv.remark,
			},
		)
		pi.insert(ignore_permissions=True)

		pi.update(
			{
				"payment_schedule": get_payment_terms(
					"_Test Payment Term Template", pi.posting_date, pi.grand_total, pi.base_grand_total
				)
			}
		)

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
				"reference_name=%s and debit_in_account_currency=300",
				pi.name,
			)
		)

		self.assertEqual(pi.outstanding_amount, 1212.30)

		pi.cancel()

		self.assertFalse(
			frappe.db.sql(
				"select name from `tabJournal Entry Account` where reference_type='Purchase Invoice' and "
				"reference_name=%s",
				pi.name,
			)
		)

	def test_return_purchase_invoice_with_perpetual_inventory(self):
		pi = make_purchase_invoice(
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			expense_account="_Test Account Cost for Goods Sold - TCP1",
		)

		return_pi = make_purchase_invoice(
			is_return=1,
			return_against=pi.name,
			qty=-2,
			company="_Test Company with perpetual inventory",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			expense_account="_Test Account Cost for Goods Sold - TCP1",
		)

		# check gl entries for return
		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type=%s and voucher_no=%s
			order by account desc""",
			("Purchase Invoice", return_pi.name),
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		expected_values = {
			"Creditors - TCP1": [100.0, 0.0],
			"Stock Received But Not Billed - TCP1": [0.0, 100.0],
		}

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.debit)
			self.assertEqual(expected_values[gle.account][1], gle.credit)

	def test_standalone_return_using_pi(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

		item = self.make_item().name
		company = "_Test Company with perpetual inventory"
		warehouse = "Stores - TCP1"

		make_stock_entry(item_code=item, target=warehouse, qty=50, rate=120)

		return_pi = make_purchase_invoice(
			is_return=1,
			item=item,
			qty=-10,
			update_stock=1,
			rate=100,
			company=company,
			warehouse=warehouse,
			cost_center="Main - TCP1",
		)

		# assert that stock consumption is with actual rate
		self.assertGLEs(
			return_pi,
			[{"credit": 1200, "debit": 0}],
			gle_filters={"account": "Stock In Hand - TCP1"},
		)

	def test_return_with_lcv(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc
		from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import (
			create_landed_cost_voucher,
		)

		item = self.make_item().name
		company = "_Test Company with perpetual inventory"
		warehouse = "Stores - TCP1"
		cost_center = "Main - TCP1"

		pi = make_purchase_invoice(
			item=item,
			company=company,
			warehouse=warehouse,
			cost_center=cost_center,
			update_stock=1,
			qty=10,
			rate=100,
		)

		# Create landed cost voucher - will increase valuation of received item by 10
		create_landed_cost_voucher("Purchase Invoice", pi.name, pi.company, charges=100)
		return_pi = make_return_doc(pi.doctype, pi.name)
		return_pi.save().submit()

		# assert that stock consumption is with actual in rate
		self.assertGLEs(
			return_pi,
			[{"credit": 1100, "debit": 0}],
			gle_filters={"account": "Stock In Hand - TCP1"},
		)

		# assert loss booked in COGS
		self.assertGLEs(
			return_pi,
			[{"credit": 0, "debit": 100}],
			gle_filters={"account": "Cost of Goods Sold - TCP1"},
		)

	def test_multi_currency_gle(self):
		pi = make_purchase_invoice(
			supplier="_Test Supplier USD",
			credit_to="_Test Payable USD - _TC",
			currency="USD",
			conversion_rate=50,
		)

		gl_entries = frappe.db.sql(
			"""select account, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""",
			pi.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		expected_values = {
			"_Test Payable USD - _TC": {
				"account_currency": "USD",
				"debit": 0,
				"debit_in_account_currency": 0,
				"credit": 12500,
				"credit_in_account_currency": 250,
			},
			"_Test Account Cost for Goods Sold - _TC": {
				"account_currency": "INR",
				"debit": 12500,
				"debit_in_account_currency": 12500,
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
			for _i, gle in enumerate(gl_entries):
				self.assertEqual(expected_values[gle.account][field], gle[field])

		# Check for valid currency
		pi1 = make_purchase_invoice(
			supplier="_Test Supplier USD", credit_to="_Test Payable USD - _TC", do_not_save=True
		)

		self.assertRaises(InvalidCurrency, pi1.save)

		# cancel
		pi.cancel()

		gle = frappe.db.sql(
			"""select name from `tabGL Entry`
			where voucher_type='Sales Invoice' and voucher_no=%s""",
			pi.name,
		)

		self.assertFalse(gle)

	def test_purchase_invoice_update_stock_gl_entry_with_perpetual_inventory(self):
		pi = make_purchase_invoice(
			update_stock=1,
			posting_date=frappe.utils.nowdate(),
			posting_time=frappe.utils.nowtime(),
			cash_bank_account="Cash - TCP1",
			company="_Test Company with perpetual inventory",
			supplier_warehouse="Work In Progress - TCP1",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			expense_account="_Test Account Cost for Goods Sold - TCP1",
		)

		gl_entries = frappe.db.sql(
			"""select account, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""",
			pi.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)
		stock_in_hand_account = get_inventory_account(pi.company, pi.get("items")[0].warehouse)

		expected_gl_entries = dict(
			(d[0], d) for d in [[pi.credit_to, 0.0, 250.0], [stock_in_hand_account, 250.0, 0.0]]
		)

		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gl_entries[gle.account][0], gle.account)
			self.assertEqual(expected_gl_entries[gle.account][1], gle.debit)
			self.assertEqual(expected_gl_entries[gle.account][2], gle.credit)

	def test_purchase_invoice_for_is_paid_and_update_stock_gl_entry_with_perpetual_inventory(self):
		pi = make_purchase_invoice(
			update_stock=1,
			posting_date=frappe.utils.nowdate(),
			posting_time=frappe.utils.nowtime(),
			cash_bank_account="Cash - TCP1",
			is_paid=1,
			company="_Test Company with perpetual inventory",
			supplier_warehouse="Work In Progress - TCP1",
			warehouse="Stores - TCP1",
			cost_center="Main - TCP1",
			expense_account="_Test Account Cost for Goods Sold - TCP1",
		)

		gl_entries = frappe.db.sql(
			"""SELECT
				account,
				ARRAY_AGG(account_currency) AS account_currency,
				SUM(debit) AS debit,
				SUM(credit) AS credit,
				SUM(debit_in_account_currency) AS debit_in_account_currency,
				SUM(credit_in_account_currency) AS credit_in_account_currency
			FROM
				`tabGL Entry`
			WHERE
				voucher_type = 'Purchase Invoice'
				AND voucher_no = %s
			GROUP BY
				account,
				voucher_no
			ORDER BY
				account ASC;""",
			(pi.name,),
			as_dict=1,
		)
		stock_in_hand_account = get_inventory_account(pi.company, pi.get("items")[0].warehouse)
		self.assertTrue(gl_entries)

		expected_gl_entries = dict(
			(d[0], d)
			for d in [
				[pi.credit_to, 250.0, 250.0],
				[stock_in_hand_account, 250.0, 0.0],
				["Cash - TCP1", 0.0, 250.0],
			]
		)

		for _i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gl_entries[gle.account][0], gle.account)
			self.assertEqual(expected_gl_entries[gle.account][1], gle.debit)
			self.assertEqual(expected_gl_entries[gle.account][2], gle.credit)

	def test_auto_batch(self):
		item_code = frappe.db.get_value("Item", {"has_batch_no": 1, "create_new_batch": 1}, "name")

		if not item_code:
			doc = frappe.get_doc(
				{
					"doctype": "Item",
					"is_stock_item": 1,
					"item_code": "test batch item",
					"item_group": "Products",
					"has_batch_no": 1,
					"create_new_batch": 1,
				}
			).insert(ignore_permissions=True)
			item_code = doc.name

		pi = make_purchase_invoice(
			update_stock=1,
			posting_date=frappe.utils.nowdate(),
			posting_time=frappe.utils.nowtime(),
			item_code=item_code,
		)

		self.assertTrue(frappe.db.get_value("Batch", {"item": item_code, "reference_name": pi.name}))

	def test_update_stock_and_purchase_return(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import get_qty_after_transaction

		actual_qty_0 = get_qty_after_transaction()

		pi = make_purchase_invoice(
			update_stock=1, posting_date=frappe.utils.nowdate(), posting_time=frappe.utils.nowtime()
		)

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

	def test_rejected_serial_no(self):
		pi = make_purchase_invoice(
			item_code="_Test Serialized Item With Series",
			received_qty=2,
			qty=1,
			rejected_qty=1,
			rate=500,
			update_stock=1,
			rejected_warehouse="_Test Rejected Warehouse - _TC",
			allow_zero_valuation_rate=1,
		)
		pi.load_from_db()

		serial_no = get_serial_nos_from_bundle(pi.get("items")[0].serial_and_batch_bundle)[0]
		rejected_serial_no = get_serial_nos_from_bundle(pi.get("items")[0].rejected_serial_and_batch_bundle)[
			0
		]

		self.assertEqual(
			frappe.db.get_value("Serial No", serial_no, "warehouse"),
			pi.get("items")[0].warehouse,
		)

		self.assertEqual(
			frappe.db.get_value("Serial No", rejected_serial_no, "warehouse"),
			pi.get("items")[0].rejected_warehouse,
		)

	def test_outstanding_amount_after_advance_jv_cancelation(self):
		from erpnext.accounts.doctype.journal_entry.test_journal_entry import (
			test_records as jv_test_records,
		)

		jv = frappe.copy_doc(jv_test_records[1])
		jv.accounts[0].is_advance = "Yes"
		jv.insert()
		jv.submit()

		pi = frappe.copy_doc(test_records[0])
		pi.append(
			"advances",
			{
				"reference_type": "Journal Entry",
				"reference_name": jv.name,
				"reference_row": jv.get("accounts")[0].name,
				"advance_amount": 400,
				"allocated_amount": 300,
				"remarks": jv.remark,
			},
		)
		pi.insert(ignore_permissions=True)
		pi.submit()
		pi.load_from_db()

		# check outstanding after advance allocation
		self.assertEqual(flt(pi.outstanding_amount), flt(pi.rounded_total - pi.total_advance))

		# added to avoid Document has been modified exception
		jv = frappe.get_doc("Journal Entry", jv.name)
		jv.cancel()

		pi.load_from_db()
		# check outstanding after advance cancellation
		self.assertEqual(flt(pi.outstanding_amount), flt(pi.rounded_total + pi.total_advance))

	def test_outstanding_amount_after_advance_payment_entry_cancelation(self):
		pe = frappe.get_doc(
			{
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
				"paid_to": "_Test Payable - _TC",
			}
		)
		pe.insert(ignore_permissions=True)
		pe.submit()

		pi = frappe.copy_doc(test_records[0])
		pi.is_pos = 0
		pi.append(
			"advances",
			{
				"doctype": "Purchase Invoice Advance",
				"reference_type": "Payment Entry",
				"reference_name": pe.name,
				"advance_amount": 300,
				"allocated_amount": 300,
				"remarks": pe.remarks,
			},
		)
		pi.insert(ignore_permissions=True)
		pi.submit()

		pi.load_from_db()

		# check outstanding after advance allocation
		self.assertEqual(flt(pi.outstanding_amount), flt(pi.rounded_total - pi.total_advance))

		# added to avoid Document has been modified exception
		pe = frappe.get_doc("Payment Entry", pe.name)
		pe.cancel()

		pi.load_from_db()
		# check outstanding after advance cancellation
		self.assertEqual(flt(pi.outstanding_amount), flt(pi.rounded_total + pi.total_advance))

	def test_purchase_invoice_with_shipping_rule(self):
		from erpnext.accounts.doctype.shipping_rule.test_shipping_rule import create_shipping_rule

		shipping_rule = create_shipping_rule(
			shipping_rule_type="Buying", shipping_rule_name="Shipping Rule - Purchase Invoice Test"
		)

		pi = frappe.copy_doc(test_records[0])

		pi.shipping_rule = shipping_rule.name
		pi.insert(ignore_permissions=True)
		pi.save()

		self.assertEqual(pi.net_total, 1250)

		self.assertEqual(pi.total_taxes_and_charges, 354.1)
		self.assertEqual(pi.grand_total, 1604.1)

	def test_make_pi_without_terms(self):
		pi = make_purchase_invoice(do_not_save=1)

		self.assertFalse(pi.get("payment_schedule"))

		pi.insert(ignore_permissions=True)

		self.assertTrue(pi.get("payment_schedule"))

	def test_duplicate_due_date_in_terms(self):
		pi = make_purchase_invoice(do_not_save=1)
		pi.append("payment_schedule", dict(due_date="2017-01-01", invoice_portion=50.00, payment_amount=50))
		pi.append("payment_schedule", dict(due_date="2017-01-01", invoice_portion=50.00, payment_amount=50))

		self.assertRaises(frappe.ValidationError, pi.insert)

	def test_debit_note(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import get_outstanding_amount

		pi = make_purchase_invoice(item_code="_Test Item", qty=(5 * -1), rate=500, is_return=1)
		pi.load_from_db()
		self.assertTrue(pi.status, "Return")

		outstanding_amount = get_outstanding_amount(
			pi.doctype, pi.name, "Creditors - _TC", pi.supplier, "Supplier"
		)

		self.assertEqual(pi.outstanding_amount, outstanding_amount)

		pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="_Test Bank - _TC")
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = pi.currency
		pe.paid_to_account_currency = pi.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.paid_amount = pi.grand_total * -1
		pe.insert(ignore_permissions=True)
		pe.submit()

		pi_doc = frappe.get_doc("Purchase Invoice", pi.name)
		self.assertEqual(pi_doc.outstanding_amount, 0)

	def test_purchase_invoice_with_cost_center(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center

		cost_center = "_Test Cost Center for BS Account - _TC"
		create_cost_center(cost_center_name="_Test Cost Center for BS Account", company="_Test Company")

		pi = make_purchase_invoice_against_cost_center(cost_center=cost_center, credit_to="Creditors - _TC")
		self.assertEqual(pi.cost_center, cost_center)

		expected_values = {
			"Creditors - _TC": {"cost_center": cost_center},
			"_Test Account Cost for Goods Sold - _TC": {"cost_center": cost_center},
		}

		gl_entries = frappe.db.sql(
			"""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""",
			pi.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_purchase_invoice_without_cost_center(self):
		cost_center = "_Test Cost Center - _TC"
		pi = make_purchase_invoice(credit_to="Creditors - _TC")

		expected_values = {
			"Creditors - _TC": {"cost_center": None},
			"_Test Account Cost for Goods Sold - _TC": {"cost_center": cost_center},
		}

		gl_entries = frappe.db.sql(
			"""select account, cost_center, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""",
			pi.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["cost_center"], gle.cost_center)

	def test_deferred_expense_via_journal_entry(self):
		deferred_account = create_account(
			account_name="Deferred Expense", parent_account="Current Assets - _TC", company="_Test Company"
		)

		acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		acc_settings.book_deferred_entries_via_journal_entry = 1
		acc_settings.submit_journal_entries = 1
		acc_settings.save()

		item = create_item("_Test Item for Deferred Accounting", is_purchase_item=True)
		item.enable_deferred_expense = 1
		item.item_defaults[0].deferred_expense_account = deferred_account
		item.save()

		pi = make_purchase_invoice(item=item.name, qty=1, rate=100, do_not_save=True)
		pi.set_posting_time = 1
		pi.posting_date = "2019-01-10"
		pi.items[0].enable_deferred_expense = 1
		pi.items[0].service_start_date = "2019-01-10"
		pi.items[0].service_end_date = "2019-03-15"
		pi.items[0].deferred_expense_account = deferred_account
		pi.save()
		pi.submit()

		pda1 = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2019-01-01",
				end_date="2019-03-31",
				type="Expense",
				company="_Test Company",
			)
		)

		pda1.insert()
		pda1.submit()

		expected_gle = [
			["_Test Account Cost for Goods Sold - _TC", 0.0, 33.85, "2019-01-31"],
			[deferred_account, 33.85, 0.0, "2019-01-31"],
			["_Test Account Cost for Goods Sold - _TC", 0.0, 43.08, "2019-02-28"],
			[deferred_account, 43.08, 0.0, "2019-02-28"],
			["_Test Account Cost for Goods Sold - _TC", 0.0, 23.07, "2019-03-15"],
			[deferred_account, 23.07, 0.0, "2019-03-15"],
		]

		gl_entries = gl_entries = frappe.db.sql(
			"""select account, debit, credit, posting_date
			from `tabGL Entry`
			where voucher_type='Journal Entry' and voucher_detail_no=%s and posting_date <= %s
			order by posting_date asc, account asc""",
			(pi.items[0].name, pi.posting_date),
			as_dict=1,
		)

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gle[i][0], gle.account)
			self.assertEqual(expected_gle[i][1], gle.credit)
			self.assertEqual(expected_gle[i][2], gle.debit)
			self.assertEqual(getdate(expected_gle[i][3]), gle.posting_date)

		acc_settings = frappe.get_doc("Accounts Settings", "Accounts Settings")
		acc_settings.book_deferred_entries_via_journal_entry = 0
		acc_settings.submit_journal_entriessubmit_journal_entries = 0
		acc_settings.save()

	@change_settings("Accounts Settings", {"unlink_payment_on_cancellation_of_invoice": 1})
	def test_gain_loss_with_advance_entry(self):
		unlink_enabled = frappe.db.get_single_value(
			"Accounts Settings", "unlink_payment_on_cancellation_of_invoice"
		)

		frappe.db.set_single_value("Accounts Settings", "unlink_payment_on_cancellation_of_invoice", 1)

		original_account = frappe.db.get_value("Company", "_Test Company", "exchange_gain_loss_account")
		frappe.db.set_value(
			"Company", "_Test Company", "exchange_gain_loss_account", "Exchange Gain/Loss - _TC"
		)

		pay = frappe.get_doc(
			{
				"doctype": "Payment Entry",
				"company": "_Test Company",
				"payment_type": "Pay",
				"party_type": "Supplier",
				"party": "_Test Supplier USD",
				"paid_to": "_Test Payable USD - _TC",
				"paid_from": "Cash - _TC",
				"paid_amount": 70000,
				"target_exchange_rate": 70,
				"received_amount": 1000,
			}
		)
		pay.insert()
		pay.submit()

		pi = make_purchase_invoice(
			supplier="_Test Supplier USD",
			currency="USD",
			conversion_rate=75,
			rate=500,
			do_not_save=1,
			qty=1,
		)
		pi.cost_center = "_Test Cost Center - _TC"
		pi.advances = []
		pi.append(
			"advances",
			{
				"reference_type": "Payment Entry",
				"reference_name": pay.name,
				"advance_amount": 1000,
				"remarks": pay.remarks,
				"allocated_amount": 500,
				"ref_exchange_rate": 70,
			},
		)
		pi.save()
		pi.submit()

		creditors_account = pi.credit_to

		expected_gle = [
			["_Test Account Cost for Goods Sold - _TC", 37500.0],
			["_Test Payable USD - _TC", -37500.0],
		]

		gl_entries = frappe.db.sql(
			"""
			select account, sum(debit - credit) as balance from `tabGL Entry`
			where voucher_no=%s
			group by account
			order by account asc""",
			(pi.name),
			as_dict=1,
		)

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gle[i][0], gle.account)
			self.assertEqual(expected_gle[i][1], gle.balance)

		pi.reload()
		self.assertEqual(pi.outstanding_amount, 0)

		total_debit_amount = frappe.db.get_all(
			"Journal Entry Account",
			{"account": creditors_account, "docstatus": 1, "reference_name": pi.name},
			"sum(debit) as amount",
			group_by="reference_name",
		)[0].amount
		self.assertEqual(flt(total_debit_amount, 2), 2500)
		jea_parent = frappe.db.get_all(
			"Journal Entry Account",
			filters={
				"account": creditors_account,
				"docstatus": 1,
				"reference_name": pi.name,
				"debit": 2500,
				"debit_in_account_currency": 0,
			},
			fields=["parent"],
		)[0]
		self.assertEqual(
			frappe.db.get_value("Journal Entry", jea_parent.parent, "voucher_type"), "Exchange Gain Or Loss"
		)

		pi_2 = make_purchase_invoice(
			supplier="_Test Supplier USD",
			currency="USD",
			conversion_rate=73,
			rate=500,
			do_not_save=1,
			qty=1,
		)
		pi_2.cost_center = "_Test Cost Center - _TC"
		pi_2.advances = []
		pi_2.append(
			"advances",
			{
				"reference_type": "Payment Entry",
				"reference_name": pay.name,
				"advance_amount": 500,
				"remarks": pay.remarks,
				"allocated_amount": 500,
				"ref_exchange_rate": 70,
			},
		)
		pi_2.save()
		pi_2.submit()

		pi_2.reload()
		self.assertEqual(pi_2.outstanding_amount, 0)

		expected_gle = [
			["_Test Account Cost for Goods Sold - _TC", 36500.0],
			["_Test Payable USD - _TC", -36500.0],
		]

		gl_entries = frappe.db.sql(
			"""
			select account, sum(debit - credit) as balance from `tabGL Entry`
			where voucher_no=%s
			group by account order by account asc""",
			(pi_2.name),
			as_dict=1,
		)

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gle[i][0], gle.account)
			self.assertEqual(expected_gle[i][1], gle.balance)
		if frappe.db.db_type == "postgres":
			expected_gle = [["Cash - _TC", -70000.0], ["_Test Payable USD - _TC", 70000.0]]
		else:
			expected_gle = [["_Test Payable USD - _TC", 70000.0], ["Cash - _TC", -70000.0]]

		gl_entries = frappe.db.sql(
			"""
			select account, sum(debit - credit) as balance from `tabGL Entry`
			where voucher_no=%s and is_cancelled=0
			group by account order by account asc""",
			(pay.name),
			as_dict=1,
		)

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gle[i][0], gle.account)
			self.assertEqual(expected_gle[i][1], gle.balance)

		total_debit_amount = frappe.db.get_all(
			"Journal Entry Account",
			{"account": creditors_account, "docstatus": 1, "reference_name": pi_2.name},
			"sum(debit) as amount",
			group_by="reference_name",
		)[0].amount
		self.assertEqual(flt(total_debit_amount, 2), 1500)
		jea_parent_2 = frappe.db.get_all(
			"Journal Entry Account",
			filters={
				"account": creditors_account,
				"docstatus": 1,
				"reference_name": pi_2.name,
				"debit": 1500,
				"debit_in_account_currency": 0,
			},
			fields=["parent"],
		)[0]
		self.assertEqual(
			frappe.db.get_value("Journal Entry", jea_parent_2.parent, "voucher_type"),
			"Exchange Gain Or Loss",
		)

		pi.reload()
		pi.cancel()

		self.assertEqual(frappe.db.get_value("Journal Entry", jea_parent.parent, "docstatus"), 2)

		pi_2.reload()
		pi_2.cancel()

		self.assertEqual(frappe.db.get_value("Journal Entry", jea_parent_2.parent, "docstatus"), 2)

		pay.reload()
		pay.cancel()

		frappe.db.set_single_value(
			"Accounts Settings", "unlink_payment_on_cancellation_of_invoice", unlink_enabled
		)
		frappe.db.set_value("Company", "_Test Company", "exchange_gain_loss_account", original_account)

	@change_settings("Accounts Settings", {"unlink_payment_on_cancellation_of_invoice": 1})
	def test_purchase_invoice_advance_taxes(self):
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		company = "_Test Company"

		tds_account_args = {
			"doctype": "Account",
			"account_name": "TDS Payable",
			"account_type": "Tax",
			"parent_account": frappe.db.get_value(
				"Account", {"account_name": "Duties and Taxes", "company": company}
			),
			"company": company,
		}

		tds_account = create_account(**tds_account_args)
		tax_withholding_category = "Test TDS - 194 - Dividends - Individual"

		# Update tax withholding category with current fiscal year and rate details
		create_tax_witholding_category(tax_withholding_category, company, tds_account)

		# create a new supplier to test
		supplier = create_supplier(
			supplier_name="_Test TDS Advance Supplier",
			tax_withholding_category=tax_withholding_category,
		)

		# Create Purchase Order with TDS applied
		po = create_purchase_order(
			do_not_save=1,
			supplier=supplier.name,
			rate=3000,
			item="_Test Non Stock Item",
			posting_date="2021-09-15",
		)
		po.save()
		po.submit()

		# Create Payment Entry Against the order
		payment_entry = get_payment_entry(dt="Purchase Order", dn=po.name)
		payment_entry.paid_from = "Cash - _TC"
		payment_entry.apply_tax_withholding_amount = 1
		payment_entry.tax_withholding_category = tax_withholding_category
		payment_entry.save()
		payment_entry.submit()

		# Check GLE for Payment Entry
		expected_gle = [
			["Cash - _TC", 0, 27000],
			["Creditors - _TC", 30000, 0],
			[tds_account, 0, 3000],
		]

		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry`
			where voucher_type='Payment Entry' and voucher_no=%s
			order by account asc""",
			(payment_entry.name),
			as_dict=1,
		)

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gle[i][0], gle.account)
			self.assertEqual(expected_gle[i][1], gle.debit)
			self.assertEqual(expected_gle[i][2], gle.credit)

		# Create Purchase Invoice against Purchase Order
		purchase_invoice = get_mapped_purchase_invoice(po.name)
		purchase_invoice.allocate_advances_automatically = 1
		purchase_invoice.items[0].item_code = "_Test Non Stock Item"
		purchase_invoice.items[0].expense_account = "_Test Account Cost for Goods Sold - _TC"
		purchase_invoice.save()
		purchase_invoice.submit()

		# Check GLE for Purchase Invoice
		# Zero net effect on final TDS payable on invoice
		if frappe.db.db_type == "postgres":
			expected_gle = [["Creditors - _TC", -30000], ["_Test Account Cost for Goods Sold - _TC", 30000]]
		else:
			expected_gle = [["_Test Account Cost for Goods Sold - _TC", 30000], ["Creditors - _TC", -30000]]

		gl_entries = frappe.db.sql(
			"""select account, sum(debit - credit) as amount
			from `tabGL Entry`
			where voucher_type='Purchase Invoice' and voucher_no=%s
			group by account
			order by account asc""",
			(purchase_invoice.name),
			as_dict=1,
		)

		for i, gle in enumerate(gl_entries):
			self.assertEqual(expected_gle[i][0], gle.account)
			self.assertEqual(expected_gle[i][1], gle.amount)

		payment_entry.load_from_db()
		self.assertEqual(payment_entry.taxes[0].allocated_amount, 3000)

		purchase_invoice.cancel()

		payment_entry.load_from_db()
		self.assertEqual(payment_entry.taxes[0].allocated_amount, 0)

	def test_provisional_accounting_entry(self):
		setup_provisional_accounting()

		pr = make_purchase_receipt(item_code="_Test Non Stock Item", posting_date=add_days(nowdate(), -2))

		pi = create_purchase_invoice_from_receipt(pr.name)
		pi.set_posting_time = 1
		pi.posting_date = add_days(pr.posting_date, 1)
		pi.items[0].expense_account = "Cost of Goods Sold - _TC"
		pi.save()
		pi.submit()

		self.assertEqual(pr.items[0].provisional_expense_account, "Provision Account - _TC")

		# Check GLE for Purchase Invoice
		expected_gle = [
			["Cost of Goods Sold - _TC", 250, 0, add_days(pr.posting_date, 1)],
			["Creditors - _TC", 0, 250, add_days(pr.posting_date, 1)],
		]

		check_gl_entries(self, pi.name, expected_gle, pi.posting_date)

		expected_gle_for_purchase_receipt = [
			["Provision Account - _TC", 250, 0, pr.posting_date],
			["_Test Account Cost for Goods Sold - _TC", 0, 250, pr.posting_date],
			["Provision Account - _TC", 0, 250, pi.posting_date],
			["_Test Account Cost for Goods Sold - _TC", 250, 0, pi.posting_date],
		]

		check_gl_entries(self, pr.name, expected_gle_for_purchase_receipt, pr.posting_date)

		# Cancel purchase invoice to check reverse provisional entry cancellation
		pi.cancel()

		expected_gle_for_purchase_receipt_post_pi_cancel = [
			["Provision Account - _TC", 0, 250, pi.posting_date],
			["_Test Account Cost for Goods Sold - _TC", 250, 0, pi.posting_date],
		]

		check_gl_entries(self, pr.name, expected_gle_for_purchase_receipt_post_pi_cancel, pr.posting_date)

		toggle_provisional_accounting_setting()

	def test_provisional_accounting_entry_for_over_billing(self):
		setup_provisional_accounting()

		# Configure Buying Settings to allow rate change
		frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 0)

		# Configure Accounts Settings to allow 300% over billingAdd commentMore actions
		frappe.db.set_single_value("Accounts Settings", "over_billing_allowance", 300)

		# Create PR: rate = 1000, qty = 5
		pr = make_purchase_receipt(
			item_code="_Test Non Stock Item", rate=1000, posting_date=add_days(nowdate(), -2)
		)

		# Overbill PR: rate = 2000, qty = 10
		pi = create_purchase_invoice_from_receipt(pr.name)
		pi.set_posting_time = 1
		pi.posting_date = add_days(pr.posting_date, -1)
		pi.items[0].qty = 10
		pi.items[0].rate = 2000
		pi.items[0].expense_account = "Cost of Goods Sold - _TC"
		pi.save()
		pi.submit()

		expected_gle = [
			["Cost of Goods Sold - _TC", 20000, 0, add_days(pr.posting_date, -1)],
			["Creditors - _TC", 0, 20000, add_days(pr.posting_date, -1)],
		]

		check_gl_entries(self, pi.name, expected_gle, pi.posting_date)

		expected_gle_for_purchase_receipt = [
			["Provision Account - _TC", 5000, 0, pr.posting_date],
			["_Test Account Cost for Goods Sold - _TC", 0, 5000, pr.posting_date],
			["Provision Account - _TC", 0, 5000, pi.posting_date],
			["_Test Account Cost for Goods Sold - _TC", 5000, 0, pi.posting_date],
		]

		check_gl_entries(self, pr.name, expected_gle_for_purchase_receipt, pr.posting_date)

		# Cancel purchase invoice to check reverse provisional entry cancellation
		pi.cancel()

		expected_gle_for_purchase_receipt_post_pi_cancel = [
			["Provision Account - _TC", 0, 5000, pi.posting_date],
			["_Test Account Cost for Goods Sold - _TC", 5000, 0, pi.posting_date],
		]

		check_gl_entries(self, pr.name, expected_gle_for_purchase_receipt_post_pi_cancel, pr.posting_date)

		toggle_provisional_accounting_setting()

	def test_provisional_accounting_entry_for_partial_billing(self):
		setup_provisional_accounting()

		# Configure Buying Settings to allow rate change
		frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 0)

		# Create PR: rate = 1000, qty = 5
		pr = make_purchase_receipt(
			item_code="_Test Non Stock Item", rate=1000, posting_date=add_days(nowdate(), -2)
		)

		# Partially bill PR: rate = 500, qty = 2
		pi = create_purchase_invoice_from_receipt(pr.name)
		pi.set_posting_time = 1
		pi.posting_date = add_days(pr.posting_date, -1)
		pi.items[0].qty = 2
		pi.items[0].rate = 500
		pi.items[0].expense_account = "Cost of Goods Sold - _TC"
		pi.save()
		pi.submit()

		expected_gle = [
			["Cost of Goods Sold - _TC", 1000, 0, add_days(pr.posting_date, -1)],
			["Creditors - _TC", 0, 1000, add_days(pr.posting_date, -1)],
		]

		check_gl_entries(self, pi.name, expected_gle, pi.posting_date)

		expected_gle_for_purchase_receipt = [
			["Provision Account - _TC", 5000, 0, pr.posting_date],
			["_Test Account Cost for Goods Sold - _TC", 0, 5000, pr.posting_date],
			["Provision Account - _TC", 0, 1000, pi.posting_date],
			["_Test Account Cost for Goods Sold - _TC", 1000, 0, pi.posting_date],
		]

		check_gl_entries(self, pr.name, expected_gle_for_purchase_receipt, pr.posting_date)

		toggle_provisional_accounting_setting()

	def test_adjust_incoming_rate(self):
		frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 0)

		frappe.db.set_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate", 1)

		# Cost of Item is zero in Purchase Receipt
		pr = make_purchase_receipt(qty=1, rate=0)
		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"stock_value_difference",
		)
		self.assertEqual(stock_value_difference, 0)
		pi = create_purchase_invoice_from_receipt(pr.name)
		for row in pi.items:
			row.rate = 150
		pi.save()
		pi.submit()
		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"stock_value_difference",
		)
		self.assertEqual(stock_value_difference, 150)

		# Increase the cost of the item

		pr = make_purchase_receipt(qty=1, rate=100)

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"stock_value_difference",
		)
		self.assertEqual(stock_value_difference, 100)

		pi = create_purchase_invoice_from_receipt(pr.name)
		for row in pi.items:
			row.rate = 150

		pi.save()
		pi.submit()

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"stock_value_difference",
		)
		self.assertEqual(stock_value_difference, 150)

		# Reduce the cost of the item

		pr = make_purchase_receipt(qty=1, rate=100)

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"stock_value_difference",
		)
		self.assertEqual(stock_value_difference, 100)

		pi = create_purchase_invoice_from_receipt(pr.name)
		for row in pi.items:
			row.rate = 50

		pi.save()
		pi.submit()

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"stock_value_difference",
		)
		self.assertEqual(stock_value_difference, 50)

		frappe.db.set_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate", 0)

		# Don't adjust incoming rate

		pr = make_purchase_receipt(qty=1, rate=100)

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"stock_value_difference",
		)
		self.assertEqual(stock_value_difference, 100)

		pi = create_purchase_invoice_from_receipt(pr.name)
		for row in pi.items:
			row.rate = 50

		pi.save()
		pi.submit()

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"stock_value_difference",
		)
		self.assertEqual(stock_value_difference, 100)

		frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 1)

	def test_item_less_defaults(self):
		pi = frappe.new_doc("Purchase Invoice")
		pi.supplier = "_Test Supplier"
		pi.company = "_Test Company"
		pi.append(
			"items",
			{
				"item_name": "Opening item",
				"qty": 1,
				"uom": "Tonne",
				"stock_uom": "Kg",
				"rate": 1000,
				"expense_account": "Stock Received But Not Billed - _TC",
			},
		)

		pi.save()
		self.assertEqual(pi.items[0].conversion_factor, 1000)

	def test_batch_expiry_for_purchase_invoice(self):
		from erpnext.controllers.sales_and_purchase_return import make_return_doc

		item = self.make_item(
			"_Test Batch Item For Return Check",
			{
				"is_purchase_item": 1,
				"is_stock_item": 1,
				"has_batch_no": 1,
				"create_new_batch": 1,
				"batch_number_series": "TBIRC.#####",
			},
		)

		pi = make_purchase_invoice(
			qty=1,
			item_code=item.name,
			update_stock=True,
		)

		pi.load_from_db()
		batch_no = get_batch_from_bundle(pi.items[0].serial_and_batch_bundle)
		self.assertTrue(batch_no)

		frappe.db.set_value("Batch", batch_no, "expiry_date", add_days(nowdate(), -1))

		return_pi = make_return_doc(pi.doctype, pi.name)
		return_pi.save().submit()

		self.assertTrue(return_pi.docstatus == 1)

	def test_advance_entries_as_asset(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

		account = create_account(
			parent_account="Current Assets - _TC",
			account_name="Advances Paid",
			company="_Test Company",
			account_type="Receivable",
		)

		set_advance_flag(company="_Test Company", flag=1, default_account=account)

		pe = create_payment_entry(
			company="_Test Company",
			payment_type="Pay",
			party_type="Supplier",
			party="_Test Supplier",
			paid_from="Cash - _TC",
			paid_to="Creditors - _TC",
			paid_amount=500,
		)
		pe.save()  # save trigger is needed for set_liability_account() to be executed
		pe.submit()

		pi = make_purchase_invoice(
			company="_Test Company",
			do_not_save=True,
			do_not_submit=True,
			rate=1000,
			price_list_rate=1000,
			qty=1,
		)
		pi.base_grand_total = 1000
		pi.grand_total = 1000
		pi.set_advances()
		for advance in pi.advances:
			advance.allocated_amount = 500 if advance.reference_name == pe.name else 0
		pi.save()
		pi.submit()

		self.assertEqual(pi.advances[0].allocated_amount, 500)

		# Check GL Entry against payment doctype
		expected_gle = [
			["Advances Paid - _TC", 500.0, 0.0, nowdate()],
			["Advances Paid - _TC", 0.0, 500.0, nowdate()],
			["Cash - _TC", 0.0, 500, nowdate()],
			["Creditors - _TC", 500, 0.0, nowdate()],
		]

		check_gl_entries(self, pe.name, expected_gle, nowdate(), voucher_type="Payment Entry")

		pi.load_from_db()
		self.assertEqual(pi.outstanding_amount, 500)

		set_advance_flag(company="_Test Company", flag=0, default_account="")

	def test_gl_entries_for_standalone_debit_note(self):
		from erpnext.stock.doctype.item.test_item import make_item

		item_code = make_item(properties={"is_stock_item": 1})
		make_purchase_invoice(item_code=item_code, qty=5, rate=500, update_stock=True)

		returned_inv = make_purchase_invoice(
			item_code=item_code, qty=-5, rate=5, update_stock=True, is_return=True
		)

		# override the rate with valuation rate
		sle = frappe.get_all(
			"Stock Ledger Entry",
			fields=["stock_value_difference", "actual_qty"],
			filters={"voucher_no": returned_inv.name},
		)[0]

		rate = flt(sle.stock_value_difference) / flt(sle.actual_qty)
		self.assertAlmostEqual(rate, 500)

	def test_payment_allocation_for_payment_terms(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import (
			create_pr_against_po,
			create_purchase_order,
		)
		from erpnext.selling.doctype.sales_order.test_sales_order import (
			automatically_fetch_payment_terms,
		)
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_invoice as make_pi_from_pr,
		)

		automatically_fetch_payment_terms()
		frappe.db.set_value(
			"Payment Terms Template",
			"_Test Payment Term Template",
			"allocate_payment_based_on_payment_terms",
			0,
		)

		po = create_purchase_order(do_not_save=1)
		po.payment_terms_template = "_Test Payment Term Template"
		po.save()
		po.submit()

		pr = create_pr_against_po(po.name, received_qty=4)
		pi = make_pi_from_pr(pr.name)
		self.assertEqual(pi.payment_schedule[0].payment_amount, 1000)

		frappe.db.set_value(
			"Payment Terms Template",
			"_Test Payment Term Template",
			"allocate_payment_based_on_payment_terms",
			1,
		)
		pi = make_pi_from_pr(pr.name)
		self.assertEqual(pi.payment_schedule[0].payment_amount, 1000)

		automatically_fetch_payment_terms(enable=0)
		frappe.db.set_value(
			"Payment Terms Template",
			"_Test Payment Term Template",
			"allocate_payment_based_on_payment_terms",
			0,
		)

	def test_offsetting_entries_for_accounting_dimensions(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.report.trial_balance.test_trial_balance import (
			clear_dimension_defaults,
			create_accounting_dimension,
			disable_dimension,
		)

		create_account(
			account_name="Offsetting",
			company="_Test Company",
			parent_account="Temporary Accounts - _TC",
		)

		create_accounting_dimension(company="_Test Company", offsetting_account="Offsetting - _TC")

		branch1 = frappe.new_doc("Branch")
		branch1.branch = "Location 1"
		branch1.insert(ignore_if_duplicate=True)
		branch2 = frappe.new_doc("Branch")
		branch2.branch = "Location 2"
		branch2.insert(ignore_if_duplicate=True)

		pi = make_purchase_invoice(
			company="_Test Company",
			do_not_save=True,
			do_not_submit=True,
			rate=1000,
			price_list_rate=1000,
			qty=1,
		)
		pi.branch = branch1.branch
		pi.items[0].branch = branch2.branch
		pi.save()
		pi.submit()

		expected_gle = [
			["Creditors - _TC", 0.0, 1000, nowdate(), branch1.branch],
			["Offsetting - _TC", 1000, 0.0, nowdate(), branch1.branch],
			["Offsetting - _TC", 0.0, 1000, nowdate(), branch2.branch],
			["_Test Account Cost for Goods Sold - _TC", 1000, 0.0, nowdate(), branch2.branch],
		]

		check_gl_entries(
			self,
			pi.name,
			expected_gle,
			nowdate(),
			voucher_type="Purchase Invoice",
			additional_columns=["branch"],
		)
		clear_dimension_defaults("Branch")
		disable_dimension()

	def test_repost_accounting_entries(self):
		# update repost settings
		settings = frappe.get_doc("Repost Accounting Ledger Settings")
		if not [x for x in settings.allowed_types if x.document_type == "Purchase Invoice"]:
			settings.append("allowed_types", {"document_type": "Purchase Invoice", "allowed": True})
		settings.save()

		pi = make_purchase_invoice(
			rate=1000,
			price_list_rate=1000,
			qty=1,
		)
		if frappe.db.db_type == "postgres":
			expected_gle = [
				["Creditors - _TC", 0.0, 1000, nowdate()],
				["_Test Account Cost for Goods Sold - _TC", 1000, 0.0, nowdate()],
			]
		else:
			expected_gle = [
				["_Test Account Cost for Goods Sold - _TC", 1000, 0.0, nowdate()],
				["Creditors - _TC", 0.0, 1000, nowdate()],
			]
		check_gl_entries(self, pi.name, expected_gle, nowdate())

		pi.items[0].expense_account = "Service - _TC"
		# Ledger reposted implicitly upon 'Update After Submit'
		pi.save()
		pi.load_from_db()

		expected_gle = [
			["Creditors - _TC", 0.0, 1000, nowdate()],
			["Service - _TC", 1000, 0.0, nowdate()],
		]
		check_gl_entries(self, pi.name, expected_gle, nowdate())

	@change_settings("Buying Settings", {"supplier_group": None})
	def test_purchase_invoice_without_supplier_group(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		# Create a Supplier
		test_supplier_name = "_Test Supplier Without Supplier Group"
		if not frappe.db.exists("Supplier", test_supplier_name):
			supplier = frappe.get_doc(
				{
					"doctype": "Supplier",
					"supplier_name": test_supplier_name,
				}
			).insert(ignore_permissions=True)

			self.assertEqual(supplier.supplier_group, None)

		po = create_purchase_order(
			supplier=test_supplier_name,
			rate=3000,
			item="_Test Non Stock Item",
			posting_date="2021-09-15",
		)

		pi = make_purchase_invoice(supplier=test_supplier_name)

		self.assertEqual(po.docstatus, 1)
		self.assertEqual(pi.docstatus, 1)

	def test_default_cost_center_for_purchase(self):
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center

		for c_center in ["_Test Cost Center Selling", "_Test Cost Center Buying"]:
			create_cost_center(cost_center_name=c_center)

		item = create_item(
			"_Test Cost Center Item For Purchase",
			is_stock_item=1,
			buying_cost_center="_Test Cost Center Buying - _TC",
			selling_cost_center="_Test Cost Center Selling - _TC",
		)

		pi = make_purchase_invoice(
			item=item.name, qty=1, rate=1000, update_stock=True, do_not_submit=True, cost_center=""
		)

		pi.items[0].cost_center = ""
		pi.set_missing_values()
		pi.calculate_taxes_and_totals()
		pi.save()

		self.assertEqual(pi.items[0].cost_center, "_Test Cost Center Buying - _TC")

	def test_debit_note_with_account_mismatch(self):
		new_creditors = create_account(
			parent_account="Accounts Payable - _TC",
			account_name="Creditors 2",
			company="_Test Company",
			account_type="Payable",
		)
		pi = make_purchase_invoice(qty=1, rate=1000)
		dr_note = make_purchase_invoice(
			qty=-1, rate=1000, is_return=1, return_against=pi.name, do_not_save=True
		)
		dr_note.credit_to = new_creditors

		self.assertRaises(frappe.ValidationError, dr_note.save)

	def test_debit_note_without_item(self):
		pi = make_purchase_invoice(item_name="_Test Item", qty=10, do_not_submit=True)
		pi.items[0].item_code = ""
		pi.save()

		self.assertFalse(pi.items[0].item_code)
		pi.submit()

		return_pi = make_purchase_invoice(
			item_name="_Test Item",
			is_return=1,
			return_against=pi.name,
			qty=-10,
			do_not_save=True,
		)
		return_pi.items[0].item_code = ""
		return_pi.save()
		return_pi.submit()
		self.assertEqual(return_pi.docstatus, 1)

	def test_purchase_invoice_with_use_serial_batch_field_for_rejected_qty(self):
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.doctype.warehouse.test_warehouse import create_warehouse

		batch_item = make_item(
			"_Test Purchase Invoice Batch Item For Rejected Qty",
			properties={"has_batch_no": 1, "create_new_batch": 1, "is_stock_item": 1},
		).name

		serial_item = make_item(
			"_Test Purchase Invoice Serial Item for Rejected Qty",
			properties={"has_serial_no": 1, "is_stock_item": 1},
		).name

		rej_warehouse = create_warehouse("_Test Purchase INV Warehouse For Rejected Qty")

		batch_no = "BATCH-PI-BNU-TPRBI-0001"
		serial_nos = ["SNU-PI-TPRSI-0001", "SNU-PI-TPRSI-0002", "SNU-PI-TPRSI-0003"]

		if not frappe.db.exists("Batch", batch_no):
			frappe.get_doc(
				{
					"doctype": "Batch",
					"batch_id": batch_no,
					"item": batch_item,
				}
			).insert()

		for serial_no in serial_nos:
			if not frappe.db.exists("Serial No", serial_no):
				frappe.get_doc(
					{
						"doctype": "Serial No",
						"item_code": serial_item,
						"serial_no": serial_no,
					}
				).insert()

		pi = make_purchase_invoice(
			item_code=batch_item,
			received_qty=10,
			qty=8,
			rejected_qty=2,
			update_stock=1,
			rejected_warehouse=rej_warehouse,
			use_serial_batch_fields=1,
			batch_no=batch_no,
			rate=100,
			do_not_submit=1,
		)

		pi.append(
			"items",
			{
				"item_code": serial_item,
				"qty": 2,
				"rate": 100,
				"base_rate": 100,
				"item_name": serial_item,
				"uom": "Nos",
				"stock_uom": "Nos",
				"conversion_factor": 1,
				"rejected_qty": 1,
				"warehouse": pi.items[0].warehouse,
				"rejected_warehouse": rej_warehouse,
				"use_serial_batch_fields": 1,
				"serial_no": "\n".join(serial_nos[:2]),
				"rejected_serial_no": serial_nos[2],
			},
		)

		pi.save()
		pi.submit()

		pi.reload()

		for row in pi.items:
			self.assertTrue(row.serial_and_batch_bundle)
			self.assertTrue(row.rejected_serial_and_batch_bundle)

			if row.item_code == batch_item:
				self.assertEqual(row.batch_no, batch_no)
			else:
				self.assertEqual(row.serial_no, "\n".join(serial_nos[:2]))
				self.assertEqual(row.rejected_serial_no, serial_nos[2])

	def test_adjust_incoming_rate_from_pi_with_multi_currency(self):
		from erpnext.stock.doctype.landed_cost_voucher.test_landed_cost_voucher import (
			make_landed_cost_voucher,
		)

		frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 0)

		frappe.db.set_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate", 1)

		# Increase the cost of the item

		pr = make_purchase_receipt(
			qty=10, rate=1, currency="USD", do_not_save=1, supplier="_Test Supplier USD"
		)
		pr.conversion_rate = 6300
		pr.plc_conversion_rate = 1
		pr.save()
		pr.submit()

		self.assertEqual(pr.conversion_rate, 6300)
		self.assertEqual(pr.plc_conversion_rate, 1)
		self.assertEqual(pr.base_grand_total, 6300 * 10)

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"stock_value_difference",
		)
		self.assertEqual(stock_value_difference, 6300 * 10)

		make_landed_cost_voucher(
			company=pr.company,
			receipt_document_type="Purchase Receipt",
			receipt_document=pr.name,
			charges=3000,
			distribute_charges_based_on="Qty",
		)

		pi = create_purchase_invoice_from_receipt(pr.name)
		for row in pi.items:
			row.rate = 1.1

		pi.save()
		pi.submit()

		stock_value_difference = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"stock_value_difference",
		)
		self.assertEqual(stock_value_difference, 7230 * 10)

		frappe.db.set_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate", 0)

		frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 1)

	def test_last_purchase_rate(self):
		item = create_item("_Test Item For Last Purchase Rate from PI", is_stock_item=1)
		pi1 = make_purchase_invoice(item_code=item.item_code, qty=10, rate=100)
		item.reload()
		self.assertEqual(item.last_purchase_rate, 100)
		pi2 = make_purchase_invoice(item_code=item.item_code, qty=10, rate=200)
		item.reload()
		self.assertEqual(item.last_purchase_rate, 200)
		pi2.cancel()
		item.reload()
		self.assertEqual(item.last_purchase_rate, 100)
		pi1.cancel()
		item.reload()
		self.assertEqual(item.last_purchase_rate, 0)

	def test_adjust_incoming_rate_from_pi_with_multi_currency_and_partial_billing(self):
		frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 0)

		frappe.db.set_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate", 1)

		pr = make_purchase_receipt(
			qty=10, rate=10, currency="USD", do_not_save=1, supplier="_Test Supplier USD"
		)
		pr.conversion_rate = 5300
		pr.save()
		pr.submit()

		incoming_rate = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"incoming_rate",
		)
		self.assertEqual(incoming_rate, 53000)  # Asserting to confirm if the default calculation is correct

		pi = create_purchase_invoice_from_receipt(pr.name)
		for row in pi.items:
			row.qty = 1

		pi.save()
		pi.submit()

		incoming_rate = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"incoming_rate",
		)
		# Test 1 : Incoming rate should not change as only the qty has changed and not the rate (this was not the case before)
		self.assertEqual(incoming_rate, 53000)

		pi = create_purchase_invoice_from_receipt(pr.name)
		for row in pi.items:
			row.qty = 1
			row.rate = 9

		pi.save()
		pi.submit()

		incoming_rate = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"incoming_rate",
		)
		# Test 2 : Rate in new PI is lower than PR, so incoming rate should also be lower
		self.assertEqual(incoming_rate, 50350)

		pi = create_purchase_invoice_from_receipt(pr.name)
		for row in pi.items:
			row.qty = 1
			row.rate = 12

		pi.save()
		pi.submit()

		incoming_rate = frappe.db.get_value(
			"Stock Ledger Entry",
			{"voucher_type": "Purchase Receipt", "voucher_no": pr.name},
			"incoming_rate",
		)
		# Test 3 : Rate in new PI is higher than PR, so incoming rate should also be higher
		self.assertEqual(incoming_rate, 54766.667)

		frappe.db.set_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate", 0)

		frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 1)

	def test_opening_invoice_rounding_adjustment_validation(self):
		pi = make_purchase_invoice(do_not_save=1)
		pi.items[0].rate = 99.98
		pi.items[0].qty = 1
		pi.items[0].expense_account = "Temporary Opening - _TC"
		pi.is_opening = "Yes"
		pi.save()
		self.assertRaises(frappe.ValidationError, pi.submit)

	def _create_opening_roundoff_account(self, company_name):
		liability_root = frappe.db.get_all(
			"Account",
			filters={"company": company_name, "root_type": "Liability", "disabled": 0},
			order_by="lft",
			limit=1,
		)[0]
		# setup round off account
		if acc := frappe.db.exists(
			"Account",
			{
				"account_name": "Round Off for Opening",
				"account_type": "Round Off for Opening",
				"company": company_name,
			},
		):
			frappe.db.set_value("Company", company_name, "round_off_for_opening", acc)
		else:
			acc = frappe.new_doc("Account")
			acc.company = company_name
			acc.parent_account = liability_root.name
			acc.account_name = "Round Off for Opening"
			acc.account_type = "Round Off for Opening"
			acc.save()
			frappe.db.set_value("Company", company_name, "round_off_for_opening", acc.name)

	def test_ledger_entries_of_opening_invoice_with_rounding_adjustment(self):
		pi = make_purchase_invoice(do_not_save=1)
		pi.items[0].rate = 99.98
		pi.items[0].qty = 1
		pi.items[0].expense_account = "Temporary Opening - _TC"
		pi.is_opening = "Yes"
		pi.save()
		self._create_opening_roundoff_account(pi.company)
		pi.submit()
		actual = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pi.name, "is_opening": "Yes", "is_cancelled": False},
			fields=["account", "debit", "credit", "is_opening"],
			order_by="account,debit",
		)
		expected = [
			{"account": "Creditors - _TC", "debit": 0.0, "credit": 100.0, "is_opening": "Yes"},
			{"account": "Round Off for Opening - _TC", "debit": 0.02, "credit": 0.0, "is_opening": "Yes"},
			{"account": "Temporary Opening - _TC", "debit": 99.98, "credit": 0.0, "is_opening": "Yes"},
		]
		self.assertEqual(len(actual), 3)
		self.assertEqual(expected, actual)

	def validate_ledger_entries(self, payment_entries, purchase_invoices):
		"""
		Validate GL entries for the given payment entries and purchase invoices.
		- payment_entries: A list of Payment Entry objects.
		- purchase_invoices: A list of Purchase Invoice objects.
		"""
		ledger_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": ["in", [pe.name for pe in payment_entries]]},
			fields=["account", "debit", "credit"],
		)

		# Validate debit entries for Creditors account
		creditor_account_debits = {}
		for entry in ledger_entries:
			if entry["account"] not in creditor_account_debits:
				creditor_account_debits[entry["account"]] = 0
			creditor_account_debits[entry["account"]] += entry["debit"]

		for pe in payment_entries:
			# Validate credit entries for Bank account
			credit_account, credit_amount = pe.paid_from, pe.paid_amount
			assert any(
				entry["account"] == credit_account and entry["credit"] == credit_amount
				for entry in ledger_entries
			), f"Credit entry missing for account: {credit_account} with amount: {credit_amount}"

		for pi in purchase_invoices:
			total_debit = sum(
				pe.paid_amount
				for pe in payment_entries
				if any(
					ref.reference_doctype == "Purchase Invoice" and ref.reference_name == pi.name
					for ref in pe.references
				)
			)
			debit_account, total_ledger_debit = pi.credit_to, creditor_account_debits.get(pi.credit_to, 0)
			assert total_ledger_debit == total_debit, (
				f"Total debit for Creditors account: {debit_account} should match total paid amount. "
				f"Total Ledger Debit: {total_ledger_debit}, Total Paid: {total_debit}"
			)

	def test_purchase_invoice_payment(self):
		"""Test payment against a single Purchase Invoice."""
		today = nowdate()

		# Step 1: Create and Submit Purchase Invoice
		purchase_invoice = make_purchase_invoice(
			supplier="_Test Supplier",
			company="_Test Company",
			item="_Test Item",
			qty=1,
			rate=100,
			warehouse="_Test Warehouse - _TC",
			currency="INR",
			naming_series="T-PINV-",
		)

		# Step 2: Create Payment Entry
		payment_entry = get_payment_entry(
			"Purchase Invoice", purchase_invoice.name, bank_account="Cash - _TC"
		)
		payment_entry.reference_no = f"Test-{purchase_invoice.name}"
		payment_entry.reference_date = today
		payment_entry.paid_amount = purchase_invoice.grand_total
		payment_entry.insert()
		payment_entry.submit()

		# Step 3: Validate Outstanding Amount
		purchase_invoice.reload()
		self.assertEqual(purchase_invoice.outstanding_amount, 0)
		self.assertEqual(purchase_invoice.status, "Paid")

		# Step 4: Validate Ledger Entries
		self.validate_ledger_entries(payment_entries=[payment_entry], purchase_invoices=[purchase_invoice])

	def test_purchase_invoice_payment_and_cancel_invoice_TC_ACC_019(self):
		"""Test payment against Purchase Invoices with advance adjustment."""
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		today = nowdate()
		# Step 1: Create and Submit the First Purchase Invoice
		first_purchase_invoice = make_purchase_invoice(
			supplier="_Test Supplier",
			company="_Test Company",
			item="_Test Item",
			qty=1,
			rate=100,
			warehouse="_Test Warehouse - _TC",
			currency="INR",
			naming_series="T-PINV-",
		)

		# Step 2: Create and Submit Payment Entry for the First Purchase Invoice
		payment_entry = get_payment_entry(
			"Purchase Invoice", first_purchase_invoice.name, bank_account="Cash - _TC"
		)
		payment_entry.reference_no = f"Test-{first_purchase_invoice.name}"
		payment_entry.reference_date = today
		payment_entry.paid_amount = first_purchase_invoice.grand_total
		payment_entry.insert(ignore_permissions=True)
		payment_entry.submit()

		# Step 3: Validate Outstanding Amount for the First Purchase Invoice
		first_purchase_invoice.reload()
		self.assertEqual(first_purchase_invoice.outstanding_amount, 0)
		self.assertEqual(first_purchase_invoice.status, "Paid")

		# Step 4: Cancel the First Purchase Invoice
		first_purchase_invoice.cancel()

		# Reload Payment Entry to Validate It Is Unlinked
		payment_entry.reload()
		self.assertEqual(payment_entry.references, [])

	def test_multiple_purchase_invoices_single_payment(self):
		"""Test single payment against multiple Purchase Invoices."""
		# Step 1: Create multiple Purchase Invoices
		pi1 = make_purchase_invoice()
		pi2 = make_purchase_invoice()
		total_payment_amount = pi1.grand_total + pi2.grand_total

		# Step 2: Create Payment Entry for both invoices
		payment_entry = get_payment_entry("Purchase Invoice", pi1.name, bank_account="Cash - _TC")
		payment_entry.append(
			"references",
			{
				"reference_doctype": "Purchase Invoice",
				"reference_name": pi2.name,
				"allocated_amount": pi2.grand_total,
			},
		)
		payment_entry.paid_amount = total_payment_amount
		payment_entry.insert()
		payment_entry.submit()

		# Step 3: Validate Outstanding Amounts
		for pi in [pi1, pi2]:
			pi.reload()
			self.assertEqual(pi.outstanding_amount, 0)
			self.assertEqual(pi.status, "Paid")

		# Step 4: Validate Ledger Entries
		self.validate_ledger_entries(payment_entries=[payment_entry], purchase_invoices=[pi1, pi2])

	def test_multiple_payment_entries_single_purchase_invoice(self):
		"""Test multiple payments against a single Purchase Invoice."""
		# Step 1: Create and Submit Purchase Invoice
		pi = make_purchase_invoice(qty=1, rate=300)
		pi.submit()

		# Step 2: Create Payment Entry 1 (Part Payment)
		pe1 = get_payment_entry("Purchase Invoice", pi.name, bank_account="Cash - _TC")
		pe1.paid_amount = 100
		pe1.references[0].allocated_amount = pe1.paid_amount
		pe1.submit()

		# Step 3: Create Payment Entry 2 (Remaining Payment)
		pe2 = frappe.copy_doc(pe1)
		pe2.paid_amount = 200
		pe2.references[0].allocated_amount = pe2.paid_amount
		pe2.submit()

		# Step 4: Validate Outstanding Amount
		pi.reload()
		self.assertEqual(pi.outstanding_amount, 0)
		self.assertEqual(pi.status, "Paid")

		# Step 5: Validate Ledger Entries
		self.validate_ledger_entries(payment_entries=[pe1, pe2], purchase_invoices=[pi])

	def test_tax_withholding_with_supplier_TC_ACC_023(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_purchase_invoice,
			make_test_item,
		)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_records as records_for_pi
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		records_for_pi("_Test Supplier TDS")
		category_doc = frappe.get_doc("Tax Withholding Category", "Test - TDS - 194C - Company")
		for rate in category_doc.rates:
			rate.from_date = add_days(today(), -30)
			rate.to_date = add_days(today(), 30)
		category_doc.save()
		supplier = frappe.get_doc("Supplier", "_Test Supplier TDS")
		if supplier:
			self.assertEqual(supplier.tax_withholding_category, "Test - TDS - 194C - Company")

		item = make_test_item()
		pi = create_purchase_invoice(supplier=supplier.name, item_code=item.name)
		pi.apply_tds = 1
		pi.tax_withholding_category = "Test - TDS - 194C - Company"
		pi.save()
		pi.submit()
		gl_entries = frappe.db.sql(
			"""select account, sum(debit) as debit, sum(credit) as credit , against_voucher
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			group by account,against_voucher""",
			pi.name,
			as_dict=1,
		)

		expected_result = [
			{"account": "Creditors - _TC", "debit": 1800.0, "credit": 90000.0, "against_voucher": pi.name},
			{
				"account": "_Test Account Excise Duty - _TC",
				"debit": 90000.0,
				"credit": 0.0,
				"against_voucher": None,
			},
			{"account": "_Test TDS Payable - _TC", "debit": 0.0, "credit": 1800.0, "against_voucher": None},
		]
		self.assertEqual(gl_entries, expected_result)

	def test_multiple_purchase_invoices_multiple_payments(self):
		"""Test payments against multiple Purchase Invoices and validate ledger entries."""
		today = nowdate()

		# Step 1: Create and Submit Purchase Invoices and Payment Entries
		purchase_invoices, payment_entries = [], []
		for _ in range(3):
			pi = make_purchase_invoice()
			purchase_invoices.append(pi)

			pe = get_payment_entry("Purchase Invoice", pi.name, bank_account="Cash - _TC")
			pe.update(
				{
					"reference_no": f"Test-{pi.name}",
					"reference_date": today,
					"paid_from_account_currency": pi.currency,
					"paid_to_account_currency": pi.currency,
					"source_exchange_rate": 1,
					"target_exchange_rate": 1,
					"paid_amount": pi.grand_total,
				}
			)
			pe.insert(ignore_permissions=True)
			pe.submit()
			payment_entries.append(pe)

		# Step 2: Validate Outstanding Amounts and Ledger Entries
		for pi in purchase_invoices:
			pi.reload()
			self.assertEqual(pi.outstanding_amount, 0, f"Outstanding amount is not zero for {pi.name}.")
			self.assertEqual(pi.status, "Paid", f"Purchase Invoice status is not 'Paid' for {pi.name}.")

		# Step 3: Validate Ledger Entries
		ledger_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": ["in", [pe.name for pe in payment_entries]]},
			fields=["account", "debit", "credit"],
		)

		for pe in payment_entries:
			debit_account, debit_amount = pe.paid_from, pe.paid_amount  # Paid from Cash/Bank
			credit_account, credit_amount = (
				purchase_invoices[0].credit_to,
				pe.paid_amount,
			)  # Credited to Creditors

			# Assert debit entry for Creditors and credit entry for Cash/Bank
			assert any(
				entry["account"] == debit_account and entry["credit"] == debit_amount
				for entry in ledger_entries
			), f"Credit entry missing for account: {debit_account} with amount: {debit_amount}."
			assert any(
				entry["account"] == credit_account and entry["debit"] == credit_amount
				for entry in ledger_entries
			), f"Debit entry missing for account: {credit_account} with amount: {credit_amount}."

		# Step 4: Validate total debit and credit balance
		total_credit = sum(entry["credit"] for entry in ledger_entries if entry["account"] == debit_account)
		total_debit = sum(entry["debit"] for entry in ledger_entries if entry["account"] == credit_account)
		assert (
			total_credit == total_debit
		), f"Total credit ({total_credit}) does not match total debit ({total_debit})."

	def test_lower_tax_deduction_TC_ACC_025_and_TC_ACC_026(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_purchase_invoice,
			make_test_item,
		)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_records as records_for_pi
		from erpnext.accounts.utils import get_fiscal_year

		tax_withholding_category = create_tax_witholding_category(
			category_name="Test - TDS - 194C - Company", company="_Test Company", account="Cash - _TC"
		)
		records_for_pi("_Test Supplier LDC")
		supplier = frappe.get_doc("Supplier", "_Test Supplier LDC")

		if supplier:
			update_ldc_details(supplier=supplier)
			self.assertEqual(supplier.tax_withholding_category, "Test - TDS - 194C - Company")
			fiscal_year, valid_from, valid_upto = get_fiscal_year(date=nowdate())
			ldc = create_ldc(supplier=supplier.name)
			filtered_data = {
				key: getattr(ldc, key)
				for key in [
					"tax_withholding_category",
					"fiscal_year",
					"supplier",
					"certificate_limit",
					"rate",
					"valid_from",
					"valid_upto",
				]
			}
			exepected_data = {
				"tax_withholding_category": "Test - TDS - 194C - Company",
				"fiscal_year": fiscal_year,
				"valid_from": valid_from,
				"valid_upto": valid_upto,
				"supplier": supplier.name,
				"certificate_limit": 40000,
				"rate": 1,
			}

			self.assertEqual(filtered_data, exepected_data)

			item = make_test_item()

			pi = create_purchase_invoice(supplier=supplier.name, rate=50000, item_code=item.name)
			pi.apply_tds = 1
			pi.tax_withholding_category = tax_withholding_category.name
			pi.save()
			pi.submit()

			expected_gle = [
				["Creditors - _TC", 0.0, 50000.0, pi.posting_date],
				["Creditors - _TC", 5000.0, 0.0, pi.posting_date],
				["Stock Received But Not Billed - _TC", 50000.0, 0.0, pi.posting_date],
				["_Test TDS Payable - _TC", 0.0, 5000.0, pi.posting_date],
			]

			check_gl_entries(self, pi.name, expected_gle, pi.posting_date)

	def test_currency_exchange_with_pi_TC_ACC_027(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_purchase_invoice,
			make_test_item,
		)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_records as records_for_pi
		from erpnext.controllers.tests.test_accounts_controller import make_supplier

		supplier_name = make_supplier("_Test Supplier USD", currency="USD")

		records_for_pi("_Test Supplier USD")
		supplier = frappe.get_doc("Supplier", supplier_name)

		# if supplier:
		item = make_test_item()

		pi = create_purchase_invoice(
			supplier=supplier.name,
			currency="USD",
			rate=100,
			item_code=item.name,
			credit_to="_Test Payable USD - _TC",
		)
		pi.conversion_rate = 63
		pi.save()
		pi.submit()

		pe = get_payment_entry("Purchase Invoice", pi.name)
		pe.payment_type = "Pay"
		pe.paid_from = "Cash - _TC"
		pe.target_exchange_rate = 60
		pe.save()
		pe.submit()

		expected_gle = [
			["Cash - _TC", 0.0, 6300.0, pe.posting_date],
			["Exchange Gain/Loss - _TC", 300.0, 0.0, pe.posting_date],
			["_Test Payable USD - _TC", 6000.0, 0.0, pe.posting_date],
		]

		check_gl_entries(
			doc=self,
			voucher_no=pe.name,
			expected_gle=expected_gle,
			posting_date=pe.posting_date,
			voucher_type="Payment Entry",
		)

		jea_parent = frappe.db.get_all(
			"Journal Entry Account",
			filters={
				"account": pi.credit_to,
				"docstatus": 1,
				"reference_name": pi.name,
				"party_type": "Supplier",
				"party": "_Test Supplier USD",
				"debit": 300,
			},
			fields=["parent"],
		)[0]

		self.assertEqual(
			frappe.db.get_value("Journal Entry", jea_parent.parent, "voucher_type"), "Exchange Gain Or Loss"
		)

		expected_jv_entries = [
			["Exchange Gain/Loss - _TC", 0.0, 300.0, pe.posting_date],
			["_Test Payable USD - _TC", 300.0, 0.0, pe.posting_date],
		]

		check_gl_entries(
			doc=self,
			voucher_no=jea_parent.parent,
			expected_gle=expected_jv_entries,
			posting_date=pe.posting_date,
			voucher_type="Journal Entry",
		)

	def test_advance_payment_TC_ACC_028(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

		pe = create_payment_entry(paid_amount=2500, save=True)
		pe.submit()

		pi = make_purchase_invoice(rate=1000, do_not_save=True)
		pi.append(
			"advances",
			{
				"reference_type": "Payment Entry",
				"reference_name": pe.name,
				"advance_amount": 2500,
				"allocated_amount": 2500,
			},
		)
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.status, "Partly Paid")
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.outstanding_amount, 2500)

		expected_entries = [
			{"account": "Stock Received But Not Billed - _TC", "debit": 5000.0, "credit": 0.0},
			{"account": "Creditors - _TC", "debit": 0.0, "credit": 5000.0},
		]

		pi_gle_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)

		self.assertCountEqual(pi_gle_entries, expected_entries)

		pe_1 = get_payment_entry(pi.doctype, pi.name)
		pe_1.insert()
		pe_1.submit()

		pi.load_from_db()
		self.assertEqual(pi.status, "Paid")
		self.assertEqual(pi.outstanding_amount, 0.0)

		pe_1_gl_entry = frappe.get_all(
			"GL Entry", filters={"voucher_no": pe_1.name}, fields=["account", "debit", "credit"]
		)
		actual_set = {(entry["account"], entry["debit"], entry["credit"]) for entry in pe_1_gl_entry}
		expected_set = {("Bank - _TC", 0.0, 2500.0), ("Creditors - _TC", 2500.0, 0.0)}

		self.assertSetEqual(actual_set, expected_set)

	def test_single_payment_request_for_purchase_invoice_TC_ACC_035(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_purchase_invoice,
			make_test_item,
		)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_records as records_for_pi,
		)
		from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		records_for_pi("_Test Supplier")

		supplier = frappe.get_doc("Supplier", "_Test Supplier")

		if supplier:
			item = make_test_item()
			pi = create_purchase_invoice(
				supplier=supplier.name,
				currency="INR",
				rate=5000,
				item_code=item.name,
			)
			pi.save(ignore_permissions=True)
			pi.submit()

			pr = make_payment_request(
				dt="Purchase Invoice",
				dn=pi.name,
				party_type="Supplier",
				party=supplier.name,
				grand_total=5000,
				submit_doc=1,
				return_doc=1,
			)
			pe = pr.create_payment_entry(submit=False)
			pe.payment_type = "Pay"
			pe.paid_from = "Cash - _TC"
			pe.save(ignore_permissions=True)
			pe.submit()
			pr.load_from_db()
			self.assertEqual(pr.status, "Paid")
			pe.load_from_db()
			expected_gle = [
				["Cash - _TC", 0.0, 5000.0, pe.posting_date],
				["Creditors - _TC", 5000.0, 0.0, pe.posting_date],
			]
			check_gl_entries(
				doc=self,
				voucher_no=pe.name,
				expected_gle=expected_gle,
				voucher_type="Payment Entry",
				posting_date=pe.posting_date,
			)
			pi.load_from_db()
			self.assertEqual(pi.status, "Paid")

	def test_multi_payment_request_for_purchase_invoice_TC_ACC_036(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_purchase_invoice,
			make_test_item,
		)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_records as records_for_pi,
		)
		from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		records_for_pi("_Test Supplier")

		supplier = frappe.get_doc("Supplier", "_Test Supplier")

		if supplier:
			item = make_test_item()
			pi = create_purchase_invoice(
				supplier=supplier.name,
				currency="INR",
				rate=5000,
				item_code=item.name,
			)
			pi.save()
			pi.submit()

			pr = make_payment_request(
				dt="Purchase Invoice",
				dn=pi.name,
				party_type="Supplier",
				party=supplier.name,
				return_doc=1,
			)
			pr.grand_total = pr.grand_total / 2
			pr.save()
			pr.submit()
			pe = pr.create_payment_entry(submit=False)
			pe.payment_type = "Pay"
			pe.paid_from = "Cash - _TC"
			pe.save()
			pe.submit()
			pr.load_from_db()
			self.assertEqual(pr.status, "Paid")
			pe.load_from_db()
			expected_gle = [
				["Cash - _TC", 0.0, 2500.0, pe.posting_date],
				["Creditors - _TC", 2500.0, 0.0, pe.posting_date],
			]
			check_gl_entries(
				doc=self,
				voucher_no=pe.name,
				expected_gle=expected_gle,
				voucher_type="Payment Entry",
				posting_date=pe.posting_date,
			)
			pi.load_from_db()
			self.assertEqual(pi.status, "Partly Paid")
			_pr = make_payment_request(
				dt="Purchase Invoice",
				dn=pi.name,
				party_type="Supplier",
				party=supplier.name,
				return_doc=1,
				submit_doc=1,
			)
			_pe = _pr.create_payment_entry(submit=False)
			_pe.payment_type = "Pay"
			_pe.paid_from = "Cash - _TC"
			_pe.save()
			_pe.submit()
			_pr.load_from_db()
			self.assertEqual(_pr.status, "Paid")
			_pe.load_from_db()
			expected_gle = [
				["Cash - _TC", 0.0, 2500.0, _pe.posting_date],
				["Creditors - _TC", 2500.0, 0.0, _pe.posting_date],
			]
			check_gl_entries(
				doc=self,
				voucher_no=_pe.name,
				expected_gle=expected_gle,
				voucher_type="Payment Entry",
				posting_date=_pe.posting_date,
			)

	def test_tds_computation_summary_report_TC_ACC_094(self):
		"""Test the TDS Computation Summary report for Purchase Invoice data."""
		from frappe.desk.query_report import get_report_result

		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		company = "_Test Company"
		tds_account_args = {
			"doctype": "Account",
			"account_name": "TDS Payable",
			"account_type": "Tax",
			"parent_account": frappe.db.get_value(
				"Account", {"account_name": "Duties and Taxes", "company": company}
			),
			"company": company,
		}
		tds_account = create_account(**tds_account_args)
		tax_withholding_category = "Test TDS - 194 - Dividends - Individual"
		create_tax_witholding_category(tax_withholding_category, company, tds_account)

		# create a new supplier to test
		supplier = create_supplier(
			supplier_name="_Test TDS Advance Supplier",
			tax_withholding_category=tax_withholding_category,
		)

		# Create Purchase Order with TDS applied
		po = create_purchase_order(
			do_not_save=1,
			supplier=supplier.name,
			rate=3000,
			item="_Test Non Stock Item",
			posting_date=nowdate(),
		)
		po.save().submit()
		# Create Purchase Invoice against Purchase Order
		purchase_invoice = get_mapped_purchase_invoice(po.name)
		purchase_invoice.posting_date = nowdate()
		purchase_invoice.allocate_advances_automatically = 1
		purchase_invoice.items[0].item_code = "_Test Non Stock Item"
		purchase_invoice.items[0].expense_account = "_Test Account Cost for Goods Sold - _TC"
		purchase_invoice.save()
		purchase_invoice.submit()

		report_name = "TDS Computation Summary"

		filters = {
			"company": company,
			"party_type": "Supplier",
			"from_date": str(get_quarter_start(getdate(nowdate()))),
			"to_date": nowdate(),
		}
		report = frappe.get_doc("Report", report_name)
		report_data = get_report_result(report, filters) or []
		# Extract expected data from the report result
		rows = report_data[1]
		# Assuming `rows` contains the data from the report
		expected_data = {
			"party": supplier.name,
			"section_code": tax_withholding_category,
			"entity_type": "Company",
			"rate": 10.0,  # TDS rate
			"total_amount": 30000.0,  # Total amount for the invoice
			"tax_amount": 3000.0,  # TDS amount deducted
		}

		# Find the row corresponding to the purchase invoice
		matching_row = None
		for row in rows:
			if (
				row["party"] == expected_data["party"]
				and row["section_code"] == expected_data["section_code"]
			):
				matching_row = row
				break

		# Assert the matching row exists
		self.assertIsNotNone(
			matching_row, "The expected row for the supplier and section code was not found."
		)
		purchase_invoice.cancel()

	def test_tds_computation_summary_report_TC_ACC_095(self):
		from frappe.desk.query_report import get_report_result

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry

		company = "_Test Company"

		# Create TDS account
		tds_account_args = {
			"doctype": "Account",
			"account_name": "TDS Payable",
			"account_type": "Tax",
			"parent_account": frappe.db.get_value(
				"Account", {"account_name": "Duties and Taxes", "company": company}
			),
			"company": company,
		}
		tds_account = create_account(**tds_account_args)

		# Create Tax Withholding Category
		tax_withholding_category = "Test - TDS - 194C - Company"
		create_tax_witholding_category(tax_withholding_category, company, tds_account)
		# Create Supplier with the TDS category
		supplier = create_supplier(
			supplier_name="_Test Supplier TDS PE",
			tax_withholding_category=tax_withholding_category,
		)

		# Create Payment Entry with TDS
		payment_entry = create_payment_entry(
			party_type="Supplier",
			party=supplier.name,
			payment_type="Pay",
			paid_from="Cash - _TC",
			paid_to="Creditors - _TC",
			save=True,
		)
		payment_entry.posting_date = nowdate()
		payment_entry.apply_tax_withholding_amount = 1
		payment_entry.tax_withholding_category = tax_withholding_category
		payment_entry.paid_amount = 30000.0
		payment_entry.append(
			"taxes",
			{
				"account_head": "_Test TDS Payable - _TC",
				"charge_type": "On Paid Amount",
				"rate": 0,
				"add_deduct_tax": "Deduct",
				"description": "TDS Deduction",
			},
		)
		payment_entry.save()
		payment_entry.submit()

		# Run the report
		report_name = "TDS Computation Summary"
		filters = {
			"company": company,
			"party_type": "Supplier",
			"from_date": str(get_quarter_start(getdate(nowdate()))),
			"to_date": nowdate(),
		}
		report = frappe.get_doc("Report", report_name)
		report_data = get_report_result(report, filters) or []
		rows = report_data[1]

		# Expected values
		expected_data = {
			"party": supplier.name,
			"section_code": tax_withholding_category,
			"entity_type": "Company",
			"rate": 10.0,
			"total_amount": 30000.0,
			"tax_amount": 3000.0,
		}

		# Find matching row
		matching_row = None
		for row in rows:
			if (
				row["party"] == expected_data["party"]
				and row["section_code"] == expected_data["section_code"]
			):
				matching_row = row
				break

		# Assertions
		self.assertIsNotNone(
			matching_row, "The expected row for the supplier and section code was not found."
		)
		self.assertEqual(matching_row["rate"], expected_data["rate"])
		self.assertEqual(matching_row["total_amount"], expected_data["total_amount"])
		self.assertEqual(matching_row["tax_amount"], expected_data["tax_amount"])

		# Cleanup
		payment_entry.cancel()

	def test_tds_computation_summary_report_TC_ACC_096(self):
		from frappe.desk.query_report import get_report_result

		company = "_Test Company"

		# Create TDS account
		tds_account_args = {
			"doctype": "Account",
			"account_name": "TDS Payable Journal",
			"account_type": "Tax",
			"parent_account": frappe.db.get_value(
				"Account", {"account_name": "Duties and Taxes", "company": company}
			),
			"company": company,
		}
		tds_account = create_account(**tds_account_args)
		# Create Tax Withholding Category
		tax_withholding_category = "Test - TDS - 194H - Journal"
		create_tax_witholding_category(tax_withholding_category, company, tds_account)

		# Create Supplier with the TDS category
		supplier = create_supplier(
			supplier_name="_Test Supplier TDS JE",
			tax_withholding_category=tax_withholding_category,
		)

		# Create Journal Entry with TDS
		je = frappe.new_doc("Journal Entry")
		je.voucher_type = "Journal Entry"
		je.posting_date = nowdate()
		je.company = company
		je.tax_withholding_category = tax_withholding_category
		je.apply_tax_withholding_amount = 1

		je.append(
			"accounts",
			{
				"account": "Creditors - _TC",
				"party_type": "Supplier",
				"party": supplier.name,
				"credit_in_account_currency": 10000.0,
			},
		)
		je.append(
			"accounts",
			{
				"account": "Cash - _TC",
				"debit_in_account_currency": 9000.0,
			},
		)
		je.append(
			"accounts",
			{
				"account": tds_account,
				"debit_in_account_currency": 1000.0,
			},
		)
		je.save()
		je.submit()

		# Run the report
		report_name = "TDS Computation Summary"
		filters = {
			"company": company,
			"party_type": "Supplier",
			"from_date": str(get_quarter_start(getdate(nowdate()))),
			"to_date": nowdate(),
		}
		report = frappe.get_doc("Report", report_name)
		report_data = get_report_result(report, filters) or []
		rows = report_data[1]

		# Expected values
		expected_data = {
			"party": supplier.name,
			"section_code": tax_withholding_category,
			"entity_type": "Company",
			"rate": 10.0,
			"total_amount": 10000.0,
			"tax_amount": 500.0,
		}

		# Find matching row
		matching_row = None
		for row in rows:
			if (
				row["party"] == expected_data["party"]
				and row["section_code"] == expected_data["section_code"]
			):
				matching_row = row
				break

		# Assertion
		self.assertIsNotNone(
			matching_row,
			"The expected row for Journal Entry TDS was not found in the report. Check if Journal Entry data is included.",
		)

		je.cancel()

	def test_invoice_status_on_payment_entry_submit_TC_B_035_and_TC_B_037(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
		from erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment import (
			get_linked_payments_for_doc,
		)

		frappe.set_value("Supplier", "_Test Supplier", "payment_terms", None)
		add_purchase_invoice_in_account_reposting_setting()
		pi = make_purchase_invoice(
			qty=1, item_code="_Test Item", supplier="_Test Supplier", company="_Test Company", rate=30
		)

		pi.save()
		pi.reload()
		pi.submit()
		pi_status_before = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status_before, "Unpaid")

		pe = create_payment_entry(
			company="_Test Company",
			payment_type="Pay",
			party_type="Supplier",
			party="_Test Supplier",
			paid_to="Creditors - _TC",
			paid_from="Cash - _TC",
			paid_amount=pi.grand_total,
		)
		pe.append(
			"references",
			{
				"reference_doctype": "Purchase Invoice",
				"reference_name": pi.name,
				"allocated_amount": pi.rounded_total,
			},
		)
		pe.save()
		pe.submit()
		pe.reload()
		pi.reload()
		pi_status_after = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status_after, "Paid")

		return_pi = make_debit_note(pi.name)
		return_pi.update_outstanding_for_self = 0
		return_pi.save()
		return_pi.submit()
		self.assertEqual(return_pi.status, "Return")

		pi.reload()
		self.assertEqual(pi.status, "Paid")

		get_linked_payments_for_doc(pe.company, pe.doctype, pe.name)

	def test_partly_paid_of_pi_to_pr_to_pe_TC_B_081(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_payment_entry,
		)
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		warehouse = frappe.db.get_all("Warehouse", {"company": "_Test Company", "is_group": 0}, ["name"])
		cost_center = frappe.db.get_value("Cost Center", {"company": "_Test Company"}, "name")
		create_supplier(supplier_name="_Test Supplier")
		paid_from_account = frappe.db.get_value(
			"Account",
			{"company": "_Test Company", "account_type": ["in", ["Bank", "Cash"]], "is_group": 0},
			["name"],
		)
		get_or_create_fiscal_year("_Test Company")
		create_item(item_code="_Test Item", warehouse=warehouse[0].name)

		pi = make_purchase_invoice(
			qty=1,
			item_code="_Test Item",
			supplier="_Test Supplier",
			company="_Test Company",
			supplier_warehouse=warehouse[0]["name"],
			warehouse=warehouse[1]["name"],
			expense_account="Cash - _TC",
			uom="Box",
			cost_center=cost_center,
			rate=500,
			do_not_save=True,
		)
		pi.due_date = today()
		pi.save()
		pi.submit()

		pr = frappe.new_doc("Payment Request")
		pr.payment_request_type = "Outward"
		pr.party_type = "Supplier"
		pr.party = "_Test Supplier"
		pr.reference_doctype = "Purchase Invoice"
		pr.reference_name = pi.name
		pr.grand_total = 250

		pr.save()
		pr.submit()

		pe = create_payment_entry(
			company="_Test Company",
			payment_type="Pay",
			party_type="Supplier",
			party="_Test Supplier",
			paid_to="Creditors - _TC",
			paid_from=paid_from_account,
			paid_amount=pr.grand_total,
		)

		pe.append(
			"references",
			{
				"reference_doctype": "Purchase Invoice",
				"reference_name": pi.name,
				"allocated_amount": pr.grand_total,
			},
		)
		pe.save()
		pe.submit()

		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Partly Paid")

	def test_material_transfer_between_branch_TC_B_149(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_inter_company_purchase_invoice
		from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_company_and_supplier

		get_required_data = create_company_and_supplier()
		parent_company = get_required_data.get("parent_company")
		child_company = get_required_data.get("child_company")
		supplier = get_required_data.get("supplier")
		customer = get_required_data.get("customer")
		price_list = get_required_data.get("price_list")
		item_name = make_test_item("test_service")
		si = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": parent_company,
				"customer": customer,
				"due_date": today(),
				"currency": "INR",
				"selling_price_list": price_list,
				"items": [
					{
						"item_code": item_name,
						"qty": 10,
						"rate": 100,
					}
				],
			}
		)
		si.insert(ignore_permissions=True)
		si.submit()
		self.assertEqual(si.company, parent_company)
		self.assertEqual(si.customer, customer)
		self.assertEqual(si.selling_price_list, price_list)
		self.assertEqual(si.items[0].rate, 100)
		self.assertEqual(si.total, 1000)
		pi = make_inter_company_purchase_invoice(si.name)
		pi.bill_no = "test bill"
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.company, child_company)
		self.assertEqual(pi.supplier, supplier)
		self.assertEqual(pi.items[0].rate, 100)
		self.assertEqual(pi.total, 1000)

	def test_fully_paid_of_pi_to_pr_to_pe_TC_B_082(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_payment_entry,
			make_test_item,
		)
		from erpnext.controllers.tests.test_accounts_controller import make_supplier

		add_purchase_invoice_in_account_reposting_setting()
		make_test_item("_Test Item")
		make_supplier("_Test Supplier", currency="INR")
		pi = make_purchase_invoice(
			qty=1,
			item_code="_Test Item",
			supplier="_Test Supplier",
			company="_Test Company",
			cost_center="Main - _TC",
			uom="Nos",
			warehouse="Stores - _TC",
			supplier_warehouse="Stores - _TC",
			expense_account="Cost of Goods Sold - _TC",
			rate=500,
		)

		pi.save()
		pi.reload()
		pi.submit()

		pr = frappe.new_doc("Payment Request")
		pr.payment_request_type = "Outward"
		pr.party_type = "Supplier"
		pr.party = "_Test Supplier"
		pr.reference_doctype = "Purchase Invoice"
		pr.reference_name = pi.name
		pr.grand_total = 500

		pr.save()
		pr.submit()

		pe = create_payment_entry(
			company="_Test Company",
			payment_type="Pay",
			party_type="Supplier",
			party="_Test Supplier",
			paid_to="Creditors - _TC",
			paid_from="Cash - _TC",
			paid_amount=pr.grand_total,
		)
		pe.append(
			"references",
			{
				"reference_doctype": "Purchase Invoice",
				"reference_name": pi.name,
				"allocated_amount": pr.grand_total,
			},
		)
		pe.save()
		pe.submit()

		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Paid")

	def test_partly_paid_of_pi_to_pr_to_pe_with_gst_TC_B_083(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_company,
			create_payment_entry,
		)
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		warehouse = frappe.db.get_all("Warehouse", {"company": "_Test Company", "is_group": 0}, ["name"])
		get_or_create_fiscal_year("_Test Company")
		purchase_tax_category = frappe.db.get_value("Tax Category", {"title": "Test Tax Category 1"}, "name")
		purchase_tax = frappe.new_doc("Purchase Taxes and Charges Template")
		purchase_tax.title = "TEST"
		purchase_tax.company = "_Test Company"
		purchase_tax.tax_category = purchase_tax_category
		cost_center = frappe.db.get_value("Cost Center", {"company": "_Test Company"}, "name")
		account_head = frappe.db.get_value(
			"Account", {"company": "_Test Company", "is_group": 0, "account_type": "Tax"}, "name"
		)
		create_item(item_code="_Test Item", warehouse=warehouse[0].name)
		purchase_tax.append(
			"taxes",
			{
				"category": "Total",
				"add_deduct_tax": "Add",
				"charge_type": "On Net Total",
				"account_head": account_head,
				"rate": 100,
				"description": "GST",
			},
		)

		purchase_tax.save(ignore_permissions=True)
		pi = make_purchase_invoice(
			qty=1,
			item_code="_Test Item",
			supplier="_Test Supplier",
			company="_Test Company",
			rate=500,
			supplier_warehouse=warehouse[0]["name"],
			warehouse=warehouse[1]["name"],
			expense_account="Cash - _TC",
			uom="Box",
			cost_center=cost_center,
			do_not_save=True,
		)

		pi.taxes_and_charges = purchase_tax.name
		pi.save(ignore_permissions=True)
		pi.submit()

		pr = frappe.new_doc("Payment Request")
		pr.payment_request_type = "Outward"
		pr.party_type = "Supplier"
		pr.party = "_Test Supplier"
		pr.reference_doctype = "Purchase Invoice"
		pr.reference_name = pi.name
		pr.grand_total = 250

		pr.save(ignore_permissions=True)
		pr.submit()

		paid_from_account = frappe.db.get_value(
			"Account",
			{"company": "_Test Company", "account_type": ["in", ["Bank", "Cash"]], "is_group": 0},
			["name"],
		)
		pe = create_payment_entry(
			company="_Test Company",
			payment_type="Pay",
			party_type="Supplier",
			party="_Test Supplier",
			paid_to="Creditors - _TC",
			paid_from=paid_from_account,
			paid_amount=pr.grand_total,
		)
		pe.append(
			"references",
			{
				"reference_doctype": "Purchase Invoice",
				"reference_name": pi.name,
				"allocated_amount": pr.grand_total,
			},
		)
		pe.save(ignore_permissions=True)
		pe.submit()

		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Partly Paid")

	def test_fully_paid_of_pi_to_pr_to_pe_with_gst_TC_B_084(self):
		frappe.set_user("Administrator")
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_entry
		from erpnext.buying.doctype.supplier.test_supplier import create_supplier

		frappe.set_value("Supplier", "_Test Supplier", "payment_terms", None)
		template = frappe.get_all(
			"Purchase Taxes and Charges Template",
			filters={
				"company": "_Test Company",
				"tax_category": "_Test Tax Category 1",
				"disabled": 0,
			},
			fields=["name"],
			limit=1,
		)

		if not template:
			purchase_tax = frappe.new_doc("Purchase Taxes and Charges Template")
			purchase_tax.title = "TEST"
			purchase_tax.company = "_Test Company"
			purchase_tax.tax_category = "_Test Tax Category 1"

			purchase_tax.append(
				"taxes",
				{
					"category": "Total",
					"add_deduct_tax": "Add",
					"charge_type": "On Net Total",
					"account_head": "_Test Account Excise Duty - _TC",
					"rate": 100,
					"description": "GST",
				},
			)

			purchase_tax.insert()
		else:
			purchase_tax = frappe.get_doc("Purchase Taxes and Charges Template", template[0].name)

		pi = make_purchase_invoice(
			qty=1,
			item_code="_Test Item",
			supplier="_Test Supplier",
			company="_Test Company",
			rate=500,
			do_not_save=True,
		)

		pi.taxes_and_charges = purchase_tax.name
		pi.save()
		pi.submit()

		pr = frappe.new_doc("Payment Request")
		pr.payment_request_type = "Outward"
		pr.party_type = "Supplier"
		pr.party = "_Test Supplier"
		pr.reference_doctype = "Purchase Invoice"
		pr.reference_name = pi.name
		pr.grand_total = pi.grand_total

		pr.save()
		pr.submit()

		pe = create_payment_entry(
			company="_Test Company",
			payment_type="Pay",
			party_type="Supplier",
			party="_Test Supplier",
			paid_to="Creditors - _TC",
			paid_from="Cash - _TC",
			paid_amount=pr.grand_total,
		)
		pe.append(
			"references",
			{
				"reference_doctype": "Purchase Invoice",
				"reference_name": pi.name,
				"allocated_amount": pr.grand_total,
			},
		)
		pe.save()
		pe.submit()

		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Paid")

	def test_pi_ignore_pricing_rule_TC_B_051(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.buying.doctype.purchase_order.test_purchase_order import get_company_or_supplier

		item_price = 130
		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		target_warehouse = "Stores - TC-5"
		item = make_test_item("test_item_ignore_rule")
		item.is_purchase_item = 1
		item.is_sales_item = 0
		item.save(ignore_permissions=True)

		if not frappe.db.exists("Item Price", {"item_code": item.item_code, "price_list": "Standard Buying"}):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"price_list": get_or_create_price_list(),
					"item_code": item.item_code,
					"price_list_rate": item_price,
					"currency": "INR",
				}
			).insert(ignore_permissions=True, ignore_mandatory=True)

		if not frappe.db.exists("Pricing Rule", {"title": "10% Discount"}):
			frappe.get_doc(
				{
					"doctype": "Pricing Rule",
					"title": "10% Discount",
					"company": company,
					"apply_on": "Item Code",
					"items": [{"item_code": item.item_code}],
					"rate_or_discount": "Discount Percentage",
					"discount_percentage": 10,
					"selling": 0,
					"buying": 1,
				}
			).insert(ignore_permissions=True)

		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"supplier": supplier,
				"company": company,
				"posting_date": today(),
				"currency": "INR",
				"buying_price_list": get_or_create_price_list(),
				"set_warehouse": target_warehouse,
				"items": [{"item_code": item.item_code, "warehouse": target_warehouse, "qty": 1}],
			}
		)
		pi.bill_no = "test_bill_1122"
		pi.insert(ignore_permissions=True)
		self.assertEqual(len(pi.items), 1)
		self.assertEqual(pi.items[0].rate, 117)
		self.assertEqual(pi.items[0].discount_percentage, 10)
		pi.ignore_pricing_rule = 1
		pi.save(ignore_permissions=True)
		self.assertEqual(pi.items[0].rate, 130)
		self.assertEqual(pi.items[0].discount_percentage, 0)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)
		self.assertEqual(pi.items[0].rate, 130)

	def test_standalone_pi_is_fully_paid_TC_B_088(self):
		frappe.set_user("Administrator")
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		purchase_tax = frappe.new_doc("Purchase Taxes and Charges Template")
		purchase_tax.title = "TEST"
		purchase_tax.company = "_Test Company"
		purchase_tax.tax_category = "_Test Tax Category 2"

		purchase_tax.append(
			"taxes",
			{
				"category": "Total",
				"add_deduct_tax": "Add",
				"charge_type": "On Net Total",
				"account_head": "_Test Account Excise Duty - _TC",
				"_Test Account Excise Duty": "_Test Account Excise Duty",
				"rate": 100,
				"description": "GST",
			},
		)

		purchase_tax.save()

		pi = make_purchase_invoice(
			qty=1,
			item_code="_Test Item",
			supplier="_Test Supplier",
			company="_Test Company",
			rate=500,
			do_not_save=True,
		)

		pi.taxes_and_charges = purchase_tax.name
		pi.is_paid = 1
		pi.mode_of_payment = "Cash"
		pi.cash_bank_account = "Cash - _TC"
		pi.save()
		pi.paid_amount = pi.grand_total
		pi.submit()

		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Paid")

	def test_standalone_pi_is_partly_paid_TC_B_090(self):
		frappe.set_user("Administrator")
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		purchase_tax = frappe.new_doc("Purchase Taxes and Charges Template")
		purchase_tax.title = "TEST"
		purchase_tax.company = "_Test Company"
		purchase_tax.tax_category = "_Test Tax Category 2"

		purchase_tax.append(
			"taxes",
			{
				"category": "Total",
				"add_deduct_tax": "Add",
				"charge_type": "On Net Total",
				"account_head": "_Test Account Excise Duty - _TC",
				"_Test Account Excise Duty": "_Test Account Excise Duty",
				"rate": 100,
				"description": "GST",
			},
		)

		purchase_tax.save()

		pi = make_purchase_invoice(
			qty=1,
			item_code="_Test Item",
			supplier="_Test Supplier",
			company="_Test Company",
			rate=500,
			do_not_save=True,
		)

		pi.taxes_and_charges = purchase_tax.name
		pi.is_paid = 1
		pi.mode_of_payment = "Cash"
		pi.cash_bank_account = "Cash - _TC"
		pi.save()
		pi.paid_amount = pi.grand_total / 2
		pi.submit()

		pi_status = frappe.db.get_value("Purchase Invoice", pi.name, "status")
		self.assertEqual(pi_status, "Partly Paid")

	def test_pi_with_additional_discount_TC_B_054(self):
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		pi_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"supplier": "_Test Supplier",
			"schedule_date": "2025-01-13",
			"qty": 1,
			"rate": 10000,
			"apply_discount_on": "Net Total",
			"additional_discount_percentage": 10,
			"do_not_submit": 1,
		}

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = "_Test Company"
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax IGST", "company": "_Test Company"}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		doc_pi = make_purchase_invoice(**pi_data)
		doc_pi.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 12,
				"description": "Input GST",
			},
		)
		doc_pi.submit()
		self.assertEqual(doc_pi.discount_amount, 1000)
		self.assertEqual(doc_pi.grand_total, 10080)

		# Accounting Ledger Checks
		pi_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": doc_pi.name}, fields=["account", "debit", "credit"]
		)

		# PI Ledger Validation
		pi_total = sum(entry["debit"] for entry in pi_gl_entries)
		self.assertEqual(pi_total, 10080)

	def test_pi_with_additional_discount_TC_B_060(self):
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		# Scenario : PI [With Additional Discount on Grand Total][StandAlone]
		pi_data = {
			"company": "_Test Company",
			"item_code": "_Test Item",
			"warehouse": "Stores - _TC",
			"supplier": "_Test Supplier",
			"schedule_date": "2025-01-13",
			"qty": 1,
			"rate": 10000,
			"apply_discount_on": "Grand Total",
			"additional_discount_percentage": 10,
			"do_not_submit": 1,
		}

		acc = frappe.new_doc("Account")
		acc.account_name = "Input Tax IGST"
		acc.parent_account = "Tax Assets - _TC"
		acc.company = "_Test Company"
		account_name = frappe.db.exists(
			"Account", {"account_name": "Input Tax IGST", "company": "_Test Company"}
		)
		if not account_name:
			account_name = acc.insert(ignore_permissions=True)

		doc_pi = make_purchase_invoice(**pi_data)
		doc_pi.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": account_name,
				"rate": 12,
				"description": "Input GST",
			},
		)
		doc_pi.submit()
		self.assertEqual(doc_pi.discount_amount, 1120)
		self.assertEqual(doc_pi.grand_total, 10080)

		# Accounting Ledger Checks
		pi_gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": doc_pi.name}, fields=["account", "debit", "credit"]
		)

		# PI Ledger Validation
		pi_total = sum(entry["debit"] for entry in pi_gl_entries)
		self.assertEqual(pi_total, 10080)

	@if_app_installed("india_compliance")
	def test_pi_standalone_pi_with_deferred_expense_TC_B_095(self):
		gst_hsn_code = "11112222"
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		from erpnext.accounts.doctype.account.test_account import create_account

		create_account(
			account_name="Deferred Expense", company="_Test Company", parent_account="Tax Assets - _TC"
		)
		if not frappe.db.exists("GST HSN Code", gst_hsn_code):
			gst_hsn_doc = frappe.new_doc("GST HSN Code")
			gst_hsn_doc.hsn_code = gst_hsn_code
			gst_hsn_doc.insert(ignore_permissions=True)

		if not frappe.db.exists("Item", "_Test Item"):
			item = frappe.new_doc("Item")
			item.item_code = "_Test Item"
			item.gst_hsn_code = gst_hsn_code
			item.item_group = "All Item Groups"
			item.enable_deferred_expense = 1
			item.no_of_months_exp = 12
			item.insert(ignore_permissions=True)
		else:
			item = frappe.get_doc("Item", "_Test Item")
			item.gst_hsn_code = gst_hsn_code
			item.enable_deferred_expense = 1
			item.no_of_months_exp = 12
			item.save(ignore_permissions=True)
		pi = make_purchase_invoice(item_code=item.item_code, qty=1, rate=100, do_not_submit=True)
		if pi.items:
			pi.items[0].enable_deferred_expense = 1
			pi.items[0].deferred_expense_account = "Deferred Expense - _TC"
			pi.items[0].service_start_date = today()
			pi.items[0].service_end_date = add_days(today(), 1)
		pi.submit()

	def test_pi_with_uploader_TC_B_092(self):
		item_1 = create_item("_Test Item")
		item_2 = create_item("_Test Item Home Desktop 200")
		pi_data = {
			"doctype": "Purchase Invoice",
			"company": "_Test Company",
			"supplier": "_Test Supplier",
			"set_posting_time": 1,
			"posting_date": today(),
			"update_stock": 1,
			"currency": "INR",
			"items": [],
		}

		# Uploader Data
		uploaded_data = [
			{"item_code": item_1.item_code, "warehouse": "_Test Warehouse 1 - _TC", "qty": 1, "rate": 2000},
			{"item_code": item_2.item_code, "warehouse": "_Test Warehouse 1 - _TC", "qty": 1, "rate": 1000},
		]

		# Simulating Upload Feature: Fill items table using uploaded data
		pi_doc = frappe.get_doc(pi_data)
		for row in uploaded_data:
			pi_doc.append(
				"items",
				{
					"item_code": row["item_code"],
					"warehouse": row["warehouse"],
					"qty": row["qty"],
					"rate": row["rate"],
				},
			)

		# Insert and Submit PI
		pi_doc.insert()
		pi_doc.submit()

		# Assertions for items table
		self.assertEqual(len(pi_doc.items), 2, "All items should be added to the PI.")
		self.assertEqual(pi_doc.items[0].item_code, "_Test Item", "First item code should be 'Tissue'.")
		self.assertEqual(
			pi_doc.items[1].item_code, "_Test Item Home Desktop 200", "Second item code should be 'Book'."
		)
		self.assertEqual(pi_doc.items[0].rate, 2000, "Rate for Tissue should be 2000.")
		self.assertEqual(pi_doc.items[1].rate, 1000, "Rate for Book should be 1000.")

		# Check Accounting Entries
		gle = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi_doc.name}, fields=["account", "debit", "credit"]
		)
		self.assertGreater(len(gle), 0, "GL Entries should be created.")

		# Validate Stock Ledger
		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": pi_doc.name},
			fields=["item_code", "actual_qty", "stock_value"],
		)
		self.assertEqual(len(sle), 2, "Stock Ledger should have entries for both items.")
		self.assertEqual(sle[0]["item_code"], "_Test Item Home Desktop 200")
		self.assertEqual(sle[1]["item_code"], "_Test Item")
		self.assertEqual(sle[0]["actual_qty"], 1, "Quantity for Tissue should be 1.")
		self.assertEqual(sle[1]["actual_qty"], 1, "Quantity for Book should be 1.")

		# Cleanup
		pi_doc.cancel()

	def test_deferred_expense_invoice_line_item_TC_ACC_041(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_records as records_for_pi,
		)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			make_test_item,
		)

		records_for_pi("_Test Supplier")

		item = make_test_item()
		item.enable_deferred_expense = 1
		item.no_of_months_exp = 12
		item.save()

		create_account(
			account_name="Deferred Expense", company="_Test Company", parent_account="Tax Assets - _TC"
		)

		pi = make_purchase_invoice(
			qty=1,
			item_code=item.item_code,
			supplier="_Test Supplier",
			company="_Test Company",
			rate=50000,
			do_not_submit=True,
		)
		if pi.items:
			pi.items[0].enable_deferred_expense = 1
			pi.items[0].deferred_expense_account = "Deferred Expense - _TC"

		pi.submit()
		expected_gl_entries = [
			["Creditors - _TC", 0.0, 50000.0, pi.posting_date],
			["Deferred Expense - _TC", 50000.0, 0.0, pi.posting_date],
		]

		check_gl_entries(
			self,
			pi.name,
			expected_gl_entries,
			pi.posting_date,
		)

	def test_deferred_expense_invoice_multiple_item_TC_ACC_042(self):
		from erpnext.accounts.doctype.account.test_account import create_account
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_records as records_for_pi,
		)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			make_test_item,
		)
		from erpnext.stock.get_item_details import calculate_service_end_date
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")

		create_account(
			account_name="Deferred Expense", company="_Test Company", parent_account="Tax Assets - _TC"
		)
		records_for_pi("_Test Supplier")

		items_list = ["_Test Item 1", "_Test Item 2"]
		for item in items_list:
			item = make_test_item(item_name=item)
			item.enable_deferred_expense = 1
			item.no_of_months_exp = 12
			item.save(ignore_permissions=True)

		pi = make_purchase_invoice(
			qty=1,
			item_code=items_list[0],
			supplier="_Test Supplier",
			company="_Test Company",
			rate=50000,
			do_not_submit=True,
		)
		if pi.items:
			pi.items[0].enable_deferred_expense = 1
			pi.items[0].deferred_expense_account = "Deferred Expense - _TC"

		pi.append(
			"items",
			{
				"item_name": items_list[1],
				"item_code": items_list[1],
				"qty": 1,
				"rate": 50000,
				"warehouse": "_Test Warehouse - _TC",
				"expense_account": "_Test Account Cost for Goods Sold - _TC",
				"enable_deferred_expense": 1,
				"deferred_expense_account": "Deferred Expense - _TC",
				"service_start_date": pi.posting_date,
			},
		)
		end_date_obj = calculate_service_end_date(args=pi.items[1].as_dict())
		pi.items[1].service_end_date = end_date_obj.get("service_end_date")
		pi.save()
		pi.submit()

		expected_gl_entries = [
			["Creditors - _TC", 0.0, 100000.0, pi.posting_date],
			["Deferred Expense - _TC", 50000.0, 0.0, pi.posting_date],
			["Deferred Expense - _TC", 50000.0, 0.0, pi.posting_date],
		]
		check_gl_entries(
			self,
			pi.name,
			expected_gl_entries,
			pi.posting_date,
		)

	@change_settings("Global Defaults", {"default_currency": "INR"})
	def test_pi_with_tds_TC_B_151(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.buying.doctype.purchase_order.test_purchase_order import (
			create_new_account,
			get_company_or_supplier,
		)

		get_company_supplier = get_company_or_supplier()
		company = get_company_supplier.get("company")
		supplier = get_company_supplier.get("supplier")
		item = make_test_item("_test_item")
		warehouse = "Stores - TC-5"
		account = "TDS Payable - TC-5"
		if not frappe.db.exists("Account", account):
			account = create_new_account(
				account_name="TDS Payable",
				company=company,
				parent_account="Duties and Taxes - TC-5",
				account_type="Tax",
			)
		tax_category = frappe.get_doc(
			{
				"doctype": "Tax Withholding Category",
				"__newname": "test_tax_withholding_category",
				"rates": [
					{
						"from_date": get_year_start(getdate()),
						"to_date": get_year_ending(getdate()),
						"tax_withholding_rate": 2,
						"single_threshold": 1000,
						"cumulative_threshold": 100000,
					}
				],
				"accounts": [
					{
						"company": company,
						"account": account,
					}
				],
			}
		)
		tax_category.insert(ignore_if_duplicate=1, ignore_permissions=True)

		frappe.db.set_value("Supplier", supplier, "tax_withholding_category", tax_category.name)
		pi = frappe.get_doc(
			{
				"doctype": "Purchase Invoice",
				"supplier": supplier,
				"company": company,
				"posting_date": today(),
				"apply_tds": 1,
				"items": [
					{
						"item_code": item.item_code,
						"qty": 2,
						"rate": 500,
						"warehouse": warehouse,
					}
				],
			}
		)
		pi.bill_no = "test_bill_1122"
		pi.taxes_and_charges = ""
		pi.taxes = []
		pi.tax_withholding_category = tax_category.name
		pi.insert(ignore_permissions=True)
		pi.submit()

		self.assertEqual(pi.taxes[0].tax_amount, 20)
		self.assertEqual(pi.taxes_and_charges_deducted, 20)
		self.assertEqual(pi.grand_total, 980)

		self.assertEqual(pi.items[0].qty, 2)
		self.assertEqual(pi.items[0].rate, 500)

		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": pi.name, "company": company},
			fields=["account", "debit", "credit"],
		)

		tds_entry = next(entry for entry in gl_entries if entry["account"] == account)
		self.assertEqual(tds_entry["credit"], 20)
		self.assertEqual(tds_entry["debit"], 0)

		total_debit = sum(entry["debit"] for entry in gl_entries)
		total_credit = sum(entry["credit"] for entry in gl_entries)
		self.assertEqual(total_debit, total_credit)

		self.addCleanup(
			lambda: frappe.delete_doc("Purchase Invoice", pi.name, force=1, ignore_permissions=True)
		)
		self.addCleanup(
			lambda: frappe.delete_doc(
				"Tax Withholding Category", tax_category.name, force=1, ignore_permissions=True
			)
		)
		self.addCleanup(lambda: frappe.db.set_value("Supplier", supplier, "tax_withholding_category", ""))

	def test_repost_account_ledger_for_pi_TC_ACC_117(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.doctype.repost_accounting_ledger.test_repost_accounting_ledger import (
			update_repost_settings,
		)
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		update_repost_settings()
		company = "_Test Company"
		item = make_test_item("_Test Item")
		pi = make_purchase_invoice(
			supplier="_Test Supplier",
			company=company,
			item_code=item.name,
			rate=1000,
			qty=1,
		)
		ral = frappe.get_doc(
			{
				"doctype": "Repost Accounting Ledger",
				"company": company,
				"vouchers": [{"voucher_type": "Purchase Invoice", "voucher_no": pi.name}],
			}
		).insert(ignore_permissions=True)
		ral.submit()
		pi.items[0].expense_account = "_Test Account Stock Adjustment - _TC"
		pi.db_update()
		pi.submit()
		expected_gl_entries = [
			["Creditors - _TC", 0.0, pi.grand_total, pi.posting_date],
			["_Test Account Stock Adjustment - _TC", pi.grand_total, 0.0, pi.posting_date],
		]
		check_gl_entries(self, pi.name, expected_gl_entries, pi.posting_date)

	def test_over_billing_allowance_TC_ACC_119(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.buying.doctype.purchase_order.test_purchase_order import (
			create_purchase_order,
			get_or_create_fiscal_year,
		)

		get_or_create_fiscal_year("_Test Company")
		account_setting = frappe.get_doc("Accounts Settings")
		account_setting.db_set("over_billing_allowance", 10)
		account_setting.save(ignore_permissions=True)
		buying_setting = frappe.get_doc("Buying Settings")
		buying_setting.db_set("maintain_same_rate", 0)
		company = "_Test Company"
		item = make_test_item("_Test Item")
		po = create_purchase_order(
			supplier="_Test Supplier",
			company=company,
			item_code=item.name,
			rate=1000,
			qty=1,
		)
		po.submit()

		try:
			pi = make_pi_from_po(po.name)
			pi.items[0].rate = 1200
			pi.save(ignore_permissions=True)
			pi.submit()
		except Exception as e:
			error_msg = str(e)
			self.assertEqual(
				error_msg,
				'This document is over limit by Amount 100.0 for item _Test Item. Are you making another Purchase Invoice against the same Purchase Order Item?To allow over billing, update "Over Billing Allowance" in Accounts Settings or the Item.',
			)

	def test_promotion_scheme_for_buying_TC_ACC_114(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			create_records as records_for_pi,
		)
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import (
			make_test_item,
		)

		item = make_test_item("_Test Item Promotion")

		frappe.get_doc(
			{
				"doctype": "Promotional Scheme",
				"__newname": "_Test Promotional Scheme",
				"company": "_Test Company",
				"buying": 1,
				"valid_from": nowdate(),
				"valid_upto": add_days(nowdate(), 20),
				"currency": "INR",
				"items": [{"item_code": item.name, "uom": "Nos"}],
				"price_discount_slabs": [
					{
						"min_qty": "10",
						"max_qty": "100",
						"min_amount": 0,
						"max_amount": 0,
						"rate_or_discount": "Discount Percentage",
						"discount_percentage": 2,
						"rule_description": "2%",
					},
					{
						"min_qty": "101",
						"max_qty": "1000",
						"min_amount": 0,
						"max_amount": 0,
						"rate_or_discount": "Discount Percentage",
						"discount_percentage": 5,
						"rule_description": "5%",
					},
				],
			}
		).insert()

		_pi = make_purchase_invoice(
			supplier="_Test Supplier",
			item_code=item.name,
			qty=10,
			rate=1000,
			company="_Test Company",
			do_not_submit=True,
		)
		self.assertEqual(2, _pi.items[0].discount_percentage)

	def test_generate_purchase_invoice_with_items_different_gst_rates_TC_ACC_130(self):
		import json

		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		item = make_test_item("_Test GST Item")

		gst_rates = [
			{"rate": 5, "template": "GST 5%", "range": (500, 1000)},
			{"rate": 12, "template": "GST 12%", "range": (1001, 10000)},
			{"rate": 18, "template": "GST 18%", "range": (10001, 100000)},
		]
		for gst in gst_rates:
			if not frappe.db.exists("Item Tax Template", {"title": gst.get("template")}):
				frappe.get_doc(
					{
						"doctype": "Item Tax Template",
						"title": gst.get("template"),
						"company": "_Test Company",
						"gst_rate": gst.get("rate"),
						"taxes": [{"tax_type": "Marketing Expenses - _TC", "tax_rate": gst.get("rate")}],
					}
				).insert(ignore_permissions=True, ignore_if_duplicate=True)
		purchase_taxes_template = create_or_get_purchase_taxes_template("_Test Company")

		gst_rates = [
			{"rate": 5, "template": "GST 5% - _TC", "range": (500, 1000)},
			{"rate": 12, "template": "GST 12% - _TC", "range": (1001, 10000)},
			{"rate": 18, "template": "GST 18% - _TC", "range": (10001, 100000)},
		]
		if not item.taxes:
			for gst in gst_rates:
				item.append(
					"taxes",
					{
						"item_tax_template": gst["template"],
						"valid_from": frappe.utils.add_months(nowdate(), -1),
						"minimum_net_rate": gst["range"][0],
						"maximum_net_rate": gst["range"][1],
					},
				)
				item.save()
		rate_tax = [
			{"total_amount": 25, "total_tax": 5, "item_rate": 500},
			{"total_amount": 132, "total_tax": 12, "item_rate": 1100},
			{"total_amount": 1980, "total_tax": 18, "item_rate": 11000},
		]
		for rate in rate_tax:
			pi = make_purchase_invoice(
				supplier="_Test Supplier",
				company="_Test Company",
				item_code=item.name,
				qty=1,
				rate=rate.get("item_rate"),
				do_not_submit=True,
			)
			taxes = [
				{
					"charge_type": "On Net Total",
					"add_deduct_tax": "Add",
					"category": "Total",
					"rate": rate.get("total_tax") / 2,
					"account_head": purchase_taxes_template.get("sgst_account"),
					"description": "SGST",
				},
				{
					"charge_type": "On Net Total",
					"add_deduct_tax": "Add",
					"category": "Total",
					"rate": rate.get("total_tax") / 2,
					"account_head": purchase_taxes_template.get("cgst_account"),
					"description": "CGST",
				},
			]
			for tax in taxes:
				pi.append("taxes", tax)
			pi.save()
			total_tax = 0.0
			total_amount = 0.0
			for taxes in pi.taxes:
				item_wise_tax_detail = taxes.item_wise_tax_detail

				if isinstance(item_wise_tax_detail, str):
					item_wise_tax_detail = json.loads(item_wise_tax_detail)
				if "_Test GST Item" in item_wise_tax_detail:
					total_tax += item_wise_tax_detail["_Test GST Item"][0]
					total_amount += item_wise_tax_detail["_Test GST Item"][1]
			self.assertEqual(total_tax, rate.get("total_tax"))
			self.assertEqual(total_amount, rate.get("total_amount"))

	def test_direct_purchase_invoice_via_update_stock_TC_SCK_131(self):
		# Create Purchase Invoice with Update Stock
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company
		from erpnext.stock.doctype.item.test_item import make_item
		from erpnext.stock.utils import get_or_create_fiscal_year

		create_company()
		parent_warehouse = frappe.db.get_value(
			"Warehouse", {"is_group": 1, "company": "_Test Company"}, "name"
		)
		account = frappe.db.get_value("Account", {"company": "_Test Company"}, "name")
		cost_center = frappe.db.get_value("Cost Center", {"company": "_Test Company"}, "name")
		create_warehouse(
			warehouse_name="_Test Warehouse 1 - _TC",
			properties={"parent_warehouse": f"{parent_warehouse}"},
			company="_Test Company",
		)
		get_or_create_fiscal_year("_Test Company")
		create_supplier(supplier_name="_Test Supplier 1")
		warehouse = frappe.db.get_all("Warehouse", {"is_group": 0, "company": "_Test Company"}, ["name"])
		pi = make_purchase_invoice(
			supplier="_Test Supplier 1",
			item_code=create_item(
				item_code="Book", warehouse=warehouse[-1].name, company="_Test Company"
			).item_code,
			qty=5,
			update_stock=True,
			warehouse=warehouse[-1].name,
			supplier_warehouse=warehouse[0].name,
			uom="Box",
			cost_center=cost_center,
			expense_account=account,
			do_not_save=True,
		)
		pi.due_date = today()
		pi.save()
		pi.submit()

		# Check Stock Ledger Entries
		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": pi.name},
			fields=["item_code", "warehouse", "actual_qty", "stock_value_difference"],
		)
		self.assertEqual(len(sle), 1)
		self.assertEqual(sle[0].item_code, "Book")
		self.assertEqual(sle[0].warehouse, warehouse[-1].name)
		self.assertEqual(sle[0].actual_qty, 5)

		# Check Accounting Ledger Entries
		gl_entries = frappe.get_all(
			"GL Entry", filters={"voucher_no": pi.name}, fields=["account", "debit", "credit"]
		)
		self.assertTrue(gl_entries)
		expected_gl_entries = [
			{"account": "_Stock In Hand - _TC", "debit": pi.grand_total, "credit": 0},
			{"account": "Creditors - _TC", "debit": 0, "credit": pi.grand_total},
		]

		for gle in expected_gl_entries:
			for acccount in gl_entries:
				if acccount["account"] == gle["account"]:
					self.assertEqual(acccount["debit"], gle["debit"])
					self.assertEqual(acccount["credit"], gle["credit"])

	def test_supplier_invoice_number_uniqueness_validation_TC_ACC_136(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		account_setting = frappe.get_doc("Accounts Settings")
		account_setting.check_supplier_invoice_uniqueness = 1
		account_setting.save()
		item = make_test_item("_Test Item")

		pi = make_purchase_invoice(
			supplier="_Test Supplier",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			do_not_submit=True,
		)
		pi.bill_no = "ADF01234"
		pi.save()
		pi.submit()
		try:
			_pi = make_purchase_invoice(
				supplier="_Test Supplier",
				company="_Test Company",
				item_code=item.name,
				qty=1,
				rate=1000,
				do_not_submit=True,
			)
			_pi.bill_no = "ADF01234"
			_pi.save()
		except Exception as e:
			error_msg = str(e)
			self.assertEqual(error_msg, f"Supplier Invoice No exists in Purchase Invoice {pi.name}")

	def setUp(self):
		import random

		from erpnext.accounts.doctype.pricing_rule.test_pricing_rule import make_pricing_rule
		from erpnext.stock.doctype.item.test_item import make_item

		# Ensure supplier exists
		if not frappe.db.exists("Company", "_Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "_Test Company"
			company.default_currency = "INR"
			company.insert()

		supplier = create_supplier(
			supplier_name="Monica",
			supplier_type="Company",
		)

		if not frappe.db.exists("Supplier", supplier.supplier_name):
			supplier.insert(ignore_permissions=True)

			# Ensure Item exists with rate rules
		it_fields = {
			"item_name": "Boat Earpods",
			"is_stock_item": 1,
			"stock_uom": "Nos",
			"valuation_rate": 5000,
			"standard_rate": 5000,
		}

		item = make_item("Boat Earpods", it_fields).name
		if not frappe.db.exists("Item Price", {"item_code": item, "price_list": "Standard Buying"}):
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"price_list": "Standard Buying",
					"item_code": item,
					"price_list_rate": 5000,
				}
			).insert(ignore_permissions=True)

	def test_purchase_invoice_discount(self):
		if not frappe.db.exists("Pricing Rule", {"title": "Boat Earpods - Monica Discount", "disable": 0}):
			frappe.get_doc(
				{
					"doctype": "Pricing Rule",
					"title": "Boat Earpods - Monica Discount",
					"company": "_Test Company",
					"apply_on": "Item Code",
					"items": [{"item_code": "Boat Earpods"}],
					"rate_or_discount": "Discount Percentage",
					"discount_percentage": 10,
					"selling": 0,
					"buying": 1,
				}
			).insert()

		pi = make_purchase_invoice(
			company="_Test Company",
			supplier="Monica",
			posting_date="2024-12-15",
			update_stock=1,
			set_warehouse=create_warehouse("Stores-test", properties=None, company="_Test Company"),
			warehouse=create_warehouse("Stores-test", properties=None, company="_Test Company"),
			qty=20,
			rate=50000,
			item_code="Boat Earpods",
		)

		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": pi.name},
			fields=["actual_qty", "valuation_rate", "incoming_rate", "stock_value", "stock_value_difference"],
		)
		self.assertEqual(sle[0]["actual_qty"], 20)
		self.assertEqual(sle[0]["valuation_rate"], 45)

	def test_lcv_with_purchase_invoice_for_stock_item_TC_ACC_112(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		item = make_test_item("_Test Item10")
		item.is_stock_item = 1
		item.save(ignore_permissions=True)

		pi = make_purchase_invoice(
			supplier="_Test Supplier",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			do_not_submit=True,
			update_stock=True,
		)
		pi.submit()

		lvc = frappe.get_doc(
			{
				"doctype": "Landed Cost Voucher",
				"company": "_Test Company",
				"posting_date": pi.posting_date,
				"purchase_receipts": [
					{
						"receipt_document_type": "Purchase Invoice",
						"receipt_document": pi.name,
						"supplier": "_Test Supplier",
						"grand_total": pi.grand_total,
						"posting_date": pi.posting_date,
					}
				],
			}
		)
		lvc.get_items_from_purchase_receipts()
		lvc.append(
			"taxes",
			{
				"expense_account": "Expenses Included In Valuation - _TC",
				"amount": "300",
				"account_currency": "INR",
				"description": "test",
			},
		)
		lvc.save(ignore_permissions=True)
		lvc.submit()

		expected_gle = [
			["Creditors - _TC", 0.0, pi.grand_total, pi.posting_date],
			["_Test Account Cost for Goods Sold - _TC", 0.0, 300.0, pi.posting_date],
			["Stock In Hand - _TC", pi.grand_total + 300, 0.0, pi.posting_date],
		]

		self.assertEqual(expected_gle[0], ["Creditors - _TC", 0.0, 1000.0, frappe.utils.today()])
		self.assertEqual(
			expected_gle[1], ["_Test Account Cost for Goods Sold - _TC", 0.0, 300.0, frappe.utils.today()]
		)
		self.assertEqual(expected_gle[2], ["Stock In Hand - _TC", 1300.0, 0.0, frappe.utils.today()])

	def test_lcv_with_purchase_invoice_for_fixed_asset_item_TC_ACC_113(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item

		create_asset_data()
		item = make_test_item("_Test Asstes Item")

		if not item.is_fixed_asset:
			item.is_stock_item = 0
			item.is_fixed_asset = 1
			item.auto_create_assets = 1
			item.asset_category = "Test_Category"
			item.asset_naming_series = "ACC-ASS-.YYYY.-"
			item.flags.ignore_mandatory = 1
			item.save()
		pi = make_purchase_invoice(
			supplier="_Test Supplier",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			expense_account="CWIP Account - _TC",
			do_not_submit=True,
			update_stock=1,
			do_not_save=True,
		)

		pi.items[0].asset_location = "Test Location"

		pi.insert(ignore_permissions=True).submit()
		asset = frappe.get_value(
			"Asset",
			{"company": "_Test Company", "item_code": item.name, "asset_category": "Test_Category"},
			"name",
		)
		if asset:
			asset_doc = frappe.get_doc("Asset", asset)
			if not asset_doc.purchase_invoice or asset_doc.purchase_invoice != pi.name:
				asset_doc.purchase_invoice = pi.name
				asset_doc.available_for_use_date = nowdate()
				asset_doc.flags.ignore_mandatory = 1
				asset_doc.save()
		lvc = frappe.get_doc(
			{
				"doctype": "Landed Cost Voucher",
				"company": "_Test Company",
				"posting_date": pi.posting_date,
				"purchase_receipts": [
					{
						"receipt_document_type": "Purchase Invoice",
						"receipt_document": pi.name,
						"supplier": "_Test Supplier",
						"grand_total": pi.grand_total,
						"posting_date": pi.posting_date,
					}
				],
			}
		)

		lvc.get_items_from_purchase_receipts()
		lvc.append(
			"taxes",
			{
				"expense_account": "Expenses Included In Valuation - _TC",
				"amount": "300",
				"account_currency": "INR",
				"description": "test",
			},
		)

		lvc.save()
		lvc.submit()

		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Purchase Invoice", "voucher_no": pi.name, "is_cancelled": 0},
			fields=["account", "debit", "credit", "posting_date"],
			order_by="posting_date, account, creation",
		)

		expected_gle = [[gle.account, gle.debit, gle.credit, gle.posting_date] for gle in gl_entries]

		check_gl_entries(self, pi.name, expected_gle=expected_gle, posting_date=pi.posting_date)

	def test_payment_term_discount_for_pi_at_fully_paid_TC_ACC_098(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		if not frappe.db.exists("Payment Term", "_Test Discount Term"):
			frappe.get_doc(
				{
					"doctype": "Payment Term",
					"payment_term_name": "_Test Discount Term",
					"invoice_portion": 100,
					"mode_of_payment": "Cash",
					"discount_type": "Percentage",
					"due_date_based_on": "Day(s) after invoice date",
					"discount": 10,
				}
			).insert(ignore_permissions=True)

		item = make_test_item("_Test Item")

		pi = make_purchase_invoice(
			supplier="_Test Supplier",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			do_not_submit=True,
			do_not_save=True,
		)

		pi.append(
			"payment_schedule",
			{
				"payment_term": "_Test Discount Term",
				"due_date": add_days(nowdate(), 1),
				"invoice_portion": 100,
				"payment_amount": pi.grand_total,
				"discount_date": add_days(nowdate(), 1),
			},
		)
		pi.insert(ignore_permissions=True).submit()
		pe = get_payment_entry(pi.doctype, pi.name, bank_account="Cash - _TC", reference_date=nowdate())
		pe.reference_no = "1"
		pe.deductions[0].account = "_Test Account Discount - _TC"
		pe.save(ignore_permissions=True).submit()
		expected_gle = [
			["Cash - _TC", 0.0, (pi.grand_total - pi.grand_total * 0.1), nowdate()],
			["Creditors - _TC", pi.grand_total, 0.0, nowdate()],
			["_Test Account Discount - _TC", 0.0, pi.grand_total * 0.1, nowdate()],
		]
		check_gl_entries(
			self,
			voucher_no=pe.name,
			expected_gle=expected_gle,
			posting_date=nowdate(),
			voucher_type="Payment Entry",
		)

	def test_payment_term_discount_for_pi_at_partially_paid_TC_ACC_100(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		if not frappe.db.exists("Payment Term", "_Test partially Discount Term"):
			frappe.get_doc(
				{
					"doctype": "Payment Term",
					"payment_term_name": "_Test partially Discount Term",
					"invoice_portion": 70,
					"mode_of_payment": "Cash",
					"discount_type": "Percentage",
					"due_date_based_on": "Day(s) after invoice date",
					"discount": 5,
				}
			).insert()

		item = make_test_item("_Test Item")

		pi = make_purchase_invoice(
			supplier="_Test Supplier",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=1000,
			do_not_submit=True,
			do_not_save=True,
		)

		pi.append(
			"payment_schedule",
			{
				"payment_term": "_Test partially Discount Term",
				"due_date": add_days(nowdate(), 1),
				"invoice_portion": 70,
				"payment_amount": 1000 * 0.7,
				"discount_date": add_days(nowdate(), 1),
			},
		)

		pi.insert(ignore_permissions=True).submit()
		pe = get_payment_entry(pi.doctype, pi.name, bank_account="Cash - _TC", reference_date=nowdate())
		pe.reference_no = "1"
		pe.deductions[0].account = "_Test Account Discount - _TC"

		pe.save().submit()

		expected_gle = [
			["Cash - _TC", 0.0, (pi.grand_total - pi.grand_total * 0.05), nowdate()],
			["Creditors - _TC", pi.grand_total, 0.0, nowdate()],
			["_Test Account Discount - _TC", 0.0, pi.grand_total * 0.05, nowdate()],
		]

		check_gl_entries(
			self,
			voucher_no=pe.name,
			expected_gle=expected_gle,
			posting_date=nowdate(),
			voucher_type="Payment Entry",
		)

	def test_stop_pi_creation_when_value_exceeds_budget_TC_ACC_133(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.utils import get_fiscal_year
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		year = get_fiscal_year(date=nowdate(), company="_Test Company")[0]
		company = frappe.get_doc("Company", "_Test Company")
		if company.stock_received_but_not_billed != "Cost of Goods Sold - _TC":
			company.stock_received_but_not_billed = "Cost of Goods Sold - _TC"
			company.save()

		budget = (
			frappe.get_doc(
				{
					"doctype": "Budget",
					"budget_against": "Cost Center",
					"company": "_Test Company",
					"cost_center": "_Test Write Off Cost Center - _TC",
					"fiscal_year": year,
					"applicable_on_purchase_order": 1,
					"action_if_annual_budget_exceeded_on_po": "Stop",
					"action_if_accumulated_monthly_budget_exceeded_on_po": "Stop",
					"applicable_on_booking_actual_expenses": 1,
					"action_if_annual_budget_exceeded": "Stop",
					"action_if_accumulated_monthly_budget_exceeded": "Stop",
					"accounts": [{"account": "Cost of Goods Sold - _TC", "budget_amount": 10000}],
				}
			)
			.insert()
			.submit()
		)

		item = make_test_item("_Test Item")
		try:
			pi = make_purchase_invoice(
				supplier="_Test Supplier",
				company="_Test Company",
				item_code=item.name,
				qty=1,
				rate=11000,
				expense_account="Cost of Goods Sold - _TC",
				do_not_submit=True,
			)

			pi.cost_center = "_Test Write Off Cost Center - _TC"
			pi.items[0].cost_center = "_Test Write Off Cost Center - _TC"

			pi.save().submit()
		except Exception as e:
			print(str(e))
			self.assertEqual(
				str(e),
				"""Annual Budget for Account Cost of Goods Sold - _TC against Cost Center _Test Write Off Cost Center - _TC is ₹ 10,000.00. It will be exceed by ₹ 1,000.00Total Expenses booked through - Actual Expenses - ₹ 0.00Material Requests - ₹ 0.00Unbilled Orders - ₹ 0.00""",
			)

			budget.cancel()
			budget.load_from_db()
			pi.cancel()
			pi.load_from_db()
			frappe.delete_doc("Budget", budget.name, force=1)
			frappe.delete_doc("Purchase Invoice", pi.name, force=1)

	def test_warn_pi_creation_when_value_exceeds_budget_TC_ACC_145(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import make_test_item
		from erpnext.accounts.utils import get_fiscal_year
		from erpnext.stock.utils import get_or_create_fiscal_year

		get_or_create_fiscal_year("_Test Company")
		year = get_fiscal_year(date=nowdate(), company="_Test Company")[0]
		company = frappe.get_doc("Company", "_Test Company")
		if company.stock_received_but_not_billed != "Cost of Goods Sold - _TC":
			company.stock_received_but_not_billed = "Cost of Goods Sold - _TC"
			company.save()

		budget = (
			frappe.get_doc(
				{
					"doctype": "Budget",
					"budget_against": "Cost Center",
					"company": "_Test Company",
					"cost_center": "_Test Write Off Cost Center - _TC",
					"fiscal_year": year,
					"applicable_on_purchase_order": 1,
					"action_if_annual_budget_exceeded_on_po": "Warn",
					"action_if_accumulated_monthly_budget_exceeded_on_po": "Warn",
					"applicable_on_booking_actual_expenses": 1,
					"action_if_annual_budget_exceeded": "Warn",
					"action_if_accumulated_monthly_budget_exceeded": "Warn",
					"accounts": [{"account": "Cost of Goods Sold - _TC", "budget_amount": 10000}],
				}
			)
			.insert()
			.submit()
		)

		item = make_test_item("_Test Item")

		pi = make_purchase_invoice(
			supplier="_Test Supplier",
			company="_Test Company",
			item_code=item.name,
			qty=1,
			rate=11000,
			expense_account="Cost of Goods Sold - _TC",
			do_not_submit=True,
		)

		pi.cost_center = "_Test Write Off Cost Center - _TC"
		pi.items[0].cost_center = "_Test Write Off Cost Center - _TC"

		pi.save().submit()
		budget_exceeded_found = False

		for msg in frappe.get_message_log():
			if msg.get("title") == "Budget Exceeded" and msg.get("indicator") == "orange":
				if "Annual Budget for Account" in msg.get("message", ""):
					budget_exceeded_found = True
					break

		self.assertTrue(budget_exceeded_found, "Budget exceeded message not found")
		budget.cancel()
		budget.load_from_db()
		pi.cancel()
		pi.load_from_db()
		frappe.delete_doc("Budget", budget.name, force=1)
		frappe.delete_doc("Purchase Order", pi.name, force=1)

	def test_trx_currency_debit_credit_for_high_precision(self):
		exc_rate = 0.737517516
		pi = make_purchase_invoice(
			currency="USD", conversion_rate=exc_rate, qty=1, rate=2000, do_not_save=True
		)
		pi.supplier = "_Test Supplier USD"
		pi.save().submit()

		expected = (
			("_Test Account Cost for Goods Sold - _TC", 1475.04, 0.0, 2000.0, 0.0, "USD", exc_rate),
			("_Test Payable USD - _TC", 0.0, 1475.04, 0.0, 2000.0, "USD", exc_rate),
		)

		actual = frappe.db.get_all(
			"GL Entry",
			filters={"voucher_no": pi.name},
			fields=[
				"account",
				"debit",
				"credit",
				"debit_in_transaction_currency",
				"credit_in_transaction_currency",
				"transaction_currency",
				"transaction_exchange_rate",
			],
			order_by="account",
			as_list=1,
		)
		self.assertEqual(actual, expected)

	def test_prevents_fully_returned_invoice_with_zero_quantity(self):
		from erpnext.controllers.sales_and_purchase_return import StockOverReturnError, make_return_doc

		invoice = make_purchase_invoice(qty=10)

		return_doc = make_return_doc(invoice.doctype, invoice.name)
		return_doc.items[0].qty = -10
		return_doc.save().submit()

		return_doc = make_return_doc(invoice.doctype, invoice.name)
		return_doc.items[0].qty = 0

		self.assertRaises(StockOverReturnError, return_doc.save)

	def test_apply_discount_on_grand_total(self):
		"""
		To test if after applying discount on grand total,
		the grand total is calculated correctly without any rounding errors
		"""
		invoice = make_purchase_invoice(qty=3, rate=100, do_not_save=True, do_not_submit=True)
		invoice.append(
			"items",
			{
				"item_code": "_Test Item",
				"qty": 3,
				"rate": 50.3,
			},
		)
		invoice.append(
			"taxes",
			{
				"charge_type": "On Net Total",
				"account_head": "_Test Account VAT - _TC",
				"description": "VAT",
				"rate": 15,
			},
		)

		# the grand total here will be 518.54
		invoice.disable_rounded_total = 1
		# apply discount on grand total to adjust the grand total to 518
		invoice.discount_amount = 0.54

		invoice.save()

		# check if grand total is 518 and not something like 517.99 due to rounding errors
		self.assertEqual(invoice.grand_total, 518)

	def test_apply_discount_on_grand_total_with_previous_row_total_tax(self):
		"""
		To test if after applying discount on grand total,
		where the tax is calculated on previous row total, the grand total is calculated correctly
		"""

		invoice = make_purchase_invoice(qty=2, rate=100, do_not_save=True, do_not_submit=True)
		invoice.extend(
			"taxes",
			[
				{
					"charge_type": "Actual",
					"account_head": "_Test Account VAT - _TC",
					"description": "VAT",
					"tax_amount": 100,
				},
				{
					"charge_type": "On Previous Row Amount",
					"account_head": "_Test Account VAT - _TC",
					"description": "VAT",
					"row_id": 1,
					"rate": 10,
				},
				{
					"charge_type": "On Previous Row Total",
					"account_head": "_Test Account VAT - _TC",
					"description": "VAT",
					"row_id": 1,
					"rate": 10,
				},
			],
		)

		# the total here will be 340, so applying 40 discount
		invoice.discount_amount = 40
		invoice.save()

		self.assertEqual(invoice.grand_total, 300)

	def test_pr_pi_over_billing(self):
		from erpnext.stock.doctype.purchase_receipt.purchase_receipt import (
			make_purchase_invoice as make_purchase_invoice_from_pr,
		)

		# Configure Buying Settings to allow rate change
		frappe.db.set_single_value("Buying Settings", "maintain_same_rate", 0)

		pr = make_purchase_receipt(qty=10, rate=10)
		pi = make_purchase_invoice_from_pr(pr.name)

		pi.items[0].rate = 12

		# Test 1 - This will fail because over billing is not allowed
		self.assertRaises(frappe.ValidationError, pi.submit)

		frappe.db.set_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate", 1)
		# Test 2 - This will now submit because over billing allowance is ignored when set_landed_cost_based_on_purchase_invoice_rate is checked
		pi.submit()

		frappe.db.set_single_value("Buying Settings", "set_landed_cost_based_on_purchase_invoice_rate", 0)
		frappe.db.set_single_value("Accounts Settings", "over_billing_allowance", 20)
		pi.cancel()
		pi = make_purchase_invoice_from_pr(pr.name)
		pi.items[0].rate = 12

		# Test 3 - This will now submit because over billing is allowed upto 20%
		pi.submit()

		pi.reload()
		pi.cancel()
		pi = make_purchase_invoice_from_pr(pr.name)
		pi.items[0].rate = 13

		# Test 4 - Since this PI is overbilled by 130% and only 120% is allowed, it will fail
		self.assertRaises(frappe.ValidationError, pi.submit)

	def test_discount_percentage_not_set_when_amount_is_manually_set(self):
		pi = make_purchase_invoice(do_not_save=True)
		discount_amount = 7
		pi.discount_amount = discount_amount
		pi.save()
		self.assertEqual(pi.additional_discount_percentage, None)
		pi.set_posting_time = 1
		pi.posting_date = add_days(today(), -1)
		pi.save()
		self.assertEqual(pi.discount_amount, discount_amount)

	@if_app_installed("projects")
	def test_validate_available_budget_TC_ACC_292(self):
		from unittest.mock import patch

		project_name = "test_project" + frappe.generate_hash(length=5)
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert(ignore_permissions=True)

		project = frappe.db.get_value("Project", {"project_name": project_name})

		wbs = frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"project": project,
				"wbs_name": "test_wbs",
				"company": "_Test Company",
				"gl_account": "Cash - _TC",
			}
		)
		wbs.insert(ignore_permissions=True)
		wbs.submit()

		self.assertEqual(wbs.docstatus, 1)

		zero_budget = frappe.get_doc(
			{
				"doctype": "Zero Budget",
				"project": project,
				"posting_date": today(),
				"zero_budget_item": [{"wbs_element": wbs.name, "zero_budget": 100}],
			}
		)
		zero_budget.insert(ignore_permissions=True)
		zero_budget.submit()

		self.assertEqual(wbs.docstatus, 1)

		wbs.load_from_db()

		wbs_1 = frappe.copy_doc(wbs)
		wbs_1.insert(ignore_permissions=True)
		wbs_1.submit()

		with patch("frappe.msgprint") as mock_msgprint:
			args = {"qty": 1, "rate": 200, "do_not_submit": True}
			pi = make_purchase_invoice(**args)
			pi.items[0].work_breakdown_structure = wbs.name
			pi.save()

			self.assertTrue(mock_msgprint.called)
			msg_args, _ = mock_msgprint.call_args
			self.assertIn("Available Budget Limit Exceeded", msg_args[0])

			pi.append(
				"items",
				{
					"item_code": "_Test Item",
					"rate": 200,
					"qty": 1,
					"warehouse": "_Test Warehouse - _TC",
					"work_breakdown_structure": wbs_1.name,
				},
			)
			pi.save()
			self.assertTrue(mock_msgprint.called)
			msg_args, _ = mock_msgprint.call_args
			self.assertIn("Available Budget Limit Exceeded", msg_args[0])

	@if_app_installed("projects")
	def test_update_actual_overall_budget_TC_ACC_293(self):
		project_name = "test_project" + frappe.generate_hash(length=5)
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert()

		project = frappe.db.get_value("Project", {"project_name": project_name})

		wbs = frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"project": project,
				"wbs_name": "test_wbs",
				"company": "_Test Company",
				"gl_account": "Cash - _TC",
			}
		)
		wbs.insert()
		wbs.submit()

		self.assertEqual(wbs.docstatus, 1)

		zero_budget = frappe.get_doc(
			{
				"doctype": "Zero Budget",
				"project": project,
				"posting_date": today(),
				"zero_budget_item": [{"wbs_element": wbs.name, "zero_budget": 100}],
			}
		)
		zero_budget.insert()
		zero_budget.submit()

		self.assertEqual(wbs.docstatus, 1)

		args = {"qty": 1, "rate": 200, "do_not_submit": True}
		pi = make_purchase_invoice(**args)
		pi.items[0].work_breakdown_structure = wbs.name
		pi.save()
		pi.submit()
		self.assertEqual(pi.docstatus, 1)

		pi.load_from_db()
		pi.cancel()

	@if_app_installed("projects")
	def test_update_locked_actual_overall_budgets_TC_ACC_294(self):
		project_name = "test_project" + frappe.generate_hash(length=5)
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert()

		project = frappe.db.get_value("Project", {"project_name": project_name})

		wbs = frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"project": project,
				"wbs_name": "test_wbs",
				"company": "_Test Company",
				"gl_account": "Cash - _TC",
			}
		)
		wbs.insert()
		wbs.submit()

		self.assertEqual(wbs.docstatus, 1)

		zero_budget = frappe.get_doc(
			{
				"doctype": "Zero Budget",
				"project": project,
				"posting_date": today(),
				"zero_budget_item": [{"wbs_element": wbs.name, "zero_budget": 100}],
			}
		)
		zero_budget.insert()
		zero_budget.submit()

		self.assertEqual(wbs.docstatus, 1)
		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 1)

		args = {"qty": 1, "rate": 100, "do_not_submit": True}
		pi = make_purchase_invoice(**args)
		pi.items[0].work_breakdown_structure = wbs.name
		pi.save()
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			pi.submit()

		self.assertIn("this WBS is locked", str(cm.exception))

		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 0)
		pi.submit()
		self.assertEqual(pi.docstatus, 1)

		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 1)
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			pi.cancel()

		self.assertIn("this WBS is locked", str(cm.exception))

	@if_app_installed("projects")
	def test_locked_committed_overall_budget_po_to_pi_TC_ACC_295(self):
		from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order

		project_name = "test_project" + frappe.generate_hash(length=5)
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert()

		project = frappe.db.get_value("Project", {"project_name": project_name})

		wbs = frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"project": project,
				"wbs_name": "test_wbs",
				"company": "_Test Company",
				"gl_account": "Cash - _TC",
			}
		)
		wbs.insert()
		wbs.submit()

		self.assertEqual(wbs.docstatus, 1)

		zero_budget = frappe.get_doc(
			{
				"doctype": "Zero Budget",
				"project": project,
				"posting_date": today(),
				"zero_budget_item": [{"wbs_element": wbs.name, "zero_budget": 100}],
			}
		)
		zero_budget.insert()
		zero_budget.submit()

		args = {"qty": 1, "rate": 100, "do_not_save": True}
		po = create_purchase_order(**args)
		po.insert(ignore_permissions=True)
		po.submit()
		self.assertEqual(po.docstatus, 1)

		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 1)
		po = make_purchase_invoice(po.name)
		po.items[0].work_breakdown_structure = wbs.name
		po.save()
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			po.submit()

		self.assertIn("this WBS is locked", str(cm.exception))

		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 0)
		po.submit()
		self.assertEqual(po.docstatus, 1)

		frappe.db.set_value("Work Breakdown Structure", wbs.name, "locked", 1)
		with self.assertRaises(frappe.exceptions.ValidationError) as cm:
			po.cancel()

		self.assertIn("this WBS is locked", str(cm.exception))

	@change_settings("Buying Settings", {"po_required": "Yes"})
	def test_po_required_in_pi_TC_ACC_319(self):
		args = {"qty": 1, "rate": 200, "do_not_save": True}
		pi = make_purchase_invoice(**args)
		with self.assertRaises(frappe.ValidationError) as cm:
			pi.insert(ignore_permissions=True)
		self.assertIn(
			"Purchase Order Required for item _Test ItemTo submit the invoice without purchase order please set Purchase Order Required as No in Buying Settings",
			str(cm.exception),
		)

	@change_settings("Buying Settings", {"pr_required": "Yes"})
	def test_pr_required_in_pi_TC_ACC_309(self):
		args = {"qty": 1, "rate": 200, "do_not_save": True}
		pi = make_purchase_invoice(**args)
		with self.assertRaises(frappe.ValidationError) as cm:
			pi.insert(ignore_permissions=True)
		self.assertIn(
			"Purchase Receipt Required for item _Test ItemTo submit the invoice without purchase receipt please set Purchase Receipt Required as No in Buying Settings",
			str(cm.exception),
		)

	def test_validate_write_off_account_TC_ACC_310(self):
		args = {"qty": 1, "rate": 200, "do_not_save": True}
		pi = make_purchase_invoice(**args)
		pi.write_off_amount = 100
		pi.write_off_account = ""
		with self.assertRaises(frappe.ValidationError) as cm:
			pi.save()
		self.assertIn("Please enter Write Off Account", str(cm.exception))

	def test_validate_supplier_invoice_date_TC_ACC_311(self):
		args = {"qty": 1, "rate": 200, "do_not_save": True}
		pi = make_purchase_invoice(**args)
		pi.posting_date = today()
		pi.bill_date = add_days(today(), 1)
		with self.assertRaises(frappe.ValidationError) as cm:
			pi.save()
		self.assertIn("Supplier Invoice Date cannot be greater than Posting Date", str(cm.exception))

	def test_block_and_unblock_purchase_invoice_TC_ACC_312(self):
		from .purchase_invoice import block_invoice, change_release_date, unblock_invoice

		args = {"qty": 1, "rate": 200, "do_not_save": True}
		pi = make_purchase_invoice(**args)
		pi.insert(ignore_permissions=True)
		pi.submit()

		block_invoice(pi.name, release_date=today(), hold_comment="Test Comment")
		pi.load_from_db()

		self.assertEqual(pi.on_hold, 1)
		self.assertEqual(pi.docstatus, 1)

		unblock_invoice(pi.name)
		pi.load_from_db()

		self.assertEqual(pi.on_hold, 0)
		self.assertEqual(pi.docstatus, 1)

		change_release_date(name=pi.name, release_date=add_days(today(), 1))
		pi.load_from_db()
		self.assertEqual(getdate(pi.release_date), getdate(add_days(today(), 1)))

	def test_get_list_context_313(self):
		from .purchase_invoice import get_list_context

		data = get_list_context()
		self.assertTrue(data.get("title"), "Purchase Invoices")
		self.assertTrue(data.get("no_breadcrumbs"), True)
		self.assertTrue(data.get("show_sidebar"), True)
		self.assertTrue(data.get("show_search"), True)

	def test_check_prev_docstatus_314(self):
		from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
		from erpnext.stock.doctype.purchase_receipt.test_purchase_receipt import make_purchase_receipt

		po = create_purchase_order(do_not_save=True)
		po.insert(ignore_permissions=True)

		pi = make_purchase_invoice(do_not_save=True)
		pi.items[0].purchase_order = po.name
		pi.insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError) as cm:
			pi.submit()
		self.assertIn(f"{po.doctype} {po.name} is not submitted", str(cm.exception))

		pr = make_purchase_receipt(do_not_save=True)
		pr.insert(ignore_permissions=True)

		pi_1 = make_purchase_invoice(do_not_save=True)
		pi_1.items[0].purchase_receipt = pr.name
		pi_1.insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError) as cm:
			pi_1.submit()
		self.assertIn(f"{pr.doctype} {pr.name} is not submitted", str(cm.exception))

	def test_make_write_off_gl_entry_with_writeoff_account_TC_ACC_315(self):
		args = {"qty": 1, "rate": 200, "do_not_save": True}
		pi = make_purchase_invoice(**args)
		pi.write_off_amount = 100
		pi.write_off_account = "Cash - _TC"
		pi.insert(ignore_permissions=True)
		pi.submit()

		self.assertEqual(pi.status, "Partly Paid")
		self.assertEqual(pi.docstatus, 1)

	def test_create_remarks_TC_ACC_316(self):
		args = {"qty": 1, "rate": 200, "do_not_save": True}
		pi = make_purchase_invoice(**args)
		pi.remarks = ""
		pi.bill_no = "test-1122"
		pi.bill_date = today()
		pi.insert(ignore_permissions=True)
		pi.submit()
		self.assertEqual(pi.remarks, f"Against Supplier Invoice {pi.bill_no} dated {formatdate(today())}")

	def test_validate_credit_to_acc_TC_ACC_317(self):
		from erpnext.accounts.doctype.account.test_account import create_account

		account = create_account(
			account_name="Deferred Expense", parent_account="Current Assets - _TC", company="_Test Company"
		)
		args = {"qty": 1, "rate": 200, "do_not_save": True}
		pi = make_purchase_invoice(**args)
		pi.credit_to = account
		with self.assertRaises(frappe.ValidationError) as cm:
			pi.insert(ignore_mandatory=True)
		self.assertIn(
			"Please ensure that the Credit To account Deferred Expense - _TC is a Payable account. You can change the account type to Payable or select a different account.",
			str(cm.exception),
		)


def set_advance_flag(company, flag, default_account):
	frappe.db.set_value(
		"Company",
		company,
		{
			"book_advance_payments_in_separate_party_account": flag,
			"default_advance_paid_account": default_account,
		},
	)


def check_gl_entries(
	doc,
	voucher_no,
	expected_gle,
	posting_date,
	voucher_type="Purchase Invoice",
	additional_columns=None,
):
	gl = frappe.qb.DocType("GL Entry")
	query = (
		frappe.qb.from_(gl)
		.select(gl.account, gl.debit, gl.credit, gl.posting_date)
		.where(
			(gl.voucher_type == voucher_type)
			& (gl.voucher_type == "Landed Cost Voucher")
			& (gl.voucher_no == voucher_no)
			& (gl.posting_date >= posting_date)
			& (gl.is_cancelled == 0)
		)
		.orderby(gl.posting_date, gl.account, gl.creation)
	)

	if additional_columns:
		for col in additional_columns:
			query = query.select(gl[col])
	gl_entries = query.run(as_dict=True)
	for i, gle in enumerate(gl_entries):
		doc.assertEqual(expected_gle[i][0], gle.account)
		doc.assertEqual(expected_gle[i][1], gle.debit)
		doc.assertEqual(expected_gle[i][2], gle.credit)
		doc.assertEqual(getdate(expected_gle[i][3]), gle.posting_date)

		if additional_columns:
			j = 4
			for col in additional_columns:
				doc.assertEqual(expected_gle[i][j], gle[col])
				j += 1


def create_tax_witholding_category(category_name, company, account):
	from erpnext.accounts.utils import get_fiscal_year

	fiscal_year = get_fiscal_year(date=nowdate())

	return frappe.get_doc(
		{
			"doctype": "Tax Withholding Category",
			"name": category_name,
			"category_name": category_name,
			"accounts": [{"company": company, "account": account}],
			"rates": [
				{
					"from_date": fiscal_year[1],
					"to_date": fiscal_year[2],
					"tax_withholding_rate": 10,
					"single_threshold": 2500,
					"cumulative_threshold": 0,
				}
			],
		}
	).insert(ignore_if_duplicate=True)


def unlink_payment_on_cancel_of_invoice(enable=1):
	accounts_settings = frappe.get_doc("Accounts Settings")
	accounts_settings.unlink_payment_on_cancellation_of_invoice = enable
	accounts_settings.save(ignore_permissions=True)


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
		pi.cash_bank_account = args.cash_bank_account

	pi.company = args.company or "_Test Company"
	pi.supplier = args.supplier or "_Test Supplier"
	pi.currency = args.currency or "INR"
	pi.conversion_rate = args.conversion_rate or 1
	pi.is_return = args.is_return
	pi.return_against = args.return_against
	pi.is_subcontracted = args.is_subcontracted or 0
	pi.supplier_warehouse = args.supplier_warehouse or "_Test Warehouse 1 - _TC"
	pi.cost_center = args.parent_cost_center
	pi.apply_discount_on = args.apply_discount_on or None
	pi.additional_discount_percentage = args.additional_discount_percentage or None

	bundle_id = None
	if not args.use_serial_batch_fields and (args.get("batch_no") or args.get("serial_no")):
		batches = {}
		qty = args.qty if args.qty is not None else 5
		item_code = args.item or args.item_code or "_Test Item"
		if args.get("batch_no"):
			batches = frappe._dict({args.batch_no: qty})

		serial_nos = args.get("serial_no") or []

		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": item_code,
					"warehouse": args.warehouse or "_Test Warehouse - _TC",
					"qty": qty,
					"batches": batches,
					"voucher_type": "Purchase Invoice",
					"serial_nos": serial_nos,
					"type_of_transaction": "Inward",
					"posting_date": args.posting_date or today(),
					"posting_time": args.posting_time,
				}
			)
		).name

	pi.append(
		"items",
		{
			"item_code": args.item or args.item_code or "_Test Item",
			"item_name": args.item_name,
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"qty": args.qty if args.qty is not None else 5,
			"received_qty": args.received_qty or 0,
			"rejected_qty": args.rejected_qty or 0,
			"rate": args.rate or 50,
			"price_list_rate": args.price_list_rate or 50,
			"expense_account": args.expense_account or "_Test Account Cost for Goods Sold - _TC",
			"discount_account": args.discount_account or None,
			"discount_amount": args.discount_amount or 0,
			"conversion_factor": 1.0,
			"serial_and_batch_bundle": bundle_id,
			"stock_uom": args.uom or "_Test UOM",
			"cost_center": args.cost_center or "_Test Cost Center - _TC",
			"project": args.project,
			"rejected_warehouse": args.rejected_warehouse or "",
			"asset_location": args.location or "",
			"allow_zero_valuation_rate": args.get("allow_zero_valuation_rate") or 0,
			"use_serial_batch_fields": args.get("use_serial_batch_fields") or 0,
			"batch_no": args.get("batch_no") if args.get("use_serial_batch_fields") else "",
			"serial_no": args.get("serial_no") if args.get("use_serial_batch_fields") else "",
		},
	)

	if args.get_taxes_and_charges:
		taxes = get_taxes()
		for tax in taxes:
			pi.append("taxes", tax)

	if not args.do_not_save:
		pi.insert(ignore_permissions=True)
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
		pi.cash_bank_account = args.cash_bank_account

	pi.company = args.company or "_Test Company"
	pi.cost_center = args.cost_center or "_Test Cost Center - _TC"
	pi.supplier = args.supplier or "_Test Supplier"
	pi.currency = args.currency or "INR"
	pi.conversion_rate = args.conversion_rate or 1
	pi.is_return = args.is_return
	pi.is_return = args.is_return
	pi.credit_to = args.return_against or "Creditors - _TC"
	pi.is_subcontracted = args.is_subcontracted or 0
	if args.supplier_warehouse:
		pi.supplier_warehouse = "_Test Warehouse 1 - _TC"

	bundle_id = None
	if args.get("batch_no") or args.get("serial_no"):
		batches = {}
		qty = args.qty or 5
		item_code = args.item or args.item_code or "_Test Item"
		if args.get("batch_no"):
			batches = frappe._dict({args.batch_no: qty})

		serial_nos = args.get("serial_no") or []

		bundle_id = make_serial_batch_bundle(
			frappe._dict(
				{
					"item_code": item_code,
					"warehouse": args.warehouse or "_Test Warehouse - _TC",
					"qty": qty,
					"batches": batches,
					"voucher_type": "Purchase Receipt",
					"serial_nos": serial_nos,
					"posting_date": args.posting_date or today(),
					"posting_time": args.posting_time,
				}
			)
		).name

	pi.append(
		"items",
		{
			"item_code": args.item or args.item_code or "_Test Item",
			"warehouse": args.warehouse or "_Test Warehouse - _TC",
			"qty": args.qty or 5,
			"received_qty": args.received_qty or 0,
			"rejected_qty": args.rejected_qty or 0,
			"rate": args.rate or 50,
			"conversion_factor": 1.0,
			"serial_and_batch_bundle": bundle_id,
			"stock_uom": "_Test UOM",
			"cost_center": args.cost_center or "_Test Cost Center - _TC",
			"project": args.project,
			"rejected_warehouse": args.rejected_warehouse or "",
		},
	)
	if not args.do_not_save:
		pi.insert(ignore_permissions=True)
		if not args.do_not_submit:
			pi.submit()
	return pi


def setup_provisional_accounting(**args):
	args = frappe._dict(args)
	create_item("_Test Non Stock Item", is_stock_item=0)
	company = args.company or "_Test Company"
	provisional_account = create_account(
		account_name=args.account_name or "Provision Account",
		parent_account=args.parent_account or "Current Liabilities - _TC",
		company=company,
	)
	toggle_provisional_accounting_setting(enable=1, company=company, provisional_account=provisional_account)


def toggle_provisional_accounting_setting(**args):
	args = frappe._dict(args)
	company = frappe.get_doc("Company", args.company or "_Test Company")
	company.enable_provisional_accounting_for_non_stock_items = args.enable or 0
	company.default_provisional_account = args.provisional_account
	company.save()


test_records = frappe.get_test_records("Purchase Invoice")


def update_ldc_details(supplier):
	if supplier:
		supplier.custom_lower_tds_deduction_applicable = "Yes"
		if frappe.db.has_column("Supplier", "pan"):
			if not supplier.pan:
				supplier.pan = "DAJPC4150P"
			supplier.flags.ignore_mandatory = True
			supplier.save()


def create_ldc(supplier):
	from erpnext.accounts.utils import get_fiscal_year

	fiscal_year, valid_from, valid_upto = get_fiscal_year(date=nowdate())

	if not frappe.db.exists("Lower Deduction Certificate", "LTC12345 Test"):
		doc = frappe.get_doc(
			{
				"doctype": "Lower Deduction Certificate",
				"tax_withholding_category": "Test - TDS - 194C - Company",
				"company": "_Test Company",
				"supplier": supplier,
				"certificate_no": "LTC12345 Test",
				"fiscal_year": fiscal_year,
				"valid_from": valid_from,
				"valid_upto": valid_upto,
				"rate": 1,
				"certificate_limit": 40000,
				"pan_no": "HYRDG4553R",
			}
		).insert(ignore_permissions=True)

		return doc
	else:
		return frappe.get_doc("Lower Deduction Certificate", "LTC12345 Test")


def get_jv_entry_account(**args):
	jea_parent = frappe.db.get_all(
		"Journal Entry Account",
		filters={
			"account": args.get("credit_to"),
			"docstatus": 1,
			"reference_name": args.get("reference_name"),
			"party_type": args.get("party_type"),
			"party": args.get("party"),
			# "debit": args.get("debit") if args.get("debit") else 0,
			# "credit": args.get("credit") if args.get("credit") else 0
		},
		fields=["parent"],
	)[0]

	return jea_parent


def create_asset_category():
	asset_category = frappe.new_doc("Asset Category")
	asset_category.asset_category_name = "Test_Category"
	asset_category.total_number_of_depreciations = 3
	asset_category.frequency_of_depreciation = 3
	asset_category.enable_cwip_accounting = 1
	asset_category.append(
		"accounts",
		{
			"company_name": "_Test Company",
			"fixed_asset_account": "_Test Fixed Asset - _TC",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - _TC",
			"depreciation_expense_account": "_Test Depreciations - _TC",
			"capital_work_in_progress_account": "CWIP Account - _TC",
		},
	)
	asset_category.append(
		"accounts",
		{
			"company_name": "_Test Company with perpetual inventory",
			"fixed_asset_account": "_Test Fixed Asset - TCP1",
			"accumulated_depreciation_account": "_Test Accumulated Depreciations - TCP1",
			"depreciation_expense_account": "_Test Depreciations - TCP1",
		},
	)

	asset_category.insert(ignore_permissions=True)


def create_asset_data():
	if not frappe.db.exists("Location", "Test Location"):
		frappe.get_doc({"doctype": "Location", "location_name": "Test Location"}).insert(
			ignore_permissions=True
		)

	if not frappe.db.exists("Finance Book", "Test Finance Book 1"):
		frappe.get_doc({"doctype": "Finance Book", "finance_book_name": "Test Finance Book 1"}).insert(
			ignore_permissions=True
		)

	if not frappe.db.exists("Finance Book", "Test Finance Book 2"):
		frappe.get_doc({"doctype": "Finance Book", "finance_book_name": "Test Finance Book 2"}).insert(
			ignore_permissions=True
		)

	if not frappe.db.exists("Finance Book", "Test Finance Book 3"):
		frappe.get_doc({"doctype": "Finance Book", "finance_book_name": "Test Finance Book 3"}).insert(
			ignore_permissions=True
		)

	if not frappe.db.exists("Asset Category", "Test_Category"):
		create_asset_category()


def get_or_create_price_list(currency="INR"):
	existing_price_list = frappe.db.get_value(
		"Price List", {"currency": currency, "buying": 1, "selling": 1}, order_by="creation ASC"
	)

	if existing_price_list:
		return existing_price_list

	new_price_list = frappe.new_doc("Price List")
	new_price_list.price_list_name = f"_test_{currency}_Price_List"
	new_price_list.currency = currency
	new_price_list.buying = 1
	new_price_list.selling = 1
	new_price_list.insert()

	return new_price_list.name


def create_or_get_purchase_taxes_template(company):
	from erpnext.buying.doctype.purchase_order.test_purchase_order import create_new_account

	sgst_account = "Input Tax SGST - _TC"
	cgst_account = "Input Tax CGST - _TC"
	purchase_template = "Input GST In-state - _TC"
	tax_category = "In-State"
	if not frappe.db.exists("Tax Category", tax_category):
		tax_category = frappe.get_doc({"doctype": "Tax Category", "title": tax_category}).insert().name

	if not frappe.db.exists("Account", sgst_account):
		sgst_account = create_new_account(
			account_name="Input Tax SGST",
			company=company,
			parent_account="Cash In Hand - _TC",
			account_type="Tax",
		)

	if not frappe.db.exists("Account", cgst_account):
		cgst_account = create_new_account(
			account_name="Input Tax CGST",
			company=company,
			parent_account="Cash In Hand - _TC",
			account_type="Tax",
		)

	if not frappe.db.exists("Purchase Taxes and Charges Template", purchase_template):
		purchase_template = (
			frappe.get_doc(
				{
					"doctype": "Purchase Taxes and Charges Template",
					"title": "Input GST In-state",
					"company": company,
					"tax_category": tax_category,
					"taxes": [
						{
							"charge_type": "On Net Total",
							"add_deduct_tax": "Add",
							"category": "Total",
							"account_head": sgst_account,
							"description": "SGST",
						},
						{
							"charge_type": "On Net Total",
							"add_deduct_tax": "Add",
							"category": "Total",
							"account_head": cgst_account,
							"description": "CGST",
						},
					],
				}
			)
			.insert()
			.name
		)

	return {
		"purchase_tax_template": purchase_template,
		"sgst_account": sgst_account,
		"cgst_account": cgst_account,
	}


def add_purchase_invoice_in_account_reposting_setting():
	doc = frappe.get_doc("Repost Accounting Ledger Settings")
	found = False
	for row in doc.allowed_types:
		if row.document_type == "Purchase Invoice":
			row.allowed = 1
			found = True

	if not found:
		# Add new child row with Purchase Invoice
		doc.append("allowed_types", {"document_type": "Purchase Invoice", "allowed": 1})
	doc.save()
