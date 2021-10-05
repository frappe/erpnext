# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.utils import add_days, nowdate, today

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


class TestDunning(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		create_dunning_type("First Notice", fee=0.0, interest=0.0, is_default=1)
		create_dunning_type("Second Notice", fee=10.0, interest=10.0, is_default=0)
		unlink_payment_on_cancel_of_invoice()

	@classmethod
	def tearDownClass(self):
		unlink_payment_on_cancel_of_invoice(0)

	def test_first_dunning(self):
		dunning = create_first_dunning()

		self.assertEqual(round(dunning.total_outstanding, 2), 100.00)
		self.assertEqual(round(dunning.total_interest, 2), 0.00)
		self.assertEqual(round(dunning.dunning_fee, 2), 0.00)
		self.assertEqual(round(dunning.dunning_amount, 2), 0.00)
		self.assertEqual(round(dunning.grand_total, 2), 100.00)

	def test_second_dunning(self):
		dunning = create_second_dunning()

		self.assertEqual(round(dunning.total_outstanding, 2), 100.00)
		self.assertEqual(round(dunning.total_interest, 2), 0.41)
		self.assertEqual(round(dunning.dunning_fee, 2), 10.00)
		self.assertEqual(round(dunning.dunning_amount, 2), 10.41)
		self.assertEqual(round(dunning.grand_total, 2), 110.41)

	def test_gl_entries(self):
		dunning = create_second_dunning()
		dunning.submit()
		gl_entries = frappe.db.sql(
			"""select account, debit, credit
			from `tabGL Entry` where voucher_type='Dunning' and voucher_no=%s
			order by account asc""",
			dunning.name,
			as_dict=1,
		)
		self.assertTrue(gl_entries)
		expected_values = dict((d[0], d) for d in [
			['Debtors - _TC', 10.41, 0.0],
			['Sales - _TC',  0.0, 10.41]
		])
		for gle in gl_entries:
			self.assertEqual(expected_values[gle.account][0], gle.account)
			self.assertEqual(expected_values[gle.account][1], gle.debit)
			self.assertEqual(expected_values[gle.account][2], gle.credit)

	def test_payment_entry(self):
		dunning = create_second_dunning()
		dunning.submit()
		pe = get_payment_entry("Dunning", dunning.name)
		pe.reference_no = "1"
		pe.reference_date = nowdate()
		pe.paid_from_account_currency = dunning.currency
		pe.paid_to_account_currency = dunning.currency
		pe.source_exchange_rate = 1
		pe.target_exchange_rate = 1
		pe.insert()
		pe.submit()
		si_doc = frappe.get_doc("Sales Invoice", dunning.sales_invoice)
		self.assertEqual(si_doc.outstanding_amount, 0)


def create_first_dunning():
	posting_date = add_days(today(), -20)
	due_date = add_days(today(), -15)
	sales_invoice = create_sales_invoice_against_cost_center(
		posting_date=posting_date, due_date=due_date, qty=1, rate=100)
	dunning = create_dunning_from_sales_invoice(sales_invoice.name)
	dunning.save()

	return dunning


def create_second_dunning():
	posting_date = add_days(today(), -20)
	due_date = add_days(today(), -15)
	sales_invoice = create_sales_invoice_against_cost_center(
		posting_date=posting_date, due_date=due_date, qty=1, rate=100)
	dunning = create_dunning_from_sales_invoice(sales_invoice.name)
	dunning_type = frappe.get_doc("Dunning Type", "Second Notice")

	dunning.dunning_type = dunning_type.name
	dunning.rate_of_interest = dunning_type.rate_of_interest
	dunning.dunning_fee = dunning_type.dunning_fee
	dunning.save()

	return dunning


def create_dunning_type(title, fee, interest, is_default):
	existing = frappe.db.exists("Dunning Type", title)
	if existing:
		return frappe.get_doc("Dunning Type", existing)

	dunning_type = frappe.new_doc("Dunning Type")
	dunning_type.dunning_type = title
	dunning_type.is_default = is_default
	dunning_type.dunning_fee = fee
	dunning_type.rate_of_interest = interest
	dunning_type.append(
		"dunning_letter_text", {
			"language": "en",
			"body_text": "We have still not received payment for our invoice",
			"closing_text": "We kindly request that you pay the outstanding amount immediately, including interest and late fees."
		}
	)
	dunning_type.save()
	return dunning_type
