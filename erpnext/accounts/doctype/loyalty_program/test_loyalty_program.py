# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from unittest.mock import patch

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import add_days, cint, flt, getdate, today

from erpnext.accounts.doctype.loyalty_program.loyalty_program import (
	get_loyalty_details,
	get_loyalty_program_details_with_points,
)
from erpnext.accounts.party import get_dashboard_info
from erpnext.tests.utils import ERPNextTestSuite


class TestLoyaltyProgram(ERPNextTestSuite):
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

	@patch("erpnext.accounts.doctype.loyalty_program.loyalty_program.get_loyalty_details")
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

	def test_points_never_expire_when_expiry_duration_is_zero(self):
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Single Loyalty")
		frappe.db.set_value(
			"Loyalty Program",
			"Test Single Loyalty",
			{"expiry_duration": 0, "from_date": add_days(today(), -30)},
		)
		before = get_loyalty_program_details_with_points(
			"Test Loyalty Customer", company="_Test Company", loyalty_program="Test Single Loyalty"
		)

		si = create_sales_invoice_record()
		si.set_posting_time = 1
		si.posting_date = add_days(today(), -1)
		si.insert()
		si.submit()

		after = get_loyalty_program_details_with_points(
			"Test Loyalty Customer", company="_Test Company", loyalty_program="Test Single Loyalty"
		)
		self.assertEqual(after.loyalty_points, before.loyalty_points + 10)
		self.assertEqual(
			getdate(frappe.db.get_value("Loyalty Point Entry", {"invoice": si.name}, "expiry_date")),
			getdate("9999-12-31"),
		)

	def test_redemption_does_not_count_as_spending(self):
		customer = make_loyalty_customer(
			"Test Redemption Spend Loyalty",
			[
				{"tier_name": "Silver", "collection_factor": 1, "min_spent": 0},
				{"tier_name": "Gold", "collection_factor": 0.5, "min_spent": 2500},
			],
		)
		for rate in (600, 400):
			make_loyalty_invoice(customer, rate)
		make_loyalty_invoice(customer, 1000, redeem=700)

		details = get_loyalty_program_details_with_points(
			customer,
			loyalty_program="Test Redemption Spend Loyalty",
			company="_Test Company",
			include_expired_entry=True,
		)
		self.assertEqual(details.total_spent, 1300)
		self.assertEqual(details.tier_name, "Silver")
		self.assertEqual(frappe.db.get_value("Customer", customer, "loyalty_program_tier"), "Silver")

	def test_return_after_points_are_redeemed(self):
		customer = make_loyalty_customer(
			"Test Return Redeemed Loyalty", [{"tier_name": "Basic", "collection_factor": 1, "min_spent": 0}]
		)
		invoice = make_loyalty_invoice(customer, 500, qty=2)
		earning = frappe.db.get_value("Loyalty Point Entry", {"invoice": invoice.name}, "name")
		make_loyalty_invoice(customer, 100, redeem=10)
		self.assertTrue(frappe.db.exists("Loyalty Point Entry", {"redeem_against": earning}))

		first_return = make_loyalty_invoice(customer, 500, qty=-1, return_against=invoice.name)
		self.assertEqual(frappe.db.get_value("Loyalty Point Entry", earning, "loyalty_points"), 500)

		frappe.db.savepoint("second_return")
		self.assertRaisesRegex(
			frappe.ValidationError,
			"already redeemed",
			make_loyalty_invoice,
			customer,
			500,
			qty=-1,
			return_against=invoice.name,
		)
		frappe.db.rollback(save_point="second_return")

		first_return.cancel()
		self.assertEqual(frappe.db.get_value("Loyalty Point Entry", earning, "loyalty_points"), 1000)

	def test_return_ignores_entries_of_another_invoice_type(self):
		customer = make_loyalty_customer(
			"Test Return Invoice Type Loyalty",
			[{"tier_name": "Basic", "collection_factor": 1, "min_spent": 0}],
		)
		invoice = make_loyalty_invoice(customer, 500, qty=2)
		earning = frappe.get_doc("Loyalty Point Entry", {"invoice": invoice.name})
		# entries of a POS Invoice with the same name, with some of its points redeemed
		pos_earning = frappe.copy_doc(earning)
		pos_earning.invoice_type = "POS Invoice"
		pos_earning.insert(ignore_links=True)
		pos_redemption = frappe.copy_doc(pos_earning)
		pos_redemption.update(
			{"redeem_against": pos_earning.name, "loyalty_points": -10, "purchase_amount": 0}
		)
		pos_redemption.insert(ignore_links=True)

		make_loyalty_invoice(customer, 500, qty=-1, return_against=invoice.name)
		self.assertEqual(
			frappe.db.get_value(
				"Loyalty Point Entry",
				{"invoice_type": "Sales Invoice", "invoice": invoice.name, "loyalty_points": (">", 0)},
				"loyalty_points",
			),
			500,
		)
		self.assertEqual(frappe.db.get_value("Loyalty Point Entry", pos_earning.name, "loyalty_points"), 1000)
		self.assertTrue(frappe.db.exists("Loyalty Point Entry", pos_redemption.name))


def get_points_earned(self):
	def get_returned_amount():
		si = frappe.qb.DocType("Sales Invoice")
		returned_amount = (
			frappe.qb.from_(si)
			.select(Sum(si.grand_total))
			.where((si.docstatus == 1) & (si.is_return == 1) & (si.return_against == self.name))
		).run()
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


def make_loyalty_customer(program_name, collection_rules):
	if not frappe.db.exists("Loyalty Program", program_name):
		frappe.get_doc(
			{
				"doctype": "Loyalty Program",
				"loyalty_program_name": program_name,
				"from_date": today(),
				"loyalty_program_type": "Multiple Tier Program"
				if len(collection_rules) > 1
				else "Single Tier Program",
				"conversion_factor": 1,
				"expiry_duration": 10,
				"company": "_Test Company",
				"cost_center": "Main - _TC",
				"expense_account": "Loyalty - _TC",
				"collection_rules": collection_rules,
			}
		).insert()
	return (
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": f"{program_name} Customer",
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
				"loyalty_program": program_name,
			}
		)
		.insert()
		.name
	)


def make_loyalty_invoice(customer, rate, qty=1, redeem=0, return_against=None):
	si = create_sales_invoice_record(qty)
	si.customer = customer
	si.items[0].rate = rate
	if redeem:
		si.redeem_loyalty_points = 1
		si.loyalty_points = redeem
	if return_against:
		si.is_return = 1
		si.return_against = return_against
	si.insert()
	si.submit()
	return si
