# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate

from erpnext.controllers.accounts_controller import get_payment_term_details
from erpnext.tests.permission_test_utils import (
	as_user,
	assert_refused_for_names,
	make_fenced_user,
)
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

	def test_get_payment_terms_fences_the_template(self):
		from erpnext.accounts.services.payment_schedule import get_payment_terms

		template = "_Test Payment Term Template"
		other = frappe.db.get_value("Payment Terms Template", {"name": ["!=", template]})

		def payment_terms_kwargs(name):
			return {"terms_template": name, "grand_total": 100}

		outside = make_fenced_user(
			"ptt-fenced@example.com", ["Accounts User"], [("Payment Terms Template", other)]
		)
		with as_user(outside):
			assert_refused_for_names(
				self,
				get_payment_terms,
				payment_terms_kwargs,
				[template],
				type_gated=True,
				caller_supplied=True,
			)
		inside = make_fenced_user(
			"ptt-fenced@example.com", ["Accounts User"], [("Payment Terms Template", template)]
		)
		with as_user(inside):
			schedule = get_payment_terms(template, grand_total=100)
		total = 0
		for row in schedule:
			total += row.payment_amount
		self.assertEqual(total, 100)

	def test_get_payment_term_details_fences_the_term(self):
		from erpnext.accounts.services.payment_schedule import get_payment_term_details

		def term_kwargs(name):
			return {"term": name, "grand_total": 100}

		outside = make_fenced_user(
			"pt-fenced@example.com", ["Accounts User"], [("Payment Term", "_Test COD")]
		)
		with as_user(outside):
			assert_refused_for_names(
				self,
				get_payment_term_details,
				term_kwargs,
				["_Test N30"],
				type_gated=True,
				caller_supplied=True,
			)
		inside = make_fenced_user("pt-fenced@example.com", ["Accounts User"], [("Payment Term", "_Test N30")])
		with as_user(inside):
			details = get_payment_term_details("_Test N30", grand_total=100)
		self.assertEqual(
			details.payment_amount, frappe.db.get_value("Payment Term", "_Test N30", "invoice_portion")
		)
