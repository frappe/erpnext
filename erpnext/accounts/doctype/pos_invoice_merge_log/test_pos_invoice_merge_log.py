# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import json
import unittest

import frappe
from frappe.tests.utils import change_settings

from erpnext.accounts.doctype.pos_closing_entry.test_pos_closing_entry import init_user_and_profile
from erpnext.accounts.doctype.pos_invoice.pos_invoice import make_sales_return
from erpnext.accounts.doctype.pos_invoice.test_pos_invoice import create_pos_invoice
from erpnext.accounts.doctype.pos_invoice_merge_log.pos_invoice_merge_log import (
	consolidate_pos_invoices,
)
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


class TestPOSInvoiceMergeLog(unittest.TestCase):
	def test_consolidated_invoice_creation(self):
		frappe.db.sql("delete from `tabPOS Invoice`")

		try:
			test_user, pos_profile = init_user_and_profile()

			pos_inv = create_pos_invoice(rate=300, do_not_submit=1)
			pos_inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 300})
			pos_inv.submit()

			pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
			pos_inv2.append(
				"payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200}
			)
			pos_inv2.submit()

			pos_inv3 = create_pos_invoice(customer="_Test Customer 2", rate=2300, do_not_submit=1)
			pos_inv3.append(
				"payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 2300}
			)
			pos_inv3.submit()

			consolidate_pos_invoices()

			pos_inv.load_from_db()
			self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv.consolidated_invoice))

			pos_inv3.load_from_db()
			self.assertTrue(frappe.db.exists("Sales Invoice", pos_inv3.consolidated_invoice))

			self.assertFalse(pos_inv.consolidated_invoice == pos_inv3.consolidated_invoice)

		finally:
			frappe.set_user("Administrator")
			frappe.db.sql("delete from `tabPOS Profile`")
			frappe.db.sql("delete from `tabPOS Invoice`")

	def test_consolidated_credit_note_creation(self):
		frappe.db.sql("delete from `tabPOS Invoice`")

		try:
			test_user, pos_profile = init_user_and_profile()

			pos_inv = create_pos_invoice(rate=300, do_not_submit=1)
			pos_inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 300})
			pos_inv.submit()

			pos_inv2 = create_pos_invoice(rate=3200, do_not_submit=1)
			pos_inv2.append(
				"payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 3200}
			)
			pos_inv2.submit()

			pos_inv3 = create_pos_invoice(customer="_Test Customer 2", rate=2300, do_not_submit=1)
			pos_inv3.append(
				"payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 2300}
			)
			pos_inv3.submit()

			pos_inv_cn = make_sales_return(pos_inv.name)
			pos_inv_cn.set("payments", [])
			pos_inv_cn.append(
				"payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": -100}
			)
			pos_inv_cn.append(
				"payments", {"mode_of_payment": "Bank Draft", "account": "_Test Bank - _TC", "amount": -200}
			)
			pos_inv_cn.paid_amount = -300
			pos_inv_cn.submit()

			consolidate_pos_invoices()

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

		finally:
			frappe.set_user("Administrator")
			frappe.db.sql("delete from `tabPOS Profile`")
			frappe.db.sql("delete from `tabPOS Invoice`")

	def test_consolidated_invoice_item_taxes(self):
		frappe.db.sql("delete from `tabPOS Invoice`")

		try:
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
			inv2.submit()

			consolidate_pos_invoices()
			inv.load_from_db()

			consolidated_invoice = frappe.get_doc("Sales Invoice", inv.consolidated_invoice)
			item_wise_tax_detail = json.loads(consolidated_invoice.get("taxes")[0].item_wise_tax_detail)

			tax_rate, amount = item_wise_tax_detail.get("_Test Item")
			self.assertEqual(tax_rate, 9)
			self.assertEqual(amount, 9)

			tax_rate2, amount2 = item_wise_tax_detail.get("_Test Item 2")
			self.assertEqual(tax_rate2, 5)
			self.assertEqual(amount2, 5)
		finally:
			frappe.set_user("Administrator")
			frappe.db.sql("delete from `tabPOS Profile`")
			frappe.db.sql("delete from `tabPOS Invoice`")

	def test_consolidation_round_off_error_1(self):
		"""
		Test round off error in consolidated invoice creation if POS Invoice has inclusive tax
		"""

		frappe.db.sql("delete from `tabPOS Invoice`")

		try:
			make_stock_entry(
				to_warehouse="_Test Warehouse - _TC",
				item_code="_Test Item",
				rate=8000,
				qty=10,
			)

			init_user_and_profile()

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

			consolidate_pos_invoices()

			inv.load_from_db()
			consolidated_invoice = frappe.get_doc("Sales Invoice", inv.consolidated_invoice)
			self.assertEqual(consolidated_invoice.outstanding_amount, 0)
			self.assertEqual(consolidated_invoice.status, "Paid")

		finally:
			frappe.set_user("Administrator")
			frappe.db.sql("delete from `tabPOS Profile`")
			frappe.db.sql("delete from `tabPOS Invoice`")

	def test_consolidation_round_off_error_2(self):
		"""
		Test the same case as above but with an Unpaid POS Invoice
		"""
		frappe.db.sql("delete from `tabPOS Invoice`")

		try:
			make_stock_entry(
				to_warehouse="_Test Warehouse - _TC",
				item_code="_Test Item",
				rate=8000,
				qty=10,
			)

			init_user_and_profile()

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
			inv3.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 1000})
			inv3.insert()
			inv3.submit()

			consolidate_pos_invoices()

			inv.load_from_db()
			consolidated_invoice = frappe.get_doc("Sales Invoice", inv.consolidated_invoice)
			self.assertEqual(consolidated_invoice.outstanding_amount, 800)
			self.assertNotEqual(consolidated_invoice.status, "Paid")

		finally:
			frappe.set_user("Administrator")
			frappe.db.sql("delete from `tabPOS Profile`")
			frappe.db.sql("delete from `tabPOS Invoice`")

	@change_settings(
		"System Settings", {"number_format": "#,###.###", "currency_precision": 3, "float_precision": 3}
	)
	def test_consolidation_round_off_error_3(self):
		frappe.db.sql("delete from `tabPOS Invoice`")

		try:
			make_stock_entry(
				to_warehouse="_Test Warehouse - _TC",
				item_code="_Test Item",
				rate=8000,
				qty=10,
			)
			init_user_and_profile()

			item_rates = [69, 59, 29]
			for i in [1, 2]:
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

			consolidate_pos_invoices()

			inv.load_from_db()
			consolidated_invoice = frappe.get_doc("Sales Invoice", inv.consolidated_invoice)
			self.assertEqual(consolidated_invoice.status, "Return")
			self.assertEqual(consolidated_invoice.rounding_adjustment, -0.001)

		finally:
			frappe.set_user("Administrator")
			frappe.db.sql("delete from `tabPOS Profile`")
			frappe.db.sql("delete from `tabPOS Invoice`")

	def test_consolidation_rounding_adjustment(self):
		"""
		Test if the rounding adjustment is calculated correctly
		"""
		frappe.db.sql("delete from `tabPOS Invoice`")

		try:
			make_stock_entry(
				to_warehouse="_Test Warehouse - _TC",
				item_code="_Test Item",
				rate=8000,
				qty=10,
			)

			init_user_and_profile()

			inv = create_pos_invoice(qty=1, rate=69.5, do_not_save=True)
			inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 70})
			inv.insert()
			inv.submit()

			inv2 = create_pos_invoice(qty=1, rate=59.5, do_not_save=True)
			inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 60})
			inv2.insert()
			inv2.submit()

			consolidate_pos_invoices()

			inv.load_from_db()
			consolidated_invoice = frappe.get_doc("Sales Invoice", inv.consolidated_invoice)
			self.assertEqual(consolidated_invoice.rounding_adjustment, 1)

		finally:
			frappe.set_user("Administrator")
			frappe.db.sql("delete from `tabPOS Profile`")
			frappe.db.sql("delete from `tabPOS Invoice`")

	def test_serial_no_case_1(self):
		"""
		Create a POS Invoice with serial no
		Create a Return Invoice with serial no
		Create a POS Invoice with serial no again
		Consolidate the invoices

		The first POS Invoice should be consolidated with a separate single Merge Log
		The second and third POS Invoice should be consolidated with a single Merge Log
		"""

		from erpnext.stock.doctype.serial_no.test_serial_no import get_serial_nos
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item

		frappe.db.sql("delete from `tabPOS Invoice`")

		try:
			se = make_serialized_item()
			serial_no = get_serial_nos(se.get("items")[0].serial_no)[0]

			init_user_and_profile()

			pos_inv = create_pos_invoice(
				item_code="_Test Serialized Item With Series",
				serial_no=serial_no,
				qty=1,
				rate=100,
				do_not_submit=1,
			)
			pos_inv.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 100})
			pos_inv.submit()

			pos_inv_cn = make_sales_return(pos_inv.name)
			pos_inv_cn.paid_amount = -100
			pos_inv_cn.submit()

			pos_inv2 = create_pos_invoice(
				item_code="_Test Serialized Item With Series",
				serial_no=serial_no,
				qty=1,
				rate=100,
				do_not_submit=1,
			)
			pos_inv2.append("payments", {"mode_of_payment": "Cash", "account": "Cash - _TC", "amount": 100})
			pos_inv2.submit()

			consolidate_pos_invoices()

			pos_inv.load_from_db()
			pos_inv2.load_from_db()

			self.assertNotEqual(pos_inv.consolidated_invoice, pos_inv2.consolidated_invoice)

		finally:
			frappe.set_user("Administrator")
			frappe.db.sql("delete from `tabPOS Profile`")
			frappe.db.sql("delete from `tabPOS Invoice`")
