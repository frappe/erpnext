# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.query_builder.functions import Sum
from frappe.utils import today

from erpnext.accounts.doctype.loyalty_program.loyalty_program import get_loyalty_details
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.patches.v16_0.set_entry_type_in_loyalty_point_entry import execute as label_entries
from erpnext.tests.utils import ERPNextTestSuite


class TestLoyaltyPointEntry(ERPNextTestSuite):
	def setUp(self):
		# Create test records
		self.loyalty_program_name = "Test Single Loyalty"
		self.customer_name = "Test Loyalty Customer"
		customer = frappe.get_doc("Customer", self.customer_name)
		customer.loyalty_program = self.loyalty_program_name
		customer.save()

	def create_test_invoice(self, redeem=None):
		if redeem:
			si = create_sales_invoice(customer=self.customer_name, qty=1, rate=100, do_not_save=True)
			si.redeem_loyalty_points = True
			si.loyalty_points = redeem
			return si.insert().submit()
		else:
			si = create_sales_invoice(customer=self.customer_name, qty=10, rate=1000, do_not_save=True)
			return si.insert().submit()

	def test_add_loyalty_points(self):
		self.create_test_invoice()
		doc = frappe.get_last_doc("Loyalty Point Entry")
		self.assertEqual(doc.loyalty_points, 10)

	def test_add_loyalty_points_with_discretionary_reason(self):
		doc = frappe.get_doc(
			{
				"doctype": "Loyalty Point Entry",
				"loyalty_program": "Test Single Loyalty",
				"loyalty_program_tier": "Bronce",
				"customer": self.customer_name,
				"invoice_type": "Sales Invoice",
				"loyalty_points": 75,
				"expiry_date": today(),
				"posting_date": today(),
				"company": "_Test Company",
				"discretionary_reason": "Customer Appreciation",
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.loyalty_points, 75)
		self.assertEqual(doc.discretionary_reason, "Customer Appreciation")

		# Verify the entry in the database
		entry = frappe.get_doc("Loyalty Point Entry", doc.name)
		self.assertEqual(entry.loyalty_points, 75)
		self.assertEqual(entry.discretionary_reason, "Customer Appreciation")

	def test_redeem_loyalty_points(self):
		self.create_test_invoice()
		self.create_test_invoice(redeem=7)
		doc = frappe.get_last_doc("Loyalty Point Entry")
		self.assertEqual(doc.loyalty_points, -7)

		# Check balance
		lpe = frappe.qb.DocType("Loyalty Point Entry")
		balance = (
			frappe.qb.from_(lpe).select(Sum(lpe.loyalty_points)).where(lpe.customer == self.customer_name)
		).run()[0][0]

		self.assertEqual(balance, 3)  # 10 added, 7 redeemed

	def test_earn_and_redeem_rows_are_typed(self):
		earn_invoice = self.create_test_invoice()
		redeem_invoice = self.create_test_invoice(redeem=7)

		earn = frappe.get_doc("Loyalty Point Entry", {"invoice": earn_invoice.name})
		self.assertEqual(earn.entry_type, "Earn")
		self.assertEqual(earn.earn_rate, 1000)
		self.assertEqual(earn.amount, 10)

		redeem = frappe.get_doc(
			"Loyalty Point Entry", {"invoice": redeem_invoice.name, "entry_type": "Redeem"}
		)
		self.assertEqual(redeem.redeem_against, earn.name)
		self.assertEqual(redeem.loyalty_points, -7)
		self.assertEqual(redeem.amount, -7)
		self.assertEqual(redeem.purchase_amount, 0)

	def test_redemption_is_not_tier_spend(self):
		self.create_test_invoice()
		self.create_test_invoice(redeem=7)

		details = get_loyalty_details(self.customer_name, self.loyalty_program_name, company="_Test Company")

		# 10,000 earned on the first invoice and 100 - 7 on the second; the redemption adds nothing
		self.assertEqual(details.total_spent, 10093)

	def test_cancelled_rows_are_not_counted(self):
		self.create_test_invoice()
		cancelled = self.create_test_invoice()
		frappe.db.set_value("Loyalty Point Entry", {"invoice": cancelled.name}, "is_cancelled", 1)

		details = get_loyalty_details(self.customer_name, self.loyalty_program_name, company="_Test Company")

		self.assertEqual(details.loyalty_points, 10)
		self.assertEqual(details.total_spent, 10000)

	def test_patch_labels_rows_without_changing_balance(self):
		self.create_test_invoice()
		redeem_invoice = self.create_test_invoice(redeem=7)
		adjustment = frappe.get_doc(
			{
				"doctype": "Loyalty Point Entry",
				"loyalty_program": self.loyalty_program_name,
				"customer": self.customer_name,
				"loyalty_points": 5,
				"expiry_date": today(),
				"posting_date": today(),
				"company": "_Test Company",
				"discretionary_reason": "Opening balance",
			}
		).insert(ignore_permissions=True)

		# rows written before the patch have no type, and redemptions carry the invoice total
		lpe = frappe.qb.DocType("Loyalty Point Entry")
		frappe.qb.update(lpe).set(lpe.entry_type, "").where(lpe.customer == self.customer_name).run()
		frappe.db.set_value(
			"Loyalty Point Entry",
			{"invoice": redeem_invoice.name, "redeem_against": ["is", "set"]},
			"purchase_amount",
			100,
		)
		balance_before = self.get_balance()

		label_entries()

		self.assertEqual(self.get_balance(), balance_before)
		self.assertEqual(
			frappe.db.get_value("Loyalty Point Entry", adjustment.name, "entry_type"), "Adjustment"
		)
		self.assertEqual(
			frappe.get_all(
				"Loyalty Point Entry",
				filters={"invoice": redeem_invoice.name},
				fields=["entry_type", "purchase_amount"],
				order_by="entry_type",
			),
			[{"entry_type": "Earn", "purchase_amount": 93}, {"entry_type": "Redeem", "purchase_amount": 0}],
		)

	def test_cancel_keeps_rows_and_adds_reverse_rows(self):
		self.create_test_invoice()
		redeem_invoice = self.create_test_invoice(redeem=7)
		rows = frappe.get_all("Loyalty Point Entry", filters={"invoice": redeem_invoice.name}, pluck="name")

		redeem_invoice.cancel()

		for name in rows:
			self.assertEqual(frappe.db.get_value("Loyalty Point Entry", name, "is_cancelled"), 1)
			reverse = frappe.get_doc("Loyalty Point Entry", {"reversal_of": name})
			self.assertEqual(reverse.is_cancelled, 1)
			self.assertEqual(
				reverse.loyalty_points, -frappe.db.get_value("Loyalty Point Entry", name, "loyalty_points")
			)

		self.assertEqual(
			frappe.get_all(
				"Loyalty Point Entry",
				filters={"invoice": redeem_invoice.name},
				fields=[{"SUM": "loyalty_points", "as": "points"}],
			)[0].points,
			0,
		)
		self.assertEqual(self.get_balance(), 10)

	def test_cancel_invoice_paid_with_points_restores_them(self):
		self.create_test_invoice()
		# 100 - 7 earns 0 points, so the invoice has only a redemption to undo
		redeem_invoice = self.create_test_invoice(redeem=7)

		redeem_invoice.cancel()

		details = get_loyalty_details(self.customer_name, self.loyalty_program_name, company="_Test Company")
		self.assertEqual(details.loyalty_points, 10)

	def test_cancel_of_redeemed_earning_is_refused(self):
		earn_invoice = self.create_test_invoice()
		self.create_test_invoice(redeem=7)

		self.assertRaisesRegex(frappe.ValidationError, "has been redeemed", earn_invoice.cancel)

	def get_balance(self):
		lpe = frappe.qb.DocType("Loyalty Point Entry")
		return (
			frappe.qb.from_(lpe).select(Sum(lpe.loyalty_points)).where(lpe.customer == self.customer_name)
		).run()[0][0]
