# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import json

import frappe
from frappe.model import mapper
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate, today

from erpnext import get_default_cost_center
from erpnext.accounts.doctype.payment_entry.test_payment_entry import get_payment_entry
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import (
	unlink_payment_on_cancel_of_invoice,
)
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
	create_dunning as create_dunning_from_sales_invoice,
)
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import (
	create_sales_invoice_against_cost_center,
)

EXTRA_TEST_RECORD_DEPENDENCIES = ["Company", "Cost Center"]


class TestDunning(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_dunning_type("First Notice", fee=0.0, interest=0.0, is_default=1)
		create_dunning_type("Second Notice", fee=10.0, interest=10.0, is_default=0)
		unlink_payment_on_cancel_of_invoice()

	@classmethod
	def tearDownClass(cls):
		unlink_payment_on_cancel_of_invoice(0)
		super().tearDownClass()

	def test_dunning_without_fees(self):
		dunning = create_dunning(overdue_days=20)

		self.assertEqual(round(dunning.total_outstanding, 2), 100.00)
		self.assertEqual(round(dunning.total_interest, 2), 0.00)
		self.assertEqual(round(dunning.dunning_fee, 2), 0.00)
		self.assertEqual(round(dunning.dunning_amount, 2), 0.00)
		self.assertEqual(round(dunning.grand_total, 2), 100.00)

	def test_dunning_with_fees_and_interest(self):
		dunning = create_dunning(overdue_days=15, dunning_type_name="Second Notice - _TC")

		self.assertEqual(round(dunning.total_outstanding, 2), 100.00)
		self.assertEqual(round(dunning.total_interest, 2), 0.41)
		self.assertEqual(round(dunning.dunning_fee, 2), 10.00)
		self.assertEqual(round(dunning.dunning_amount, 2), 10.41)
		self.assertEqual(round(dunning.grand_total, 2), 110.41)

	def test_dunning_with_payment_entry(self):
		dunning = create_dunning(overdue_days=15, dunning_type_name="Second Notice - _TC")
		dunning.submit()
		pe = get_payment_entry("Dunning", dunning.name)
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.insert()
		pe.submit()

		for overdue_payment in dunning.overdue_payments:
			outstanding_amount = frappe.get_value(
				"Sales Invoice", overdue_payment.sales_invoice, "outstanding_amount"
			)
			self.assertEqual(outstanding_amount, 0)

		dunning.reload()
		self.assertEqual(dunning.status, "Resolved")

	def test_fetch_overdue_payments(self):
		"""
		Create SI with overdue payment. Check if overdue payment is fetched in Dunning.
		"""
		si1 = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -1 * 6),
			qty=1,
			rate=100,
		)

		si2 = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -1 * 6),
			qty=1,
			rate=300,
		)

		dunning = create_dunning_from_sales_invoice(si1.name)
		dunning.overdue_payments = []

		method = "erpnext.accounts.doctype.sales_invoice.sales_invoice.create_dunning"
		updated_dunning = mapper.map_docs(method, json.dumps([si1.name, si2.name]), dunning)

		self.assertEqual(len(updated_dunning.overdue_payments), 2)

		self.assertEqual(updated_dunning.overdue_payments[0].sales_invoice, si1.name)
		self.assertEqual(updated_dunning.overdue_payments[0].outstanding, si1.outstanding_amount)

		self.assertEqual(updated_dunning.overdue_payments[1].sales_invoice, si2.name)
		self.assertEqual(updated_dunning.overdue_payments[1].outstanding, si2.outstanding_amount)

	def test_dunning_and_payment_against_partially_due_invoice(self):
		"""
		Create SI with first installment overdue. Check impact of Dunning and Payment Entry.
		"""
		create_payment_terms_template_for_dunning()
		sales_invoice = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -1 * 6),
			qty=1,
			rate=100,
			do_not_submit=True,
		)
		sales_invoice.payment_terms_template = "_Test 50-50 for Dunning"
		sales_invoice.submit()
		dunning = create_dunning_from_sales_invoice(sales_invoice.name)

		self.assertEqual(len(dunning.overdue_payments), 1)
		self.assertEqual(dunning.overdue_payments[0].payment_term, "_Test Payment Term 1 for Dunning")

		dunning.submit()
		pe = get_payment_entry("Dunning", dunning.name)
		pe.reference_no, pe.reference_date = "2", nowdate()
		pe.insert()
		pe.submit()
		sales_invoice.load_from_db()
		dunning.load_from_db()

		self.assertEqual(sales_invoice.status, "Partly Paid")
		self.assertEqual(sales_invoice.payment_schedule[0].outstanding, 0)
		self.assertEqual(dunning.status, "Resolved")

		# Test impact on cancellation of PE
		pe.cancel()
		sales_invoice.reload()
		dunning.reload()

		self.assertEqual(sales_invoice.status, "Overdue")
		self.assertEqual(dunning.status, "Unresolved")

	def test_dunning_resolution_from_credit_note(self):
		"""
		Test that dunning is resolved when a credit note is issued against the original invoice.
		"""
		sales_invoice = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -10), qty=1, rate=100
		)
		dunning = create_dunning_from_sales_invoice(sales_invoice.name)
		dunning.submit()

		self.assertEqual(dunning.status, "Unresolved")

		credit_note = frappe.copy_doc(sales_invoice)
		credit_note.is_return = 1
		credit_note.return_against = sales_invoice.name
		credit_note.update_outstanding_for_self = 0

		for item in credit_note.items:
			item.qty = -item.qty

		credit_note.save()
		credit_note.submit()

		dunning.reload()
		self.assertEqual(dunning.status, "Resolved")

		credit_note.cancel()
		dunning.reload()
		self.assertEqual(dunning.status, "Unresolved")

	def test_dunning_not_affected_by_standalone_credit_note(self):
		"""
		Test that dunning is NOT resolved when a credit note has update_outstanding_for_self checked.
		"""
		sales_invoice = create_sales_invoice_against_cost_center(
			posting_date=add_days(today(), -10), qty=1, rate=100
		)
		dunning = create_dunning_from_sales_invoice(sales_invoice.name)
		dunning.submit()

		self.assertEqual(dunning.status, "Unresolved")

		credit_note = frappe.copy_doc(sales_invoice)
		credit_note.is_return = 1
		credit_note.return_against = sales_invoice.name
		credit_note.update_outstanding_for_self = 1

		for item in credit_note.items:
			item.qty = -item.qty

		credit_note.save()

		credit_note = frappe.get_doc("Sales Invoice", credit_note.name)
		credit_note.submit()

		dunning.reload()
		self.assertEqual(dunning.status, "Unresolved")


def create_dunning(overdue_days, dunning_type_name=None):
	posting_date = add_days(today(), -1 * overdue_days)
	sales_invoice = create_sales_invoice_against_cost_center(posting_date=posting_date, qty=1, rate=100)
	dunning = create_dunning_from_sales_invoice(sales_invoice.name)

	if dunning_type_name:
		dunning_type = frappe.get_doc("Dunning Type", dunning_type_name)
		dunning.dunning_type = dunning_type.name
		dunning.rate_of_interest = dunning_type.rate_of_interest
		dunning.dunning_fee = dunning_type.dunning_fee
		dunning.income_account = dunning_type.income_account
		dunning.cost_center = dunning_type.cost_center

	return dunning.save()


def create_dunning_type(title, fee, interest, is_default):
	company = "_Test Company"
	if frappe.db.exists("Dunning Type", f"{title} - _TC"):
		return

	dunning_type = frappe.new_doc("Dunning Type")
	dunning_type.dunning_type = title
	dunning_type.company = company
	dunning_type.is_default = is_default
	dunning_type.dunning_fee = fee
	dunning_type.rate_of_interest = interest
	dunning_type.income_account = get_income_account(company)
	dunning_type.cost_center = get_default_cost_center(company)
	dunning_type.append(
		"dunning_letter_text",
		{
			"language": "en",
			"body_text": "We have still not received payment for our invoice",
			"closing_text": "We kindly request that you pay the outstanding amount immediately, including interest and late fees.",
		},
	)
	dunning_type.insert()


def get_income_account(company):
	return (
		frappe.get_value("Company", company, "default_income_account")
		or frappe.get_all(
			"Account",
			filters={"is_group": 0, "company": company},
			or_filters={
				"report_type": "Profit and Loss",
				"account_type": ("in", ("Income Account", "Temporary")),
			},
			limit=1,
			pluck="name",
		)[0]
	)


def create_payment_terms_template_for_dunning():
	from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_payment_term

	create_payment_term("_Test Payment Term 1 for Dunning")
	create_payment_term("_Test Payment Term 2 for Dunning")

	if not frappe.db.exists("Payment Terms Template", "_Test 50-50 for Dunning"):
		frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "_Test 50-50 for Dunning",
				"allocate_payment_based_on_payment_terms": 1,
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"payment_term": "_Test Payment Term 1 for Dunning",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 5,
					},
					{
						"doctype": "Payment Terms Template Detail",
						"payment_term": "_Test Payment Term 2 for Dunning",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 10,
					},
				],
			}
		).insert()
