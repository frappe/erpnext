# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import unittest

import frappe
from frappe.utils import add_days, getdate

from erpnext.controllers.accounts_controller import get_payment_term_details
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
