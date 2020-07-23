# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest, copy, time
from erpnext.accounts.doctype.pos_profile.test_pos_profile import make_pos_profile
from erpnext.accounts.doctype.pos_invoice.pos_invoice import make_sales_return

class TestPOSInvoice(unittest.TestCase):
	def test_timestamp_change(self):
		w = create_pos_invoice(do_not_save=1)
		w.docstatus = 0
		w.insert()

		w2 = frappe.get_doc(w.doctype, w.name)

		import time
		time.sleep(1)
		w.save()

		import time
		time.sleep(1)
		self.assertRaises(frappe.TimestampMismatchError, w2.save)
	
	def test_change_naming_series(self):
		inv = create_pos_invoice(do_not_submit=1)
		inv.naming_series = 'TEST-'

		self.assertRaises(frappe.CannotChangeConstantError, inv.save)
	
	def test_discount_and_inclusive_tax(self):
		inv = create_pos_invoice(qty=100, rate=50, do_not_save=1)
		inv.append("taxes", {
			"charge_type": "On Net Total",
			"account_head": "_Test Account Service Tax - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Service Tax",
			"rate": 14,
			'included_in_print_rate': 1
		})
		inv.insert()

		self.assertEqual(inv.net_total, 4385.96)
		self.assertEqual(inv.grand_total, 5000)

		inv.reload()

		inv.discount_amount = 100
		inv.apply_discount_on = 'Net Total'
		inv.payment_schedule = []

		inv.save()

		self.assertEqual(inv.net_total, 4285.96)
		self.assertEqual(inv.grand_total, 4885.99)

		inv.reload()

		inv.discount_amount = 100
		inv.apply_discount_on = 'Grand Total'
		inv.payment_schedule = []

		inv.save()

		self.assertEqual(inv.net_total, 4298.25)
		self.assertEqual(inv.grand_total, 4900.00)
	
	def test_tax_calculation_with_multiple_items(self):
		inv = create_pos_invoice(qty=84, rate=4.6, do_not_save=True)
		item_row = inv.get("items")[0]
		for qty in (54, 288, 144, 430):
			item_row_copy = copy.deepcopy(item_row)
			item_row_copy.qty = qty
			inv.append("items", item_row_copy)

		inv.append("taxes", {
			"account_head": "_Test Account VAT - _TC",
			"charge_type": "On Net Total",
			"cost_center": "_Test Cost Center - _TC",
			"description": "VAT",
			"doctype": "Sales Taxes and Charges",
			"rate": 19
		})
		inv.insert()

		self.assertEqual(inv.net_total, 4600)

		self.assertEqual(inv.get("taxes")[0].tax_amount, 874.0)
		self.assertEqual(inv.get("taxes")[0].total, 5474.0)

		self.assertEqual(inv.grand_total, 5474.0)

	def test_tax_calculation_with_item_tax_template(self):
		inv = create_pos_invoice(qty=84, rate=4.6, do_not_save=1)
		item_row = inv.get("items")[0]

		add_items = [
			(54, '_Test Account Excise Duty @ 12'),
			(288, '_Test Account Excise Duty @ 15'),
			(144, '_Test Account Excise Duty @ 20'),
			(430, '_Test Item Tax Template 1')
		]
		for qty, item_tax_template in add_items:
			item_row_copy = copy.deepcopy(item_row)
			item_row_copy.qty = qty
			item_row_copy.item_tax_template = item_tax_template
			inv.append("items", item_row_copy)

		inv.append("taxes", {
			"account_head": "_Test Account Excise Duty - _TC",
			"charge_type": "On Net Total",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Excise Duty",
			"doctype": "Sales Taxes and Charges",
			"rate": 11
		})
		inv.append("taxes", {
			"account_head": "_Test Account Education Cess - _TC",
			"charge_type": "On Net Total",
			"cost_center": "_Test Cost Center - _TC",
			"description": "Education Cess",
			"doctype": "Sales Taxes and Charges",
			"rate": 0
		})
		inv.append("taxes", {
			"account_head": "_Test Account S&H Education Cess - _TC",
			"charge_type": "On Net Total",
			"cost_center": "_Test Cost Center - _TC",
			"description": "S&H Education Cess",
			"doctype": "Sales Taxes and Charges",
			"rate": 3
		})
		inv.insert()

		self.assertEqual(inv.net_total, 4600)

		self.assertEqual(inv.get("taxes")[0].tax_amount, 502.41)
		self.assertEqual(inv.get("taxes")[0].total, 5102.41)

		self.assertEqual(inv.get("taxes")[1].tax_amount, 197.80)
		self.assertEqual(inv.get("taxes")[1].total, 5300.21)

		self.assertEqual(inv.get("taxes")[2].tax_amount, 375.36)
		self.assertEqual(inv.get("taxes")[2].total, 5675.57)

		self.assertEqual(inv.grand_total, 5675.57)
		self.assertEqual(inv.rounding_adjustment, 0.43)
		self.assertEqual(inv.rounded_total, 5676.0)
	
	def test_tax_calculation_with_multiple_items_and_discount(self):
		inv = create_pos_invoice(qty=1, rate=75, do_not_save=True)
		item_row = inv.get("items")[0]
		for rate in (500, 200, 100, 50, 50):
			item_row_copy = copy.deepcopy(item_row)
			item_row_copy.price_list_rate = rate
			item_row_copy.rate = rate
			inv.append("items", item_row_copy)

		inv.apply_discount_on = "Net Total"
		inv.discount_amount = 75.0

		inv.append("taxes", {
			"account_head": "_Test Account VAT - _TC",
			"charge_type": "On Net Total",
			"cost_center": "_Test Cost Center - _TC",
			"description": "VAT",
			"doctype": "Sales Taxes and Charges",
			"rate": 24
		})
		inv.insert()

		self.assertEqual(inv.total, 975)
		self.assertEqual(inv.net_total, 900)

		self.assertEqual(inv.get("taxes")[0].tax_amount, 216.0)
		self.assertEqual(inv.get("taxes")[0].total, 1116.0)

		self.assertEqual(inv.grand_total, 1116.0)

	def test_pos_returns_with_repayment(self):
		pos = create_pos_invoice(qty = 10, do_not_save=True)

		pos.append("payments", {'mode_of_payment': 'Bank Draft', 'account': '_Test Bank - _TC', 'amount': 500})
		pos.append("payments", {'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': 500})
		pos.insert()
		pos.submit()

		pos_return = make_sales_return(pos.name)

		pos_return.insert()
		pos_return.submit()

		self.assertEqual(pos_return.get('payments')[0].amount, -500)
		self.assertEqual(pos_return.get('payments')[1].amount, -500)
	
	def test_pos_change_amount(self):
		pos = create_pos_invoice(company= "_Test Company", debit_to="Debtors - _TC",
			income_account = "Sales - _TC", expense_account = "Cost of Goods Sold - _TC", rate=105,
			cost_center = "Main - _TC", do_not_save=True)

		pos.append("payments", {'mode_of_payment': 'Bank Draft', 'account': '_Test Bank - _TC', 'amount': 50})
		pos.append("payments", {'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': 60})

		pos.insert()
		pos.submit()

		self.assertEqual(pos.grand_total, 105.0)
		self.assertEqual(pos.change_amount, 5.0)
	
	def test_without_payment(self):
		inv = create_pos_invoice(do_not_save=1)
		# Check that the invoice cannot be submitted without payments
		inv.payments = []
		self.assertRaises(frappe.ValidationError, inv.insert)
	
	def test_serialized_item_transaction(self):
		from erpnext.stock.doctype.stock_entry.test_stock_entry import make_serialized_item
		from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos

		se = make_serialized_item(target_warehouse="_Test Warehouse - _TC")
		serial_nos = get_serial_nos(se.get("items")[0].serial_no)

		pos = create_pos_invoice(item=se.get("items")[0].item_code, rate=1000, do_not_save=1)
		pos.get("items")[0].serial_no = serial_nos[0]
		pos.append("payments", {'mode_of_payment': 'Bank Draft', 'account': '_Test Bank - _TC', 'amount': 1000})

		pos.insert()
		pos.submit()

		pos2 = create_pos_invoice(item=se.get("items")[0].item_code, rate=1000, do_not_save=1)
		pos2.get("items")[0].serial_no = serial_nos[0]
		pos2.append("payments", {'mode_of_payment': 'Bank Draft', 'account': '_Test Bank - _TC', 'amount': 1000})
		
		self.assertRaises(frappe.ValidationError, pos2.insert)
	
	def test_loyalty_points(self):
		from erpnext.accounts.doctype.loyalty_program.test_loyalty_program import create_records
		from erpnext.accounts.doctype.loyalty_program.loyalty_program import get_loyalty_program_details_with_points

		create_records()
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Single Loyalty")
		before_lp_details = get_loyalty_program_details_with_points("Test Loyalty Customer", company="_Test Company", loyalty_program="Test Single Loyalty")

		inv = create_pos_invoice(customer="Test Loyalty Customer", rate=10000)

		lpe = frappe.get_doc('Loyalty Point Entry', {'invoice_type': 'POS Invoice', 'invoice': inv.name, 'customer': inv.customer})
		after_lp_details = get_loyalty_program_details_with_points(inv.customer, company=inv.company, loyalty_program=inv.loyalty_program)

		self.assertEqual(inv.get('loyalty_program'), "Test Single Loyalty")
		self.assertEqual(lpe.loyalty_points, 10)
		self.assertEqual(after_lp_details.loyalty_points, before_lp_details.loyalty_points + 10)

		inv.cancel()
		after_cancel_lp_details = get_loyalty_program_details_with_points(inv.customer, company=inv.company, loyalty_program=inv.loyalty_program)
		self.assertEqual(after_cancel_lp_details.loyalty_points, before_lp_details.loyalty_points)
	
	def test_loyalty_points_redeemption(self):
		from erpnext.accounts.doctype.loyalty_program.loyalty_program import get_loyalty_program_details_with_points
		# add 10 loyalty points
		create_pos_invoice(customer="Test Loyalty Customer", rate=10000)

		before_lp_details = get_loyalty_program_details_with_points("Test Loyalty Customer", company="_Test Company", loyalty_program="Test Single Loyalty")
		
		inv = create_pos_invoice(customer="Test Loyalty Customer", rate=10000, do_not_save=1)
		inv.redeem_loyalty_points = 1
		inv.loyalty_points = before_lp_details.loyalty_points
		inv.loyalty_amount = inv.loyalty_points * before_lp_details.conversion_factor
		inv.append("payments", {'mode_of_payment': 'Cash', 'account': 'Cash - _TC', 'amount': 10000 - inv.loyalty_amount})
		inv.paid_amount = 10000
		inv.submit()

		after_redeem_lp_details = get_loyalty_program_details_with_points(inv.customer, company=inv.company, loyalty_program=inv.loyalty_program)
		self.assertEqual(after_redeem_lp_details.loyalty_points, 9)

def create_pos_invoice(**args):
	args = frappe._dict(args)
	pos_profile = None
	if not args.pos_profile:
		pos_profile = make_pos_profile()
		pos_profile.save()

	pos_inv = frappe.new_doc("POS Invoice")
	pos_inv.update_stock = 1
	pos_inv.is_pos = 1
	pos_inv.pos_profile = args.pos_profile or pos_profile.name

	pos_inv.set_missing_values()

	if args.posting_date:
		pos_inv.set_posting_time = 1
	pos_inv.posting_date = args.posting_date or frappe.utils.nowdate()

	pos_inv.company = args.company or "_Test Company"
	pos_inv.customer = args.customer or "_Test Customer"
	pos_inv.debit_to = args.debit_to or "Debtors - _TC"
	pos_inv.is_return = args.is_return
	pos_inv.return_against = args.return_against
	pos_inv.currency=args.currency or "INR"
	pos_inv.conversion_rate = args.conversion_rate or 1
	pos_inv.account_for_change_amount = "Cash - _TC"

	pos_inv.append("items", {
		"item_code": args.item or args.item_code or "_Test Item",
		"warehouse": args.warehouse or "_Test Warehouse - _TC",
		"qty": args.qty or 1,
		"rate": args.rate if args.get("rate") is not None else 100,
		"income_account": args.income_account or "Sales - _TC",
		"expense_account": args.expense_account or "Cost of Goods Sold - _TC",
		"cost_center": args.cost_center or "_Test Cost Center - _TC",
		"serial_no": args.serial_no
	})

	if not args.do_not_save:
		pos_inv.insert()
		if not args.do_not_submit:
			pos_inv.submit()
		else:
			pos_inv.payment_schedule = []
	else:
		pos_inv.payment_schedule = []

	return pos_inv