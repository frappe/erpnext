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
from erpnext.accounts.doctype.accounts_settings.accounts_settings import (
	toggle_loyalty_point_program_section,
)
from erpnext.accounts.party import get_dashboard_info
from erpnext.patches.v16_0.enable_loyalty_point_program_if_in_use import (
	execute as enable_loyalty_point_program,
)
from erpnext.tests.utils import ERPNextTestSuite, change_settings


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

		# cancelling sales invoice keeps the row and flags it
		si.cancel()
		self.assertEqual(frappe.db.get_value("Loyalty Point Entry", lpe.name, "is_cancelled"), 1)
		self.assertTrue(frappe.db.exists("Loyalty Point Entry", {"reversal_of": lpe.name}))

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

	def test_invalid_settings_are_rejected(self):
		cases = {
			"Collection Factor": {"collection_rules": [{"tier_name": "Bronze", "collection_factor": -100}]},
			"Conversion Factor": {"conversion_factor": -1},
			"Expiry Duration": {"expiry_duration": -30},
			"To Date": {"from_date": today(), "to_date": add_days(today(), -1)},
			"Company": {"company": None},
			"Multiple Tier Program": {
				"collection_rules": [
					{"tier_name": "Bronze", "collection_factor": 1000, "min_spent": 0},
					{"tier_name": "Silver", "collection_factor": 500, "min_spent": 10000},
				]
			},
		}
		for field, values in cases.items():
			with self.subTest(field=field):
				program = make_loyalty_program(**values)
				self.assertRaisesRegex(frappe.ValidationError, f"(?i){field}", program.insert)

	def test_valid_settings_are_saved(self):
		program = make_loyalty_program(expiry_duration=0, to_date=today(), conversion_factor=0).insert()
		self.assertTrue(program.name)

	@patch("erpnext.selling.doctype.customer.customer.get_default_company", return_value="_Test Company")
	def test_auto_opt_in_skips_other_company_program(self, _):
		frappe.db.set_value("Loyalty Program", {"company": "_Test Company"}, "auto_opt_in", 0)
		make_loyalty_program(
			loyalty_program_name="_Test Other Company Rewards",
			company="_Test Company 1",
			auto_opt_in=1,
			cost_center="Main - _TC1",
			expense_account=None,
		).insert()

		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test Loyalty Other Company Customer",
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
			}
		).insert()

		self.assertFalse(customer.loyalty_program)

	@patch("erpnext.selling.doctype.customer.customer.get_default_company", return_value="_Test Company 1")
	def test_invoice_enrols_customer_in_program_of_its_company(self, _):
		frappe.db.set_value("Loyalty Program", "Test Multiple Loyalty", "auto_opt_in", 0)
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test Loyalty Invoice Opt In Customer",
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
			}
		).insert()
		# saved by a user of another company, so not enrolled yet
		self.assertFalse(customer.loyalty_program)

		si = create_sales_invoice_record()
		si.customer = customer.name
		si.insert()
		si.submit()

		self.assertEqual(si.loyalty_program, "Test Single Loyalty")
		self.assertEqual(frappe.db.get_value("Customer", customer.name, "loyalty_program"), "Test Single Loyalty")
		self.assertEqual(frappe.db.get_value("Loyalty Point Entry", {"invoice": si.name}, "loyalty_points"), 10)

	def test_invoice_of_other_company_earns_no_points(self):
		program = make_loyalty_program(
			loyalty_program_name="_Test Other Company Rewards",
			company="_Test Company 1",
			cost_center="Main - _TC1",
			expense_account=None,
		).insert()
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", program.name)

		si = create_sales_invoice_record()
		si.insert()
		si.submit()

		self.assertEqual(si.loyalty_program, program.name)
		self.assertFalse(frappe.db.exists("Loyalty Point Entry", {"invoice": si.name}))

	def test_disabled_program_earns_and_redeems_nothing(self):
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Single Loyalty")
		si = create_sales_invoice_record()
		si.insert()
		si.submit()
		balance = get_loyalty_details("Test Loyalty Customer", "Test Single Loyalty").loyalty_points

		with change_settings("Accounts Settings", enable_loyalty_point_program=0):
			si_disabled = create_sales_invoice_record()
			si_disabled.insert()
			si_disabled.submit()
			self.assertFalse(frappe.db.exists("Loyalty Point Entry", {"invoice": si_disabled.name}))

			si_redeem = create_sales_invoice_record()
			si_redeem.redeem_loyalty_points = 1
			si_redeem.loyalty_points = 5
			self.assertRaisesRegex(frappe.ValidationError, "disabled", si_redeem.insert)

		self.assertEqual(
			get_loyalty_details("Test Loyalty Customer", "Test Single Loyalty").loyalty_points, balance
		)

	def test_patch_enables_program_setting_when_programs_exist(self):
		# property setters change cached meta, which the rollback does not undo
		self.addCleanup(frappe.clear_cache)
		frappe.db.set_single_value("Accounts Settings", "enable_loyalty_point_program", 0)
		toggle_loyalty_point_program_section(True)

		enable_loyalty_point_program()

		self.assertTrue(is_loyalty_program_setting_on())

	def test_patch_enables_program_setting_when_fields_are_shown(self):
		# property setters change cached meta, which the rollback does not undo
		self.addCleanup(frappe.clear_cache)
		frappe.db.set_single_value("Accounts Settings", "enable_loyalty_point_program", 0)
		frappe.db.delete("Loyalty Point Entry")
		frappe.db.delete("Loyalty Program")
		frappe.db.delete("Property Setter", {"field_name": "loyalty_points_redemption"})

		enable_loyalty_point_program()

		# a site set up before the setting existed still shows the loyalty fields
		self.assertTrue(is_loyalty_program_setting_on())

	def test_patch_keeps_program_setting_off_when_unused_and_hidden(self):
		# property setters change cached meta, which the rollback does not undo
		self.addCleanup(frappe.clear_cache)
		frappe.db.set_single_value("Accounts Settings", "enable_loyalty_point_program", 0)
		frappe.db.delete("Loyalty Point Entry")
		frappe.db.delete("Loyalty Program")
		toggle_loyalty_point_program_section(True)

		enable_loyalty_point_program()

		self.assertFalse(is_loyalty_program_setting_on())

	def test_redeem_without_program_is_refused(self):
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", None)

		si = create_sales_invoice_record()
		si.redeem_loyalty_points = 1
		si.loyalty_points = 10

		self.assertRaisesRegex(frappe.ValidationError, "not enrolled in a Loyalty Program", si.insert)

	def test_dashboard_shows_points_without_sales_invoice(self):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "_Test Loyalty POS Customer",
				"customer_group": "_Test Customer Group",
				"territory": "_Test Territory",
				"loyalty_program": "Test Single Loyalty",
			}
		).insert()
		make_points_entry(customer.name, "Test Single Loyalty", 30, invoice_type="POS Invoice")
		# not yet usable today, so not shown
		make_points_entry(customer.name, "Test Single Loyalty", 40, posting_date=add_days(today(), 3))

		info = get_dashboard_info("Customer", customer.name, customer.loyalty_program)

		self.assertEqual(len(info), 1)
		self.assertEqual(info[0]["company"], "_Test Company")
		self.assertEqual(info[0]["loyalty_points"], 30)

	def test_dashboard_shows_points_per_program(self):
		frappe.db.set_value("Customer", "Test Loyalty Customer", "loyalty_program", "Test Single Loyalty")
		make_points_entry("Test Loyalty Customer", "Test Multiple Loyalty", 200)
		si = create_sales_invoice_record()
		si.insert()
		si.submit()

		info = get_dashboard_info("Customer", "Test Loyalty Customer", "Test Single Loyalty")
		company = next(d for d in info if d["company"] == "_Test Company")

		self.assertEqual(company["loyalty_points"], 10)
		self.assertEqual(
			{d.loyalty_program: d.loyalty_points for d in company["loyalty_programs"]},
			{"Test Single Loyalty": 10, "Test Multiple Loyalty": 200},
		)


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


def make_loyalty_program(**values):
	program = frappe.get_doc(
		{
			"doctype": "Loyalty Program",
			"loyalty_program_name": "_Test Validation Loyalty",
			"loyalty_program_type": "Single Tier Program",
			"from_date": today(),
			"conversion_factor": 1,
			"expiry_duration": 10,
			"company": "_Test Company",
			"cost_center": "Main - _TC",
			"expense_account": "Loyalty - _TC",
			"collection_rules": [{"tier_name": "Bronze", "collection_factor": 1000, "min_spent": 0}],
		}
	)
	program.update(values)
	return program


def is_loyalty_program_setting_on():
	return frappe.db.get_single_value("Accounts Settings", "enable_loyalty_point_program", cache=False)


def make_points_entry(customer, loyalty_program, points, invoice_type="Sales Invoice", posting_date=None):
	return frappe.get_doc(
		{
			"doctype": "Loyalty Point Entry",
			"loyalty_program": loyalty_program,
			"customer": customer,
			"entry_type": "Earn",
			"invoice_type": invoice_type,
			"loyalty_points": points,
			"expiry_date": add_days(today(), 10),
			"posting_date": posting_date or today(),
			"company": "_Test Company",
		}
	).insert(ignore_permissions=True)
