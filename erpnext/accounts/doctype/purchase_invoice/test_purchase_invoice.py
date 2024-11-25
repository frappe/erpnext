# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, cint, flt, getdate, nowdate, today

import erpnext
from erpnext.accounts.doctype.account.test_account import create_account, get_inventory_account
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.buying.doctype.purchase_order.purchase_order import get_mapped_purchase_invoice
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice as make_pi_from_po
from erpnext.buying.doctype.purchase_order.test_purchase_order import (
	create_pr_against_po,
	create_purchase_order,
)
from erpnext.buying.doctype.supplier.test_supplier import create_supplier
from erpnext.controllers.accounts_controller import get_payment_terms
from erpnext.controllers.buying_controller import QtyMismatchError
from erpnext.exceptions import InvalidCurrency
from erpnext.projects.doctype.project.test_project import make_project
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.material_request.material_request import make_purchase_order
from erpnext.stock.doctype.material_request.test_material_request import make_material_request
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
from erpnext.stock.doctype.stock_entry.test_stock_entry import get_qty_after_transaction
from erpnext.stock.tests.test_utils import StockTestMixin

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
		pi.insert()
		pi.submit()

		# Check if the received quantity is updated in Material Request
		mr.reload()
		self.assertEqual(mr.items[0].received_qty, 10)

	def test_gl_entries_without_perpetual_inventory(self):
		frappe.db.set_value("Company", "_Test Company", "round_off_account", "Round Off - _TC")
		pi = frappe.copy_doc(test_records[0])
		self.assertTrue(not cint(erpnext.is_perpetual_inventory_enabled(pi.company)))
		pi.insert()
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

		pi_doc = frappe.get_doc("Purchase Invoice", pi_doc.name)
		pi_doc.load_from_db()
		self.assertTrue(pi_doc.status, "Paid")

		self.assertRaises(frappe.LinkExistsError, pi_doc.cancel)
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

		pi.insert()
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

		pi.insert()
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
		pi.insert()
		pi.naming_series = "TEST-"

		self.assertRaises(frappe.CannotChangeConstantError, pi.save)

		pi = frappe.copy_doc(test_records[0])
		pi.insert()
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
		pi.insert()
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
		pi.insert()

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
		pi.insert()

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

	def test_total_purchase_cost_for_project(self):
		if not frappe.db.exists("Project", {"project_name": "_Test Project for Purchase"}):
			project = make_project({"project_name": "_Test Project for Purchase"})
		else:
			project = frappe.get_doc("Project", {"project_name": "_Test Project for Purchase"})

		existing_purchase_cost = frappe.db.sql(
			f"""select sum(base_net_amount)
			from `tabPurchase Invoice Item`
			where project = '{project.name}'
			and docstatus=1"""
		)
		existing_purchase_cost = existing_purchase_cost and existing_purchase_cost[0][0] or 0

		pi = make_purchase_invoice(currency="USD", conversion_rate=60, project=project.name)
		self.assertEqual(
			frappe.db.get_value("Project", project.name, "total_purchase_cost"),
			existing_purchase_cost + 15000,
		)

		pi1 = make_purchase_invoice(qty=10, project=project.name)
		self.assertEqual(
			frappe.db.get_value("Project", project.name, "total_purchase_cost"),
			existing_purchase_cost + 15500,
		)

		pi1.cancel()
		self.assertEqual(
			frappe.db.get_value("Project", project.name, "total_purchase_cost"),
			existing_purchase_cost + 15000,
		)

		pi.cancel()
		self.assertEqual(
			frappe.db.get_value("Project", project.name, "total_purchase_cost"), existing_purchase_cost
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
			"""select account, account_currency, sum(debit) as debit,
				sum(credit) as credit, debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			group by account, voucher_no order by account asc;""",
			pi.name,
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
		pi.insert()
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
		pe.insert()
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
		pi.insert()
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
		pi.insert()
		pi.save()

		self.assertEqual(pi.net_total, 1250)

		self.assertEqual(pi.total_taxes_and_charges, 354.1)
		self.assertEqual(pi.grand_total, 1604.1)

	def test_make_pi_without_terms(self):
		pi = make_purchase_invoice(do_not_save=1)

		self.assertFalse(pi.get("payment_schedule"))

		pi.insert()

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
		pe.insert()
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

	def test_purchase_invoice_with_project_link(self):
		project = make_project(
			{
				"project_name": "Purchase Invoice Project",
				"project_template_name": "Test Project Template",
				"start_date": "2020-01-01",
			}
		)
		item_project = make_project(
			{
				"project_name": "Purchase Invoice Item Project",
				"project_template_name": "Test Project Template",
				"start_date": "2019-06-01",
			}
		)

		pi = make_purchase_invoice(credit_to="Creditors - _TC", do_not_save=1)
		pi.items[0].project = item_project.name
		pi.project = project.name

		pi.submit()

		expected_values = {
			"Creditors - _TC": {"project": project.name},
			"_Test Account Cost for Goods Sold - _TC": {"project": item_project.name},
		}

		gl_entries = frappe.db.sql(
			"""select account, cost_center, project, account_currency, debit, credit,
			debit_in_account_currency, credit_in_account_currency
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""",
			pi.name,
			as_dict=1,
		)

		self.assertTrue(gl_entries)

		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account]["project"], gle.project)

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

	def test_purchase_gl_with_tax_withholding_tax(self):
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

		pi = make_purchase_invoice(
			supplier=supplier.name,
			rate=3000,
			qty=1,
			item="_Test Non Stock Item",
			do_not_submit=1,
		)
		pi.apply_tds = 1
		pi.tax_withholding_category = tax_withholding_category
		pi.save()
		pi.submit()

		self.assertEqual(pi.taxes[0].tax_amount, 300)
		self.assertEqual(pi.taxes[0].account_head, tds_account)

		gl_entries = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": pi.name, "voucher_type": "Purchase Invoice", "account": "Creditors - _TC"},
			fields=["account", "against", "debit", "credit"],
		)

		for gle in gl_entries:
			if gle.debit:
				# GL Entry with TDS Amount
				self.assertEqual(gle.against, tds_account)
				self.assertEqual(gle.debit, 300)
			else:
				# GL Entry with Purchase Invoice Amount
				self.assertEqual(gle.credit, 3000)

	def test_provisional_accounting_entry(self):
		setup_provisional_accounting()

		pr = make_purchase_receipt(item_code="_Test Non Stock Item", posting_date=add_days(nowdate(), -2))

		pi = create_purchase_invoice_from_receipt(pr.name)
		pi.set_posting_time = 1
		pi.posting_date = add_days(pr.posting_date, -1)
		pi.items[0].expense_account = "Cost of Goods Sold - _TC"
		pi.save()
		pi.submit()

		self.assertEqual(pr.items[0].provisional_expense_account, "Provision Account - _TC")

		# Check GLE for Purchase Invoice
		expected_gle = [
			["Cost of Goods Sold - _TC", 250, 0, add_days(pr.posting_date, -1)],
			["Creditors - _TC", 0, 250, add_days(pr.posting_date, -1)],
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
		self.assertEqual(pi.payment_schedule[0].payment_amount, 2500)

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
			["_Test Account Cost for Goods Sold - _TC", 1000, 0.0, nowdate(), branch2.branch],
			["Creditors - _TC", 0.0, 1000, nowdate(), branch1.branch],
			["Offsetting - _TC", 1000, 0.0, nowdate(), branch1.branch],
			["Offsetting - _TC", 0.0, 1000, nowdate(), branch2.branch],
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

	def test_make_pr_and_pi_from_po(self):
		from erpnext.assets.doctype.asset.test_asset import create_asset_category

		if not frappe.db.exists("Asset Category", "Computers"):
			create_asset_category()

		item = create_item(
			item_code="_Test_Item", is_stock_item=0, is_fixed_asset=1, asset_category="Computers"
		)
		po = create_purchase_order(item_code=item.item_code)
		pr = create_pr_against_po(po.name, 10)
		pi = make_pi_from_po(po.name)
		pi.insert()
		pi.submit()

		pr_gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Purchase Receipt' and voucher_no=%s
			order by account asc""",
			pr.name,
			as_dict=1,
		)

		pr_expected_values = [
			["Asset Received But Not Billed - _TC", 0, 5000],
			["CWIP Account - _TC", 5000, 0],
		]

		for i, gle in enumerate(pr_gl_entries):
			self.assertEqual(pr_expected_values[i][0], gle.account)
			self.assertEqual(pr_expected_values[i][1], gle.debit)
			self.assertEqual(pr_expected_values[i][2], gle.credit)

		pi_gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Purchase Invoice' and voucher_no=%s
			order by account asc""",
			pi.name,
			as_dict=1,
		)
		pi_expected_values = [
			["Asset Received But Not Billed - _TC", 5000, 0],
			["Creditors - _TC", 0, 5000],
		]

		for i, gle in enumerate(pi_gl_entries):
			self.assertEqual(pi_expected_values[i][0], gle.account)
			self.assertEqual(pi_expected_values[i][1], gle.debit)
			self.assertEqual(pi_expected_values[i][2], gle.credit)

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

	bundle_id = None
	if not args.use_serial_batch_fields and (args.get("batch_no") or args.get("serial_no")):
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
			"qty": args.qty or 5,
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
		pi.insert()
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
