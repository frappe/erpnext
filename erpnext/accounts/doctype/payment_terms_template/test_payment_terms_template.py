# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.utils import add_days, get_datetime, getdate

from erpnext.controllers.accounts_controller import get_payment_term_details, get_payment_terms
from erpnext.tests.utils import ERPNextTestSuite


class TestPaymentTermsTemplate(ERPNextTestSuite):
	def test_create_template(self):
		template = frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "_Test Payment Terms Template For Test",
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 30,
					}
				],
			}
		)

		self.assertRaises(frappe.ValidationError, template.insert)

		template.append(
			"terms",
			{
				"doctype": "Payment Terms Template Detail",
				"invoice_portion": 50.00,
				"credit_days_based_on": "Day(s) after invoice date",
				"credit_days": 0,
			},
		)

		template.insert()

	def test_credit_days(self):
		template = frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "_Test Payment Terms Template For Test",
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"invoice_portion": 100.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": -30,
					}
				],
			}
		)

		self.assertRaises(frappe.ValidationError, template.insert)

	def test_no_discount_date_without_discount(self):
		posting_date = "2026-05-29"
		term = frappe._dict(
			{
				"payment_term": "_Test No Discount Term",
				"invoice_portion": 100.0,
				"due_date_based_on": "Day(s) after invoice date",
				"credit_days": 0,
				"credit_months": 0,
				"discount_type": "Percentage",
				"discount": 0,
				"discount_validity_based_on": "Day(s) after invoice date",
				"discount_validity": 0,
			}
		)

		details = get_payment_term_details(
			term, posting_date=posting_date, grand_total=100, base_grand_total=100
		)

		self.assertEqual(getdate(details.due_date), getdate(posting_date))
		self.assertIsNone(details.discount_date)

	def test_discount_date_generated_with_discount(self):
		posting_date = "2026-05-29"
		term = frappe._dict(
			{
				"payment_term": "_Test Discount Term",
				"invoice_portion": 100.0,
				"due_date_based_on": "Day(s) after invoice date",
				"credit_days": 30,
				"credit_months": 0,
				"discount_type": "Percentage",
				"discount": 5,
				"discount_validity_based_on": "Day(s) after invoice date",
				"discount_validity": 10,
			}
		)

		details = get_payment_term_details(
			term, posting_date=posting_date, grand_total=100, base_grand_total=100
		)

		self.assertEqual(getdate(details.due_date), getdate(add_days(posting_date, 30)))
		self.assertEqual(getdate(details.discount_date), getdate(add_days(posting_date, 10)))

	def test_payment_term_details_accept_date_objects(self):
		term = frappe._dict(
			payment_term="_Test N30",
			invoice_portion=50,
			due_date_based_on="Day(s) after invoice date",
			credit_days=30,
			discount_type="Percentage",
			discount=5,
			discount_validity_based_on="Day(s) after invoice date",
			discount_validity=10,
		)

		for convert_date in (str, getdate, get_datetime):
			posting_date = convert_date("2026-10-17")
			for bill_date in (None, convert_date("2026-10-20")):
				with self.subTest(posting_date=posting_date, bill_date=bill_date):
					details = get_payment_term_details(term, posting_date, 1000, 2000, bill_date)
					self.assertEqual(
						getdate(details.due_date), getdate("2026-11-19" if bill_date else "2026-11-16")
					)
					self.assertEqual(
						getdate(details.discount_date), getdate("2026-10-30" if bill_date else "2026-10-27")
					)
					self.assertEqual(details.payment_amount, 500)
					self.assertEqual(details.base_payment_amount, 1000)

	def test_payment_terms_accept_date_objects(self):
		for convert_date in (str, getdate, get_datetime):
			posting_date = convert_date("2026-10-17")
			for bill_date in (None, convert_date("2026-10-20")):
				with self.subTest(posting_date=posting_date, bill_date=bill_date):
					schedule = get_payment_terms(
						"_Test Payment Term Template", posting_date, 1000, 2000, bill_date
					)
					self.assertEqual(len(schedule), 2)
					self.assertEqual(getdate(schedule[0].due_date), getdate(bill_date or posting_date))
					self.assertEqual(
						getdate(schedule[1].due_date), getdate("2026-11-19" if bill_date else "2026-11-16")
					)
					for details in schedule:
						self.assertEqual(details.payment_amount, 500)
						self.assertEqual(details.base_payment_amount, 1000)

	def test_duplicate_terms(self):
		template = frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "_Test Payment Terms Template For Test",
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 30,
					},
					{
						"doctype": "Payment Terms Template Detail",
						"invoice_portion": 50.00,
						"credit_days_based_on": "Day(s) after invoice date",
						"credit_days": 30,
					},
				],
			}
		)

		self.assertRaises(frappe.ValidationError, template.insert)
