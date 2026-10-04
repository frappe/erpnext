# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.controllers.accounts_controller import get_payment_term_details, get_payment_terms
from erpnext.tests.permission_test_utils import (
	MISSING_NAME,
	as_user,
	assert_not_found,
	assert_refused,
	assert_refused_for_names,
	assert_refused_without,
	make_fenced_user,
	malformed_names,
)


class TestPaymentTermsTemplate(unittest.TestCase):
	def tearDown(self):
		frappe.delete_doc("Payment Terms Template", "_Test Payment Terms Template For Test", force=1)

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


class TestPaymentTermsPermissions(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def terms_kwargs(self, name):
		return {"terms_template": name, "posting_date": frappe.utils.nowdate(), "grand_total": 100}

	def term_kwargs(self, name):
		return {"term": name, "posting_date": frappe.utils.nowdate(), "grand_total": 100}

	def test_get_payment_terms_refuses_a_template_outside_the_fence(self):
		fenced = make_fenced_user(
			"ptt-fenced@example.com",
			["Accounts User"],
			[("Payment Terms Template", "_Test Payment Term Template 1")],
		)
		with as_user(fenced):
			assert_refused_for_names(
				self,
				get_payment_terms,
				self.terms_kwargs,
				["_Test Payment Term Template"],
				caller_supplied=True,
			)
			assert_refused_without(
				self, ["linked to"], get_payment_terms, **self.terms_kwargs("_Test Payment Term Template")
			)
			schedule = get_payment_terms(**self.terms_kwargs("_Test Payment Term Template 1"))
		total = 0
		for row in schedule:
			total += row.payment_amount
		self.assertEqual(total, 100)

	def test_get_payment_terms_allows_an_unfenced_accounts_user(self):
		user = make_fenced_user("ptt-open@example.com", ["Accounts User"])
		with as_user(user):
			schedule = get_payment_terms(**self.terms_kwargs("_Test Payment Term Template"))
		self.assertTrue(schedule)

	def test_get_payment_term_details_refuses_a_term_outside_the_fence(self):
		fenced = make_fenced_user(
			"payment-term-fenced@example.com", ["Accounts User"], [("Payment Term", "_Test N30")]
		)
		with as_user(fenced):
			assert_refused(self, get_payment_term_details, **self.term_kwargs("_Test COD"))
			for term in malformed_names():
				if term == MISSING_NAME:
					assert_not_found(self, get_payment_term_details, **self.term_kwargs(term))
				else:
					assert_refused(self, get_payment_term_details, **self.term_kwargs(term))
			details = get_payment_term_details(**self.term_kwargs("_Test N30"))
		self.assertEqual(
			details.payment_amount, frappe.db.get_value("Payment Term", "_Test N30", "invoice_portion")
		)
