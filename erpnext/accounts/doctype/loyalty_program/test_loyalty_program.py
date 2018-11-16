# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
import unittest
from frappe.utils import today, cint, flt, getdate
from erpnext.accounts.doctype.loyalty_program.loyalty_program import get_loyalty_program_details_with_points

class TestLoyaltyProgram(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		# create relevant item, customer, loyalty program, etc
		create_records()

	def test_loyalty_points_earned_single_tier(self):
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Single Loyalty")
		# create a new sales invoice
		si_original = create_sales_invoice_record()
		si_original.insert()
		si_original.submit()

		customer = frappe.get_doc('Customer', {"customer_name": "Test Loyalty Customer"})
		earned_points = get_points_earned(si_original)

		lpe = frappe.get_doc('Loyalty Point Entry', {'sales_invoice': si_original.name, 'customer': si_original.customer})

		self.assertEqual(si_original.get('loyalty_program'), customer.loyalty_program)
		self.assertEqual(lpe.get('loyalty_program_tier'), customer.loyalty_program_tier)
		self.assertEqual(lpe.loyalty_points, earned_points)

		# add redemption point
		si_redeem = create_sales_invoice_record()
		si_redeem.redeem_loyalty_points = 1
		si_redeem.loyalty_points = earned_points
		si_redeem.insert()
		si_redeem.submit()

		earned_after_redemption = get_points_earned(si_redeem)

		lpe_redeem = frappe.get_doc('Loyalty Point Entry', {'sales_invoice': si_redeem.name, 'redeem_against': lpe.name})
		lpe_earn = frappe.get_doc('Loyalty Point Entry', {'sales_invoice': si_redeem.name, 'name': ['!=', lpe_redeem.name]})

		self.assertEqual(lpe_earn.loyalty_points, earned_after_redemption)
		self.assertEqual(lpe_redeem.loyalty_points, (-1*earned_points))

		# cancel and delete
		for d in [si_redeem, si_original]:
			d.cancel()
			frappe.delete_doc('Sales Invoice', d.name)

	def test_loyalty_points_earned_multiple_tier(self):
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Multiple Loyalty")
		# assign multiple tier program to the customer
		customer = frappe.get_doc('Customer', {"customer_name": "Test Loyalty Customer"})
		customer.loyalty_program = frappe.get_doc('Loyalty Program', {'loyalty_program_name': 'Test Multiple Loyalty'}).name
		customer.save()

		# create a new sales invoice
		si_original = create_sales_invoice_record()
		si_original.insert()
		si_original.submit()

		earned_points = get_points_earned(si_original)

		lpe = frappe.get_doc('Loyalty Point Entry', {'sales_invoice': si_original.name, 'customer': si_original.customer})

		self.assertEqual(si_original.get('loyalty_program'), customer.loyalty_program)
		self.assertEqual(lpe.get('loyalty_program_tier'), customer.loyalty_program_tier)
		self.assertEqual(lpe.loyalty_points, earned_points)

		# add redemption point
		si_redeem = create_sales_invoice_record()
		si_redeem.redeem_loyalty_points = 1
		si_redeem.loyalty_points = earned_points
		si_redeem.insert()
		si_redeem.submit()

		customer = frappe.get_doc('Customer', {"customer_name": "Test Loyalty Customer"})
		earned_after_redemption = get_points_earned(si_redeem)

		lpe_redeem = frappe.get_doc('Loyalty Point Entry', {'sales_invoice': si_redeem.name, 'redeem_against': lpe.name})
		lpe_earn = frappe.get_doc('Loyalty Point Entry', {'sales_invoice': si_redeem.name, 'name': ['!=', lpe_redeem.name]})

		self.assertEqual(lpe_earn.loyalty_points, earned_after_redemption)
		self.assertEqual(lpe_redeem.loyalty_points, (-1*earned_points))
		self.assertEqual(lpe_earn.loyalty_program_tier, customer.loyalty_program_tier)

		# cancel and delete
		for d in [si_redeem, si_original]:
			d.cancel()
			frappe.delete_doc('Sales Invoice', d.name)

	def test_cancel_sales_invoice(self):
		''' cancelling the sales invoice should cancel the earned points'''
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Single Loyalty")
		# create a new sales invoice
		si = create_sales_invoice_record()
		si.insert()
		si.submit()

		lpe = frappe.get_doc('Loyalty Point Entry', {'sales_invoice': si.name, 'customer': si.customer})
		self.assertEqual(True, not (lpe is None))

		# cancelling sales invoice
		si.cancel()
		lpe = frappe.db.exists('Loyalty Point Entry', lpe.name)
		self.assertEqual(True, (lpe is None))

	def test_sales_invoice_return(self):
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Single Loyalty")
		# create a new sales invoice
		si_original = create_sales_invoice_record(2)
		si_original.conversion_rate = flt(1)
		si_original.insert()
		si_original.submit()

		earned_points = get_points_earned(si_original)
		lpe_original = frappe.get_doc('Loyalty Point Entry', {'sales_invoice': si_original.name, 'customer': si_original.customer})
		self.assertEqual(lpe_original.loyalty_points, earned_points)

		# create sales invoice return
		si_return = create_sales_invoice_record(-1)
		si_return.conversion_rate = flt(1)
		si_return.is_return = 1
		si_return.return_against = si_original.name
		si_return.insert()
		si_return.submit()

		# fetch original invoice again as its status would have been updated
		si_original = frappe.get_doc('Sales Invoice', lpe_original.sales_invoice)

		earned_points = get_points_earned(si_original)
		lpe_after_return = frappe.get_doc('Loyalty Point Entry', {'sales_invoice': si_original.name, 'customer': si_original.customer})
		self.assertEqual(lpe_after_return.loyalty_points, earned_points)
		self.assertEqual(True, (lpe_original.loyalty_points > lpe_after_return.loyalty_points))

		# cancel and delete
		for d in [si_return, si_original]:
			try:
				d.cancel()
			except frappe.TimestampMismatchError:
				frappe.get_doc('Sales Invoice', d.name).cancel()
			frappe.delete_doc('Sales Invoice', d.name)

def get_points_earned(self):
	def get_returned_amount():
		returned_amount = frappe.db.sql("""
			select sum(grand_total)
			from `tabSales Invoice`
			where docstatus=1 and is_return=1 and ifnull(return_against, '')=%s
		""", self.name)
		return abs(flt(returned_amount[0][0])) if returned_amount else 0

	lp_details = get_loyalty_program_details_with_points(self.customer, company=self.company,
		loyalty_program=self.loyalty_program, expiry_date=self.posting_date, include_expired_entry=True)
	if lp_details and getdate(lp_details.from_date) <= getdate(self.posting_date) and \
		(not lp_details.to_date or getdate(lp_details.to_date) >= getdate(self.posting_date)):
		returned_amount = get_returned_amount()
		eligible_amount = flt(self.grand_total) - cint(self.loyalty_amount) - returned_amount
		points_earned = cint(eligible_amount/lp_details.collection_factor)

	return points_earned or 0

def create_sales_invoice_record(qty=1):
	# return sales invoice doc object
	return frappe.get_doc({
		"doctype": "Sales Invoice",
		"customer": frappe.get_doc('Customer', {"customer_name": "Test Loyalty Customer"}).name,
		"company": '_Test Company',
		"due_date": today(),
		"posting_date": today(),
		"currency": "INR",
		"taxes_and_charges": "",
		"debit_to": "Debtors - _TC",
		"taxes": [],
		"items": [{
			'doctype': 'Sales Invoice Item',
			'item_code': frappe.get_doc('Item', {'item_name': 'Loyal Item'}).name,
			'qty': qty,
			"rate": 10000,
			'income_account': 'Sales - _TC',
			'cost_center': 'Main - _TC',
			'expense_account': 'Cost of Goods Sold - _TC'
		}]
	})

def create_records():
	# create a new loyalty Account
	if frappe.db.exists("Account", "Loyalty - _TC"):
		return

	frappe.get_doc({
		"doctype": "Account",
		"account_name": "Loyalty",
		"parent_account": "Direct Expenses - _TC",
		"company": "_Test Company",
		"is_group": 0,
		"account_type": "Expense Account",
	}).insert()

	# create a new loyalty program Single tier
	frappe.get_doc({
		"doctype": "Loyalty Program",
		"loyalty_program_name": "Test Single Loyalty",
		"auto_opt_in": 1,
		"from_date": today(),
		"loyalty_program_type": "Single Tier Program",
		"conversion_factor": 1,
		"expiry_duration": 10,
		"company": "_Test Company",
		"cost_center": "Main - _TC",
		"expense_account": "Loyalty - _TC",
		"collection_rules": [{
			'tier_name': 'Silver',
			'collection_factor': 1000,
			'min_spent': 1000
		}]
	}).insert()

	# create a new customer
	frappe.get_doc({
		"customer_group": "_Test Customer Group",
		"customer_name": "Test Loyalty Customer",
		"customer_type": "Individual",
		"doctype": "Customer",
		"territory": "_Test Territory"
	}).insert()

	# create a new loyalty program Multiple tier
	frappe.get_doc({
		"doctype": "Loyalty Program",
		"loyalty_program_name": "Test Multiple Loyalty",
		"auto_opt_in": 1,
		"from_date": today(),
		"loyalty_program_type": "Multiple Tier Program",
		"conversion_factor": 1,
		"expiry_duration": 10,
		"company": "_Test Company",
		"cost_center": "Main - _TC",
		"expense_account": "Loyalty - _TC",
		"collection_rules": [
			{
				'tier_name': 'Silver',
				'collection_factor': 1000,
				'min_spent': 10000
			},
			{
				'tier_name': 'Gold',
				'collection_factor': 1000,
				'min_spent': 19000
			}
		]
	}).insert()

	# create an item
	item = frappe.get_doc({
		"doctype": "Item",
		"item_code": "Loyal Item",
		"item_name": "Loyal Item",
		"item_group": "All Item Groups",
		"company": "_Test Company",
		"is_stock_item": 1,
		"opening_stock": 100,
		"valuation_rate": 10000,
	}).insert()

	# create item price
	frappe.get_doc({
		"doctype": "Item Price",
		"price_list": "Standard Selling",
		"item_code": item.item_code,
		"price_list_rate": 10000
	}).insert()
