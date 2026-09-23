# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import json

from contextlib import contextmanager

import frappe
from frappe.utils import flt

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
from erpnext.tests.utils import ERPNextTestSuite


@contextmanager
def rounding_method(method):
	"""System Settings is also cached on frappe.local, so that copy has to go as well."""
	previous = frappe.db.get_single_value("System Settings", "rounding_method")
	try:
		frappe.db.set_single_value("System Settings", "rounding_method", method)
		frappe.local.system_settings = None
		yield
	finally:
		frappe.db.set_single_value("System Settings", "rounding_method", previous)
		frappe.local.system_settings = None


def sell_over_the_counter(lines, discount_percentage=0):
	item_code, qty, rate = lines[0]
	sale = create_pos_invoice(item_code=item_code, qty=qty, rate=rate, do_not_save=True)
	for item_code, qty, rate in lines[1:]:
		sale.append(
			"items",
			{
				"item_code": item_code,
				"qty": qty,
				"rate": rate,
				"price_list_rate": rate,
				"warehouse": "_Test Warehouse - _TC",
				"income_account": "Sales - _TC",
				"cost_center": "_Test Cost Center - _TC",
			},
		)

	if discount_percentage:
		sale.apply_discount_on = "Net Total"
		sale.additional_discount_percentage = discount_percentage

	sale.run_method("calculate_taxes_and_totals")
	payable = sale.rounded_total or sale.grand_total
	sale.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": payable})
	sale.paid_amount = sale.base_paid_amount = payable
	sale.insert()
	sale.submit()
	return sale


def refund_over_the_counter(sale, qty=None):
	"""Hand back every line of `sale`, `qty` of each when fewer units come back."""
	note = make_sales_return(sale.name)
	if qty is not None:
		for item in note.items:
			item.qty = qty

	note.run_method("calculate_taxes_and_totals")
	refundable = note.rounded_total or note.grand_total
	note.payments[0].amount = refundable
	for spare in note.payments[1:]:
		spare.amount = 0
	note.paid_amount = note.base_paid_amount = refundable
	note.insert()
	note.submit()
	return note


class TestPOSInvoiceMergeLog(ERPNextTestSuite):
	def setUp(self):
		mode_of_payment = frappe.get_doc("Mode of Payment", "Bank Draft")
		self.test_user, self.pos_profile = init_user_and_profile()
		self.opening_entry = create_opening_entry(self.pos_profile, self.test_user.name)

		set_default_account_for_mode_of_payment(mode_of_payment, "_Test Company", "_Test Bank - _TC")
		frappe.db.set_single_value("POS Settings", "invoice_type", "POS Invoice")
		frappe.db.set_single_value("Selling Settings", "validate_selling_price", 0)

	def make_closing_entry(self):
		closing_entry = make_closing_entry_from_opening(self.opening_entry)
		closing_entry.insert().submit()
		return closing_entry

	def test_consolidated_invoice_creation(self):
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

		self.make_closing_entry()

		pos_inv.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv.consolidated_invoice))

		pos_inv3.load_from_db()
		self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv3.consolidated_invoice))

		self.assertFalse(pos_inv.consolidated_invoice == pos_inv3.consolidated_invoice)

	def test_consolidated_credit_note_creation(self):
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

		self.make_closing_entry()

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

		self.make_closing_entry()

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

		self.make_closing_entry()

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

		self.make_closing_entry()

		inv.load_from_db()
		consolidated_invoice = frappe.get_doc("Sales Invoice", inv.consolidated_invoice)
		self.assertNotEqual(consolidated_invoice.outstanding_amount, 800)
		self.assertEqual(consolidated_invoice.status, "Paid")

	@ERPNextTestSuite.change_settings(
		"System Settings", {"number_format": "#,###.###", "currency_precision": 3, "float_precision": 3}
	)
	def test_consolidation_round_off_error_3(self):
		make_stock_entry(
			to_warehouse="_Test Warehouse - _TC",
			item_code="_Test Item",
			rate=8000,
			qty=10,
		)

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

		self.make_closing_entry()

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

		inv = create_pos_invoice(qty=1, rate=69.5, do_not_save=True)
		inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 70})
		inv.insert()
		inv.submit()

		inv2 = create_pos_invoice(qty=1, rate=59.5, do_not_save=True)
		inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 60})
		inv2.insert()
		inv2.submit()

		self.make_closing_entry()

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

		self.load_test_records("Stock Entry")
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

		se = make_serialized_item(self)
		serial_no = get_serial_nos_from_bundle(se.get("items")[0].serial_and_batch_bundle)[0]

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

		self.make_closing_entry()

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

		self.make_closing_entry()

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
		pos_inv = create_pos_invoice(rate=300, do_not_submit=1)
		pos_inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 300})
		pos_inv.save()
		pos_inv.submit()

		closing_entry = self.make_closing_entry()

		self.assertTrue(frappe.db.exists("POS Invoice Merge Log", {"pos_closing_entry": closing_entry.name}))

		pos_merge_log_company = frappe.db.get_value(
			"POS Invoice Merge Log", {"pos_closing_entry": closing_entry.name}, "company"
		)
		self.assertEqual(pos_merge_log_company, closing_entry.company)

	@ERPNextTestSuite.change_settings("Selling Settings", {"allow_multiple_items": 1})
	def test_consolidating_returns_priced_off_a_rounded_invoice_discount(self):
		"""A return works out its own share of an invoice-level discount, so rounding can leave
		it a minor unit above the sale's, and validate_returned_items then refuses it.

		Every shape that reaches a consolidated credit note goes through one closing entry:
		a split landing on a half minor unit, the same item on two rows so the rows can only
		be paired through sales_invoice_item, fewer units coming back than went out, and — as
		a control — a sale with no invoice-level discount to split at all.
		"""
		for item_code in ("_Test Item", "_Test Item 2"):
			make_stock_entry(to_warehouse="_Test Warehouse - _TC", item_code=item_code, rate=100, qty=40)

		with rounding_method("Banker's Rounding (legacy)"):
			tied = sell_over_the_counter(
				[("_Test Item", 1, 42.86), ("_Test Item 2", 1, 57.14)], discount_percentage=25
			)
			repeated = sell_over_the_counter(
				[("_Test Item", 1, 42.86), ("_Test Item", 1, 57.14)], discount_percentage=25
			)
			oversold = sell_over_the_counter(
				[("_Test Item", 3, 42.86), ("_Test Item 2", 3, 57.14)], discount_percentage=25
			)
			undiscounted = sell_over_the_counter([("_Test Item", 1, 42.86), ("_Test Item 2", 1, 57.14)])

			# the sale and the return really do round the split apart
			self.assertEqual(
				{item.item_code: item.net_rate for item in tied.items},
				{"_Test Item": 32.15, "_Test Item 2": 42.85},
			)
			returns = [
				refund_over_the_counter(tied),
				refund_over_the_counter(repeated),
				refund_over_the_counter(oversold, qty=-1),
				refund_over_the_counter(undiscounted),
			]
			self.assertEqual(
				{item.item_code: item.net_rate for item in returns[0].items},
				{"_Test Item": 32.14, "_Test Item 2": 42.86},
			)

			self.make_closing_entry()

		for pos_invoice in [tied, repeated, oversold, undiscounted, *returns]:
			pos_invoice.load_from_db()
			self.assertTrue(
				frappe.db.exists("Sales Invoice", pos_invoice.consolidated_invoice),
				f"{pos_invoice.name} was not consolidated",
			)
			self.assertEqual(
				frappe.db.get_value("Sales Invoice", pos_invoice.consolidated_invoice, "outstanding_amount"),
				0,
			)

		for note in returns:
			# no returned row may be priced above the row it reverses
			for row in frappe.get_all(
				"Sales Invoice Item",
				filters={"parent": note.consolidated_invoice},
				fields=["item_code", "rate", "sales_invoice_item"],
			):
				self.assertTrue(row.sales_invoice_item, f"{row.item_code} lost its link to the sale")
				sold_rate = frappe.db.get_value("Sales Invoice Item", row.sales_invoice_item, "rate")
				self.assertLessEqual(row.rate, sold_rate)

		# returns for one customer land on a single credit note, which still adds up to
		# everything handed back over the counter
		refunded = {}
		for note in returns:
			refunded[note.consolidated_invoice] = refunded.get(note.consolidated_invoice, 0) + flt(
				note.grand_total
			)
		for consolidated_name, handed_back in refunded.items():
			self.assertEqual(
				flt(frappe.db.get_value("Sales Invoice", consolidated_name, "grand_total"), 2),
				flt(handed_back, 2),
			)
