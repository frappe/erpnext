# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import json

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.accounts.doctype.mode_of_payment.test_mode_of_payment import (
	set_default_account_for_mode_of_payment,
)
from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import (
	make_closing_entry_from_opening,
)
from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile
from erpnext.accounts.doctype.pos_invoice.pos_invoice import make_sales_return
from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice
from erpnext.accounts.doctype.pos_opening_entry.test_pos_opening_entry import create_opening_entry
from erpnext.stock.doctype.serial_and_batch_bundle.test_serial_and_batch_bundle import (
	get_serial_nos_from_bundle,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


class TestPOSInvoiceMergeLog(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.sql("delete from `tabPOS Opening Entry`")
		cls.enterClassContext(cls.change_settings("Selling Settings", validate_selling_price=0))
		cls.enterClassContext(cls.change_settings("POS Settings", invoice_type="POS Invoice"))
		mode_of_payment = frappe.get_doc("Mode of Payment", "Bank Draft")
		set_default_account_for_mode_of_payment(mode_of_payment, "_Test Company", "_Test Bank - _TC")

	def setUp(self):
		frappe.db.sql("delete from `tabPOS Invoice`")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.sql("delete from `tabPOS Profile`")
		frappe.db.sql("delete from `tabPOS Invoice`")

	def test_consolidated_invoice_creation(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv = create_pos_invoice(rate=300, do_not_submit=1)
		pos_inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 300})
		pos_inv.save()
		pos_inv.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv2.save()
		pos_inv2.submit()

		pos_inv3 = create_pos_invoice(customer="_Test Customer 2", rate=2300, do_not_submit=1)
		pos_inv3.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 2300})
		pos_inv3.save()
		pos_inv3.submit()

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.insert()
		closing_entry.submit()

		pos_inv.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv.consolidated_invoice))

		pos_inv3.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv3.consolidated_invoice))

		self.assertFalse(pos_inv.consolidated_invoice == pos_inv3.consolidated_invoice)

	def test_consolidated_credit_note_creation(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv = create_pos_invoice(rate=300, do_not_submit=1)
		pos_inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 300})
		pos_inv.save()
		pos_inv.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv2.save()
		pos_inv2.submit()

		pos_inv3 = create_pos_invoice(customer="_Test Customer 2", rate=2300, do_not_submit=1)
		pos_inv3.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 2300})
		pos_inv3.save()
		pos_inv3.submit()

		pos_inv_cn = make_sales_return(pos_inv.name)
		pos_inv_cn.set("payments", [])
		pos_inv_cn.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": -100})
		pos_inv_cn.append(
			"payments", {"mode_of_payment": "Bank Draft", "account": "_Test Bank - _TC", "amount": -200}
		)
		pos_inv_cn.paid_amount = -300
		pos_inv_cn.submit()

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.insert()
		closing_entry.submit()

		pos_inv.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv.consolidated_invoice))

		pos_inv3.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv3.consolidated_invoice))

		pos_inv_cn.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv_cn.consolidated_invoice))
		consolidated_credit_note = frappe.get_doc("Sales Invoice", pos_inv_cn.consolidated_invoice)
		self.assertEqual(consolidated_credit_note.is_return, 1)
		self.assertEqual(consolidated_credit_note.payments[0].mode_of_payment, "Cash")
		self.assertEqual(consolidated_credit_note.payments[0].amount, -100)
		self.assertEqual(consolidated_credit_note.payments[1].mode_of_payment, "Bank Draft")
		self.assertEqual(consolidated_credit_note.payments[1].amount, -200)

	def test_consolidated_invoice_item_taxes(self):
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		inv = create_pos_invoice(qty=1, rate=100, do_not_save=True)

		inv.append(
			"taxes",
			{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"doctype": "Sales Taxes and Charges",
				"rate": 9,
			},
		)
		inv.insert()
		inv.payments[0].amount = inv.grand_total
		inv.save()
		inv.submit()

		inv2 = create_pos_invoice(qty=1, rate=100, do_not_save=True)
		inv2.get("items")[0].item_code = "_Test Item 2"
		inv2.append(
			"taxes",
			{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"doctype": "Sales Taxes and Charges",
				"rate": 5,
			},
		)
		inv2.insert()
		inv2.payments[0].amount = inv.grand_total
		inv2.save()
		inv2.submit()

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.insert()
		closing_entry.submit()

		inv.load_from_db()

		consolidated_invoice = frappe.get_doc("Sales Invoice", inv.consolidated_invoice)

		expected_item_wise_tax_details = [
			{
				"item_row": consolidated_invoice.items[0].name,
				"tax_row": consolidated_invoice.taxes[0].name,
				"rate": 9.0,
				"amount": 9.0,
				"taxable_amount": 100.0,
			},
			{
				"item_row": consolidated_invoice.items[1].name,
				"tax_row": consolidated_invoice.taxes[0].name,
				"rate": 5.0,
				"amount": 5.0,
				"taxable_amount": 100.0,
			},
		]

		actual = [
			{
				"item_row": d.item_row,
				"tax_row": d.tax_row,
				"rate": d.rate,
				"amount": d.amount,
				"taxable_amount": d.taxable_amount,
			}
			for d in consolidated_invoice.get("item_wise_tax_details")
		]

		self.assertEqual(actual, expected_item_wise_tax_details)

	def test_consolidation_round_off_error_1(self):
		"""
		Test round off error in consolidated invoice creation if POS Invoice has inclusive tax
		"""

		make_stock_entry(
			to_warehouse="_Test Warehouse - _TC",
			item_code="_Test Item",
			rate=8000,
			qty=10,
		)

		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		inv = create_pos_invoice(qty=3, rate=10000, do_not_save=True)
		inv.append(
			"taxes",
			{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"doctype": "Sales Taxes and Charges",
				"rate": 7.5,
				"included_in_print_rate": 1,
			},
		)
		inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 30000})
		inv.insert()
		inv.submit()

		inv2 = create_pos_invoice(qty=3, rate=10000, do_not_save=True)
		inv2.append(
			"taxes",
			{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"doctype": "Sales Taxes and Charges",
				"rate": 7.5,
				"included_in_print_rate": 1,
			},
		)
		inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 30000})
		inv2.insert()
		inv2.submit()

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.insert()
		closing_entry.submit()

		inv.load_from_db()
		consolidated_invoice = frappe.get_doc("Sales Invoice", inv.consolidated_invoice)
		self.assertEqual(consolidated_invoice.outstanding_amount, 0)
		self.assertEqual(consolidated_invoice.status, "Paid")

	def test_consolidation_round_off_error_2(self):
		"""
		Test the same case as above but with an Unpaid POS Invoice
		"""
		make_stock_entry(
			to_warehouse="_Test Warehouse - _TC",
			item_code="_Test Item",
			rate=8000,
			qty=10,
		)

		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		inv = create_pos_invoice(qty=6, rate=10000, do_not_save=True)
		inv.append(
			"taxes",
			{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"doctype": "Sales Taxes and Charges",
				"rate": 7.5,
				"included_in_print_rate": 1,
			},
		)
		inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 60000})
		inv.insert()
		inv.submit()

		inv2 = create_pos_invoice(qty=6, rate=10000, do_not_save=True)
		inv2.append(
			"taxes",
			{
				"account_head": "_Test Account VAT - _TC",
				"charge_type": "On Net Total",
				"cost_center": "_Test Cost Center - _TC",
				"description": "VAT",
				"doctype": "Sales Taxes and Charges",
				"rate": 7.5,
				"included_in_print_rate": 1,
			},
		)
		inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 60000})
		inv2.insert()
		inv2.submit()

		inv3 = create_pos_invoice(qty=3, rate=600, do_not_save=True)
		inv3.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 1800})
		inv3.insert()
		inv3.submit()

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.insert()
		closing_entry.submit()

		inv.load_from_db()
		consolidated_invoice = frappe.get_doc("Sales Invoice", inv.consolidated_invoice)
		self.assertNotEqual(consolidated_invoice.outstanding_amount, 800)
		self.assertEqual(consolidated_invoice.status, "Paid")

	@IntegrationTestCase.change_settings(
		"System Settings", {"number_format": "#,###.###", "currency_precision": 3, "float_precision": 3}
	)
	def test_consolidation_round_off_error_3(self):
		make_stock_entry(
			to_warehouse="_Test Warehouse - _TC",
			item_code="_Test Item",
			rate=8000,
			qty=10,
		)
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		item_rates = [69, 59, 29]
		for _i in [1, 2]:
			inv = create_pos_invoice(is_return=1, do_not_save=1)
			inv.items = []
			for rate in item_rates:
				inv.append(
					"items",
					{
						"item_code": "_Test Item",
						"warehouse": "_Test Warehouse - _TC",
						"qty": -1,
						"rate": rate,
						"income_account": "Sales - _TC",
						"expense_account": "Cost of Goods Sold - _TC",
						"cost_center": "_Test Cost Center - _TC",
					},
				)
			inv.append(
				"taxes",
				{
					"account_head": "_Test Account VAT - _TC",
					"charge_type": "On Net Total",
					"cost_center": "_Test Cost Center - _TC",
					"description": "VAT",
					"doctype": "Sales Taxes and Charges",
					"rate": 15,
					"included_in_print_rate": 1,
				},
			)
			inv.payments = []
			inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": -157})
			inv.paid_amount = -157
			inv.save()
			inv.submit()

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.insert()
		closing_entry.submit()

		inv.load_from_db()
		consolidated_invoice = frappe.get_doc("Sales Invoice", inv.consolidated_invoice)
		self.assertEqual(consolidated_invoice.status, "Return")
		self.assertEqual(consolidated_invoice.rounding_adjustment, -0.002)

	def test_consolidation_rounding_adjustment(self):
		"""
		Test if the rounding adjustment is calculated correctly
		"""
		make_stock_entry(
			to_warehouse="_Test Warehouse - _TC",
			item_code="_Test Item",
			rate=8000,
			qty=10,
		)

		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		inv = create_pos_invoice(qty=1, rate=69.5, do_not_save=True)
		inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 70})
		inv.insert()
		inv.submit()

		inv2 = create_pos_invoice(qty=1, rate=59.5, do_not_save=True)
		inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 60})
		inv2.insert()
		inv2.submit()

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.insert()
		closing_entry.submit()

		inv.load_from_db()
		consolidated_invoice = frappe.get_doc("Sales Invoice", inv.consolidated_invoice)
		self.assertEqual(consolidated_invoice.rounding_adjustment, 1)

	def test_serial_no_case_1(self):
		"""
		Create a POS Invoice with serial no
		Create a Return Invoice with serial no
		Create a POS Invoice with serial no again
		Consolidate the invoices

		The first POS Invoice should be consolidated with a separate single Merge Log
		The second and third POS Invoice should be consolidated with a single Merge Log
		"""

		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

		se = make_serialized_item(self)
		serial_no = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)[0]

		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv = create_pos_invoice(
			item_code="_Test Serialized Item With Series",
			serial_no=[serial_no],
			qty=1,
			rate=100,
			do_not_submit=1,
		)
		pos_inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 100})
		pos_inv.save()
		pos_inv.submit()

		pos_inv_cn = make_sales_return(pos_inv.name)
		pos_inv_cn.paid_amount = -100
		pos_inv_cn.submit()

		pos_inv2 = create_pos_invoice(
			item_code="_Test Serialized Item With Series",
			serial_no=[serial_no],
			qty=1,
			rate=100,
			do_not_submit=1,
		)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 100})
		pos_inv2.save()
		pos_inv2.submit()

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.insert()
		closing_entry.submit()

		pos_inv.load_from_db()
		pos_inv2.load_from_db()

		self.assertNotEqual(pos_inv.consolidated_invoice, pos_inv2.consolidated_invoice)

	def test_separate_consolidated_invoice_for_different_accounting_dimensions(self):
		"""
		Creating 3 POS Invoices where first POS Invoice has different Cost Center than the other two.
		Consolidate the Invoices.
		Check whether the first POS Invoice is consolidated with a separate Sales Invoice than the other two.
		Check whether the second and third POS Invoice are consolidated with the same Sales Invoice.
		"""
		from erpnext.accounts.doctype.cost_center.test_cost_center import create_cost_center

		create_cost_center(cost_center_name="_Test POS Cost Center 1", is_group=0)
		create_cost_center(cost_center_name="_Test POS Cost Center 2", is_group=0)

		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv = create_pos_invoice(rate=300, do_not_submit=1)
		pos_inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 300})
		pos_inv.cost_center = "_Test POS Cost Center 1 - _TC"
		pos_inv.save()
		pos_inv.submit()

		pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
		pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200})
		pos_inv.cost_center = "_Test POS Cost Center 2 - _TC"
		pos_inv2.save()
		pos_inv2.submit()

		pos_inv3 = create_pos_invoice(rate=2300, do_not_submit=1)
		pos_inv3.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 2300})
		pos_inv.cost_center = "_Test POS Cost Center 2 - _TC"
		pos_inv3.save()
		pos_inv3.submit()

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.insert()
		closing_entry.submit()

		pos_inv.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv.consolidated_invoice))

		pos_inv2.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv2.consolidated_invoice))

		self.assertFalse(pos_inv.consolidated_invoice == pos_inv3.consolidated_invoice)

		pos_inv3.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv3.consolidated_invoice))

		self.assertTrue(pos_inv2.consolidated_invoice == pos_inv3.consolidated_invoice)

	def test_company_in_pos_invoice_merge_log(self):
		"""
		Test if the company is fetched from POS Closing Entry
		"""
		test_user, pos_profile = init_user_and_profile()
		opening_entry = create_opening_entry(pos_profile, test_user.name)

		pos_inv = create_pos_invoice(rate=300, do_not_submit=1)
		pos_inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 300})
		pos_inv.save()
		pos_inv.submit()

		closing_entry = make_closing_entry_from_opening(opening_entry)
		closing_entry.insert()
		closing_entry.submit()

		self.assertTrue(frappe.db.exists("POS Invoice Merge Log", {"pos_closing_entry": closing_entry.name}))

		pos_merge_log_company = frappe.db.get_value(
			"POS Invoice Merge Log", {"pos_closing_entry": closing_entry.name}, "company"
		)
		self.assertEqual(pos_merge_log_company, closing_entry.company)
