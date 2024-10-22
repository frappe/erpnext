# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import cint, flt, getdate, today

from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
	get_loyalty_details,
	get_loyalty_program_details_with_points,
)
from erpnext.accounts.party import get_dashboard_info


class TestLoyaltyProgram(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# create relevant item, customer, loyalty program, etc
		create_records()

	def test_loyalty_points_earned_single_tier(self):
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Single Loyalty")
		# create a new sales invoice
		si_original = create_sales_invoice_record()
		si_original.insert()
		si_original.submit()

		customer = frappe.get_doc("Customer", {"customer_name": "Test Loyalty Customer"})
		earned_points = get_points_earned(si_original)

		lpe = frappe.get_doc(
			"Loyalty Point Entry",
			{
				"invoice_type": "Sales Invoice",
				"invoice": si_original.name,
				"customer": si_original.customer,
			},
		)

		self.assertEqual(si_original.get("loyalty_program"), customer.loyalty_program)
		self.assertEqual(lpe.get("loyalty_program_tier"), "Bronce")  # is always in the first tier
		self.assertEqual(lpe.get("loyalty_program_tier"), customer.loyalty_program_tier)
		self.assertEqual(lpe.loyalty_points, earned_points)

		# add redemption point
		si_redeem = create_sales_invoice_record()
		si_redeem.redeem_loyalty_points = 1
		si_redeem.loyalty_points = earned_points
		si_redeem.insert()
		si_redeem.submit()

		earned_after_redemption = get_points_earned(si_redeem)

		lpe_redeem = frappe.get_doc(
			"Loyalty Point Entry",
			{"invoice_type": "Sales Invoice", "invoice": si_redeem.name, "redeem_against": lpe.name},
		)
		lpe_earn = frappe.get_doc(
			"Loyalty Point Entry",
			{"invoice_type": "Sales Invoice", "invoice": si_redeem.name, "name": ["!=", lpe_redeem.name]},
		)

		self.assertEqual(lpe_earn.loyalty_points, earned_after_redemption)
		self.assertEqual(lpe_redeem.loyalty_points, (-1 * earned_points))

		# cancel and delete
		for d in [si_redeem, si_original]:
			d.cancel()

	def test_loyalty_points_earned_multiple_tier(self):
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Multiple Loyalty")
		# assign multiple tier program to the customer
		customer = frappe.get_doc("Customer", {"customer_name": "Test Loyalty Customer"})
		customer.loyalty_program = frappe.get_doc(
			"Loyalty Program", {"loyalty_program_name": "Test Multiple Loyalty"}
		).name
		customer.save()

		# create a new sales invoice
		si_original = create_sales_invoice_record()
		si_original.insert()
		si_original.submit()
		customer.reload()

		earned_points = get_points_earned(si_original)

		lpe = frappe.get_doc(
			"Loyalty Point Entry",
			{
				"invoice_type": "Sales Invoice",
				"invoice": si_original.name,
				"customer": si_original.customer,
			},
		)

		self.assertEqual(si_original.get("loyalty_program"), customer.loyalty_program)
		self.assertEqual(lpe.get("loyalty_program_tier"), customer.loyalty_program_tier)
		self.assertEqual(lpe.loyalty_points, earned_points)

		# add redemption point
		si_redeem = create_sales_invoice_record()
		si_redeem.redeem_loyalty_points = 1
		si_redeem.loyalty_points = earned_points
		si_redeem.insert()
		si_redeem.submit()
		customer.reload()

		earned_after_redemption = get_points_earned(si_redeem)

		lpe_redeem = frappe.get_doc(
			"Loyalty Point Entry",
			{"invoice_type": "Sales Invoice", "invoice": si_redeem.name, "redeem_against": lpe.name},
		)
		lpe_earn = frappe.get_doc(
			"Loyalty Point Entry",
			{"invoice_type": "Sales Invoice", "invoice": si_redeem.name, "name": ["!=", lpe_redeem.name]},
		)

		self.assertEqual(lpe_earn.loyalty_points, earned_after_redemption)
		self.assertEqual(lpe_redeem.loyalty_points, (-1 * earned_points))
		self.assertEqual(lpe_earn.loyalty_program_tier, customer.loyalty_program_tier)

		# cancel and delete
		for d in [si_redeem, si_original]:
			d.cancel()

	def test_cancel_sales_invoice(self):
		"""cancelling the sales invoice should cancel the earned points"""
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Single Loyalty")
		# create a new sales invoice
		si = create_sales_invoice_record()
		si.insert()
		si.submit()

		lpe = frappe.get_doc(
			"Loyalty Point Entry",
			{"invoice_type": "Sales Invoice", "invoice": si.name, "customer": si.customer},
		)
		self.assertEqual(True, lpe is not None)

		# cancelling sales invoice
		si.cancel()
		lpe = frappe.db.exists("Loyalty Point Entry", lpe.name)
		self.assertEqual(True, (lpe is None))

	def test_sales_invoice_return(self):
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Single Loyalty")
		# create a new sales invoice
		si_original = create_sales_invoice_record(2)
		si_original.conversion_rate = flt(1)
		si_original.insert()
		si_original.submit()

		earned_points = get_points_earned(si_original)
		lpe_original = frappe.get_doc(
			"Loyalty Point Entry",
			{
				"invoice_type": "Sales Invoice",
				"invoice": si_original.name,
				"customer": si_original.customer,
			},
		)
		self.assertEqual(lpe_original.loyalty_points, earned_points)

		# create sales invoice return
		si_return = create_sales_invoice_record(-1)
		si_return.conversion_rate = flt(1)
		si_return.is_return = 1
		si_return.return_against = si_original.name
		si_return.insert()
		si_return.submit()

		# fetch original invoice again as its status would have been updated
		si_original = frappe.get_doc("Sales Invoice", lpe_original.invoice)

		earned_points = get_points_earned(si_original)
		lpe_after_return = frappe.get_doc(
			"Loyalty Point Entry",
			{
				"invoice_type": "Sales Invoice",
				"invoice": si_original.name,
				"customer": si_original.customer,
			},
		)
		self.assertEqual(lpe_after_return.loyalty_points, earned_points)
		self.assertEqual(True, (lpe_original.loyalty_points > lpe_after_return.loyalty_points))

		# cancel and delete
		for d in [si_return, si_original]:
			try:
				d.cancel()
			except frappe.TimestampMismatchError:
				frappe.get_doc("Sales Invoice", d.name).cancel()

	def test_loyalty_points_for_dashboard(self):
		doc = frappe.get_doc("Customer", "Test Loyalty Customer")
		company_wise_info = get_dashboard_info("Customer", doc.name, doc.loyalty_program)

		for d in company_wise_info:
			self.assertTrue(d.get("loyalty_points"))

	@unittest.mock.patch("erpnext.accounts.doctype.loyalty_program.loyalty_program.get_loyalty_details")
	def test_tier_selection(self, mock_get_loyalty_details):
		# Create a new loyalty program with multiple tiers
		loyalty_program = frappe.get_doc(
			{
				"doctype": "Loyalty Program",
				"loyalty_program_name": "Test Tier Selection",
				"auto_opt_in": 1,
				"from_date": today(),
				"loyalty_program_type": "Multiple Tier Program",
				"conversion_factor": 1,
				"expiry_duration": 10,
				"company": "_Test Company",
				"cost_center": "Main - _TC",
				"expense_account": "Loyalty - _TC",
				"collection_rules": [
					{"tier_name": "Gold", "collection_factor": 1000, "min_spent": 20000},
					{"tier_name": "Silver", "collection_factor": 1000, "min_spent": 10000},
					{"tier_name": "Bronze", "collection_factor": 1000, "min_spent": 0},
				],
			}
		)
		loyalty_program.insert()

		# Test cases with different total_spent and current_transaction_amount combinations
		test_cases = [
			(0, 6000, "Bronze"),
			(0, 15000, "Silver"),
			(0, 25000, "Gold"),
			(4000, 500, "Bronze"),
			(8000, 3000, "Silver"),
			(18000, 3000, "Gold"),
			(22000, 5000, "Gold"),
		]

		for total_spent, current_transaction_amount, expected_tier in test_cases:
			with self.subTest(total_spent=total_spent, current_transaction_amount=current_transaction_amount):
				# Mock the get_loyalty_details function to update the total_spent
				def side_effect(*args, **kwargs):
					result = get_loyalty_details(*args, **kwargs)
					result.update({"total_spent": total_spent})
					return result

				mock_get_loyalty_details.side_effect = side_effect

				lp_details = get_loyalty_program_details_with_points(
					"Test Loyalty Customer",
					loyalty_program=loyalty_program.name,
					company="_Test Company",
					current_transaction_amount=current_transaction_amount,
				)

				# Get the selected tier based on the current implementation
				selected_tier = lp_details.tier_name

				self.assertEqual(
					selected_tier,
					expected_tier,
					f"Expected tier {expected_tier} for total_spent {total_spent} and current_transaction_amount {current_transaction_amount}, but got {selected_tier}",
				)

		# Clean up
		loyalty_program.delete()


def get_points_earned(self):
	def get_returned_amount():
		returned_amount = frappe.db.sql(
			"""
			select sum(grand_total)
			from `tabSales Invoice`
			where docstatus=1 and is_return=1 and ifnull(return_against, '')=%s
		""",
			self.name,
		)
		return abs(flt(returned_amount[0][0])) if returned_amount else 0

	lp_details = get_loyalty_program_details_with_points(
		self.customer,
		company=self.company,
		loyalty_program=self.loyalty_program,
		expiry_date=self.posting_date,
		include_expired_entry=True,
	)
	if (
		lp_details
		and getdate(lp_details.from_date) <= getdate(self.posting_date)
		and (not lp_details.to_date or getdate(lp_details.to_date) >= getdate(self.posting_date))
	):
		returned_amount = get_returned_amount()
		eligible_amount = flt(self.grand_total) - cint(self.loyalty_amount) - returned_amount
		points_earned = cint(eligible_amount / lp_details.collection_factor)

	return points_earned or 0


def create_sales_invoice_record(qty=1):
	# return sales invoice doc object
	return frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": frappe.get_doc("Customer", {"customer_name": "Test Loyalty Customer"}).name,
			"company": "_Test Company",
			"due_date": today(),
			"posting_date": today(),
			"currency": "INR",
			"taxes_and_charges": "",
			"debit_to": "Debtors - _TC",
			"taxes": [],
			"items": [
				{
					"doctype": "Sales Invoice Item",
					"item_code": frappe.get_doc("Item", {"item_name": "Loyal Item"}).name,
					"qty": qty,
					"rate": 10000,
					"income_account": "Sales - _TC",
					"cost_center": "Main - _TC",
					"expense_account": "Cost of Goods Sold - _TC",
				}
			],
		}
	)


def create_records():
	# create a new loyalty Account
	if not frappe.db.exists("Account", "Loyalty - _TC"):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": "Loyalty",
				"parent_account": "Direct Expenses - _TC",
				"company": "_Test Company",
				"is_group": 0,
				"account_type": "Expense Account",
			}
		).insert()

	# create a new loyalty program Single tier
	if not frappe.db.exists("Loyalty Program", "Test Single Loyalty"):
		frappe.get_doc(
			{
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
				"collection_rules": [{"tier_name": "Bronce", "collection_factor": 1000, "min_spent": 0}],
			}
		).insert()

	# create a new customer
	if not frappe.db.exists("Customer", "Test Loyalty Customer"):
		frappe.get_doc(
			{
				"customer_group": "_Test Customer Group",
				"customer_name": "Test Loyalty Customer",
				"customer_type": "Individual",
				"doctype": "Customer",
				"territory": "_Test Territory",
			}
		).insert()

	# create a new loyalty program Multiple tier
	if not frappe.db.exists("Loyalty Program", "Test Multiple Loyalty"):
		frappe.get_doc(
			{
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
					{"tier_name": "Bronze", "collection_factor": 1000, "min_spent": 0},
					{"tier_name": "Silver", "collection_factor": 1000, "min_spent": 10000},
					{"tier_name": "Gold", "collection_factor": 1000, "min_spent": 19000},
				],
			}
		).insert()

	# create an item
	if not frappe.db.exists("Item", "Loyal Item"):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "Loyal Item",
				"item_name": "Loyal Item",
				"item_group": "All Item Groups",
				"company": "_Test Company",
				"is_stock_item": 1,
				"opening_stock": 100,
				"valuation_rate": 10000,
			}
		).insert()

	# create item price
	if not frappe.db.exists("Item Price", {"price_list": "Standard Selling", "item_code": "Loyal Item"}):
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"price_list": "Standard Selling",
				"item_code": "Loyal Item",
				"price_list_rate": 10000,
			}
		).insert()
